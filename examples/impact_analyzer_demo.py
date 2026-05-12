#!/usr/bin/env python3
"""
影响分析器演示程序

展示codenexus影响分析器的核心功能：
- 代码变更影响分析
- 依赖路径计算
- 变更风险评估
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from codenexus.services.impact_analyzer import (
    ImpactAnalyzer, ChangeType, ImpactLevel
)
from codenexus.database.mock_database import MockGraphDatabase
from codenexus.database.query_service import GraphQueryService
from codenexus.models.core import CodeGraph, GraphNode, GraphEdge, GraphMetadata


def create_sample_project_graph():
    """创建示例项目图谱"""
    print("🔧 创建示例项目图谱...")
    
    # 创建节点 - 模拟一个Web应用项目
    nodes = [
        # 核心业务类
        GraphNode(
            id='user_service',
            label='UserService',
            type='class',
            properties={'name': 'UserService', 'complexity': 8, 'file': 'services/user_service.py'}
        ),
        GraphNode(
            id='auth_service',
            label='AuthService',
            type='class',
            properties={'name': 'AuthService', 'complexity': 6, 'file': 'services/auth_service.py'}
        ),
        GraphNode(
            id='user_controller',
            label='UserController',
            type='class',
            properties={'name': 'UserController', 'complexity': 5, 'file': 'controllers/user_controller.py'}
        ),
        
        # 数据访问层
        GraphNode(
            id='user_repository',
            label='UserRepository',
            type='class',
            properties={'name': 'UserRepository', 'complexity': 4, 'file': 'repositories/user_repository.py'}
        ),
        GraphNode(
            id='database_connection',
            label='DatabaseConnection',
            type='class',
            properties={'name': 'DatabaseConnection', 'complexity': 3, 'file': 'database/connection.py'}
        ),
        
        # 模型类
        GraphNode(
            id='user_model',
            label='User',
            type='class',
            properties={'name': 'User', 'complexity': 2, 'file': 'models/user.py'}
        ),
        
        # 接口
        GraphNode(
            id='user_interface',
            label='IUserService',
            type='interface',
            properties={'name': 'IUserService', 'complexity': 1, 'file': 'interfaces/user_interface.py'}
        ),
        
        # 工具类
        GraphNode(
            id='password_hasher',
            label='PasswordHasher',
            type='class',
            properties={'name': 'PasswordHasher', 'complexity': 3, 'file': 'utils/password_hasher.py'}
        ),
        
        # 配置类
        GraphNode(
            id='app_config',
            label='AppConfig',
            type='class',
            properties={'name': 'AppConfig', 'complexity': 2, 'file': 'config/app_config.py'}
        ),
        
        # 测试类
        GraphNode(
            id='user_service_test',
            label='UserServiceTest',
            type='class',
            properties={'name': 'UserServiceTest', 'complexity': 4, 'file': 'tests/test_user_service.py'}
        )
    ]
    
    # 创建边 - 表示依赖关系
    edges = [
        # UserService的依赖
        GraphEdge(
            id='edge_1',
            source_id='user_service',
            target_id='user_interface',
            type='implements',
            properties={'strength': 0.9}
        ),
        GraphEdge(
            id='edge_2',
            source_id='user_service',
            target_id='user_repository',
            type='depends',
            properties={'strength': 0.8}
        ),
        GraphEdge(
            id='edge_3',
            source_id='user_service',
            target_id='auth_service',
            type='depends',
            properties={'strength': 0.7}
        ),
        GraphEdge(
            id='edge_4',
            source_id='user_service',
            target_id='password_hasher',
            type='uses',
            properties={'strength': 0.6}
        ),
        
        # UserController的依赖
        GraphEdge(
            id='edge_5',
            source_id='user_controller',
            target_id='user_service',
            type='depends',
            properties={'strength': 0.9}
        ),
        
        # UserRepository的依赖
        GraphEdge(
            id='edge_6',
            source_id='user_repository',
            target_id='database_connection',
            type='depends',
            properties={'strength': 0.8}
        ),
        GraphEdge(
            id='edge_7',
            source_id='user_repository',
            target_id='user_model',
            type='uses',
            properties={'strength': 0.7}
        ),
        
        # AuthService的依赖
        GraphEdge(
            id='edge_8',
            source_id='auth_service',
            target_id='user_repository',
            type='depends',
            properties={'strength': 0.8}
        ),
        GraphEdge(
            id='edge_9',
            source_id='auth_service',
            target_id='password_hasher',
            type='uses',
            properties={'strength': 0.9}
        ),
        
        # 配置依赖
        GraphEdge(
            id='edge_10',
            source_id='database_connection',
            target_id='app_config',
            type='depends',
            properties={'strength': 0.6}
        ),
        
        # 测试依赖
        GraphEdge(
            id='edge_11',
            source_id='user_service_test',
            target_id='user_service',
            type='tests',
            properties={'strength': 0.8}
        )
    ]
    
    # 创建图谱元数据
    metadata = GraphMetadata(
        node_count=len(nodes),
        edge_count=len(edges),
        file_count=10,
        languages=['python'],
        node_types={'class': 9, 'interface': 1},
        edge_types={'implements': 1, 'depends': 6, 'uses': 3, 'tests': 1}
    )
    
    # 创建图谱
    graph = CodeGraph(
        id='web_app_project',
        nodes=nodes,
        edges=edges,
        metadata=metadata
    )
    
    print(f"✅ 创建了包含 {len(nodes)} 个节点和 {len(edges)} 条边的项目图谱")
    return graph


def demonstrate_impact_analysis(analyzer, graph_name):
    """演示影响分析功能"""
    print("\n" + "="*60)
    print("🔍 影响分析演示")
    print("="*60)
    
    # 场景1：修改核心服务类
    print("\n📝 场景1：修改 UserService 类")
    print("-" * 40)
    
    result = analyzer.analyze_impact(
        graph_name=graph_name,
        changed_node_id='user_service',
        change_type=ChangeType.MODIFY,
        max_depth=3
    )
    
    print(f"变更节点: {result.changed_node_id}")
    print(f"变更类型: {result.change_type.value}")
    print(f"受影响节点总数: {result.total_affected_nodes}")
    
    print("\n影响级别分布:")
    for level, count in result.impact_summary.items():
        if count > 0:
            print(f"  {level.name}: {count} 个节点")
    
    print("\n受影响的节点:")
    for node in result.affected_nodes[:5]:  # 显示前5个
        print(f"  - {node.node_name} ({node.node_type})")
        print(f"    影响级别: {node.impact_level.name}")
        print(f"    影响分数: {node.impact_score:.2f}")
        print(f"    距离: {node.distance_from_change}")
    
    # 场景2：删除接口
    print("\n📝 场景2：删除 IUserService 接口")
    print("-" * 40)
    
    result = analyzer.analyze_impact(
        graph_name=graph_name,
        changed_node_id='user_interface',
        change_type=ChangeType.DELETE,
        max_depth=2
    )
    
    print(f"受影响节点总数: {result.total_affected_nodes}")
    print("影响级别分布:")
    for level, count in result.impact_summary.items():
        if count > 0:
            print(f"  {level.name}: {count} 个节点")


def demonstrate_dependency_paths(analyzer, graph_name):
    """演示依赖路径计算"""
    print("\n" + "="*60)
    print("🔗 依赖路径分析演示")
    print("="*60)
    
    # 计算从UserController到DatabaseConnection的依赖路径
    print("\n📍 计算 UserController → DatabaseConnection 的依赖路径")
    print("-" * 50)
    
    paths = analyzer.calculate_dependency_paths(
        graph_name=graph_name,
        source_node_id='user_controller',
        target_node_id='database_connection',
        max_paths=5
    )
    
    if paths:
        print(f"找到 {len(paths)} 条依赖路径:")
        for i, path in enumerate(paths, 1):
            print(f"\n路径 {i}:")
            print(f"  长度: {path.path_length}")
            print(f"  强度: {path.impact_strength:.3f}")
            print(f"  节点: {' → '.join(path.path_nodes)}")
            print(f"  关系: {' → '.join(path.relationship_types)}")
    else:
        print("未找到依赖路径")
    
    # 计算从AuthService到User模型的路径
    print("\n📍 计算 AuthService → User 的依赖路径")
    print("-" * 40)
    
    paths = analyzer.calculate_dependency_paths(
        graph_name=graph_name,
        source_node_id='auth_service',
        target_node_id='user_model',
        max_paths=3
    )
    
    if paths:
        print(f"找到 {len(paths)} 条依赖路径:")
        for i, path in enumerate(paths, 1):
            print(f"  路径 {i}: {' → '.join(path.path_nodes)} (强度: {path.impact_strength:.3f})")
    else:
        print("未找到依赖路径")


def demonstrate_risk_assessment(analyzer, graph_name):
    """演示风险评估功能"""
    print("\n" + "="*60)
    print("⚠️  变更风险评估演示")
    print("="*60)
    
    # 评估不同节点的变更风险
    test_nodes = [
        ('user_service', ChangeType.MODIFY, '修改核心业务服务'),
        ('user_interface', ChangeType.DELETE, '删除用户接口'),
        ('password_hasher', ChangeType.MODIFY, '修改密码哈希工具'),
        ('app_config', ChangeType.MODIFY, '修改应用配置'),
        ('user_model', ChangeType.RENAME, '重命名用户模型')
    ]
    
    for node_id, change_type, description in test_nodes:
        print(f"\n📊 {description}")
        print("-" * 40)
        
        risk_assessment = analyzer.assess_change_risk(
            graph_name=graph_name,
            changed_node_id=node_id,
            change_type=change_type
        )
        
        print(f"节点: {node_id}")
        print(f"变更类型: {change_type.value}")
        print(f"风险等级: {risk_assessment['risk_level'].upper()}")
        print(f"风险分数: {risk_assessment['risk_score']:.3f}")
        
        print("风险因子:")
        for factor, score in risk_assessment['risk_factors'].items():
            print(f"  {factor}: {score:.3f}")
        
        if risk_assessment['recommendations']:
            print("建议:")
            for rec in risk_assessment['recommendations'][:3]:  # 显示前3个建议
                print(f"  • {rec}")


def main():
    """主函数"""
    print("🚀 codenexus 影响分析器演示")
    print("="*60)
    
    # 初始化组件
    print("🔧 初始化影响分析器...")
    database = MockGraphDatabase()
    query_service = GraphQueryService(database)
    analyzer = ImpactAnalyzer(query_service)
    
    # 创建示例项目图谱
    graph = create_sample_project_graph()
    graph_name = database.store_graph(graph)
    
    # 演示各种功能
    demonstrate_impact_analysis(analyzer, graph_name)
    demonstrate_dependency_paths(analyzer, graph_name)
    demonstrate_risk_assessment(analyzer, graph_name)
    
    print("\n" + "="*60)
    print("✅ 影响分析器演示完成！")
    print("="*60)
    
    # 显示总结信息
    print(f"\n📈 演示总结:")
    print(f"  • 分析了包含 {len(graph.nodes)} 个节点的项目图谱")
    print(f"  • 演示了 {len(graph.edges)} 种依赖关系")
    print(f"  • 展示了影响分析、路径计算和风险评估功能")
    print(f"  • 支持多种变更类型和影响级别")


if __name__ == "__main__":
    main()