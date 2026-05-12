#!/usr/bin/env python3
"""
图优化器演示程序

展示如何使用GraphOptimizer优化代码知识图谱。
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.codenexus.models.core import (
    CodeGraph, GraphNode, GraphEdge, GraphMetadata
)
from src.codenexus.graph.graph_optimizer import GraphOptimizer


def create_sample_unoptimized_graph():
    """创建一个需要优化的示例图"""
    
    # 创建包含重复和问题的节点
    nodes = [
        # 重复节点
        GraphNode(
            id="node1",
            label="UserService",
            type="class",
            properties={
                "name": "UserService",
                "file_path": "services/user.py",
                "line_number": 1,
                "complexity": 8
            }
        ),
        GraphNode(
            id="node2",
            label="UserService",  # 重复
            type="class",
            properties={
                "name": "UserService",
                "file_path": "services/user.py",
                "line_number": 1,
                "complexity": 6  # 不同的复杂度
            }
        ),
        
        # 相似节点
        GraphNode(
            id="node3",
            label="getUserData",
            type="method",
            properties={
                "name": "getUserData",
                "file_path": "services/user.py",
                "line_number": 10,
                "complexity": 3
            }
        ),
        GraphNode(
            id="node4",
            label="getUserInfo",  # 相似名称
            type="method",
            properties={
                "name": "getUserInfo",
                "file_path": "services/user.py",
                "line_number": 20,
                "complexity": 2
            }
        ),
        
        # 正常节点
        GraphNode(
            id="node5",
            label="Database",
            type="class",
            properties={
                "name": "Database",
                "file_path": "db/connection.py",
                "line_number": 1,
                "complexity": 12
            }
        ),
        GraphNode(
            id="node6",
            label="connect",
            type="method",
            properties={
                "name": "connect",
                "file_path": "db/connection.py",
                "line_number": 15,
                "complexity": 4
            }
        ),
        
        # 孤立节点
        GraphNode(
            id="node7",
            label="UnusedClass",
            type="class",
            properties={
                "name": "UnusedClass",
                "file_path": "unused/old.py",
                "line_number": 1,
                "complexity": 1
            }
        ),
        
        # 线性链节点
        GraphNode(
            id="node8",
            label="ProcessorA",
            type="class",
            properties={"name": "ProcessorA", "file_path": "chain.py", "complexity": 2}
        ),
        GraphNode(
            id="node9",
            label="ProcessorB",
            type="class",
            properties={"name": "ProcessorB", "file_path": "chain.py", "complexity": 2}
        ),
        GraphNode(
            id="node10",
            label="ProcessorC",
            type="class",
            properties={"name": "ProcessorC", "file_path": "chain.py", "complexity": 2}
        )
    ]
    
    # 创建包含重复和问题的边
    edges = [
        # 重复边（因为node1和node2重复）
        GraphEdge(
            id="edge1",
            source_id="node1",
            target_id="node5",
            type="depends",
            properties={"call_count": 5, "strength": 0.7}
        ),
        GraphEdge(
            id="edge2",
            source_id="node2",
            target_id="node5",
            type="depends",
            properties={"call_count": 3, "strength": 0.5}
        ),
        
        # 多条相同方向的边
        GraphEdge(
            id="edge3",
            source_id="node3",
            target_id="node6",
            type="calls",
            properties={"call_count": 10, "strength": 0.8}
        ),
        GraphEdge(
            id="edge4",
            source_id="node3",
            target_id="node6",
            type="calls",
            properties={"call_count": 5, "strength": 0.6}
        ),
        
        # 正常边
        GraphEdge(
            id="edge5",
            source_id="node4",
            target_id="node6",
            type="calls",
            properties={"call_count": 2, "strength": 0.4}
        ),
        
        # 线性链
        GraphEdge(
            id="edge6",
            source_id="node8",
            target_id="node9",
            type="calls",
            properties={"strength": 0.5}
        ),
        GraphEdge(
            id="edge7",
            source_id="node9",
            target_id="node10",
            type="calls",
            properties={"strength": 0.5}
        )
    ]
    
    # 创建元数据
    metadata = GraphMetadata(
        node_count=len(nodes),
        edge_count=len(edges),
        file_count=4,
        languages=["Python"],
        node_types={"class": 6, "method": 4},
        edge_types={"depends": 2, "calls": 5},
        version="1.0"
    )
    
    return CodeGraph(
        nodes=nodes,
        edges=edges,
        metadata=metadata
    )


def demonstrate_basic_optimization():
    """演示基础优化功能"""
    print("=" * 60)
    print("图优化器基础功能演示")
    print("=" * 60)
    
    # 创建未优化的图
    original_graph = create_sample_unoptimized_graph()
    print(f"原始图统计:")
    print(f"  - 节点数: {len(original_graph.nodes)}")
    print(f"  - 边数: {len(original_graph.edges)}")
    print(f"  - 节点类型: {original_graph.metadata.node_types}")
    print(f"  - 边类型: {original_graph.metadata.edge_types}")
    
    # 创建优化器
    optimizer = GraphOptimizer()
    
    print("\n" + "-" * 40)
    print("执行基础优化...")
    print("-" * 40)
    
    # 执行基础优化
    optimized_graph = optimizer.optimize_graph(original_graph, {
        'remove_duplicates': True,
        'merge_similar_nodes': True,
        'remove_isolated_nodes': True,
        'optimize_edges': True,
        'compress_chains': False
    })
    
    print(f"\n优化后图统计:")
    print(f"  - 节点数: {len(optimized_graph.nodes)} (减少了 {len(original_graph.nodes) - len(optimized_graph.nodes)})")
    print(f"  - 边数: {len(optimized_graph.edges)} (减少了 {len(original_graph.edges) - len(optimized_graph.edges)})")
    print(f"  - 节点类型: {optimized_graph.metadata.node_types}")
    print(f"  - 边类型: {optimized_graph.metadata.edge_types}")
    
    # 显示优化统计
    stats = optimizer.get_optimization_stats()
    print(f"\n优化统计:")
    print(f"  - 移除节点数: {stats['nodes_removed']}")
    print(f"  - 移除边数: {stats['edges_removed']}")
    print(f"  - 合并节点数: {stats['nodes_merged']}")
    print(f"  - 合并边数: {stats['edges_merged']}")
    
    return original_graph, optimized_graph


def demonstrate_graph_splitting():
    """演示图分割功能"""
    print("\n" + "=" * 60)
    print("图分割功能演示")
    print("=" * 60)
    
    # 创建包含多个连通分量的图
    nodes = [
        # 第一个分量: Web服务
        GraphNode(id="web1", label="WebController", type="class", 
                 properties={"module": "web", "complexity": 5}),
        GraphNode(id="web2", label="WebService", type="class",
                 properties={"module": "web", "complexity": 8}),
        
        # 第二个分量: 数据库
        GraphNode(id="db1", label="DatabaseManager", type="class",
                 properties={"module": "database", "complexity": 10}),
        GraphNode(id="db2", label="QueryBuilder", type="class",
                 properties={"module": "database", "complexity": 6}),
        
        # 第三个分量: 工具类
        GraphNode(id="util1", label="StringUtils", type="class",
                 properties={"module": "utils", "complexity": 3}),
        GraphNode(id="util2", label="DateUtils", type="class",
                 properties={"module": "utils", "complexity": 4}),
        
        # 孤立节点
        GraphNode(id="isolated", label="OldCode", type="class",
                 properties={"module": "deprecated", "complexity": 1})
    ]
    
    edges = [
        # Web分量内部连接
        GraphEdge(id="e1", source_id="web1", target_id="web2", type="calls"),
        
        # 数据库分量内部连接
        GraphEdge(id="e2", source_id="db1", target_id="db2", type="uses"),
        
        # 工具分量内部连接
        GraphEdge(id="e3", source_id="util1", target_id="util2", type="depends")
    ]
    
    multi_component_graph = CodeGraph(
        nodes=nodes,
        edges=edges,
        metadata=GraphMetadata(languages=["Python"], file_count=4)
    )
    
    print(f"原始图: {len(multi_component_graph.nodes)} 个节点, {len(multi_component_graph.edges)} 条边")
    
    # 分割图
    optimizer = GraphOptimizer()
    subgraphs = optimizer.split_graph_by_components(multi_component_graph)
    
    print(f"\n分割结果: {len(subgraphs)} 个连通分量")
    
    for i, subgraph in enumerate(subgraphs, 1):
        print(f"\n分量 {i}:")
        print(f"  - 节点数: {len(subgraph.nodes)}")
        print(f"  - 边数: {len(subgraph.edges)}")
        
        # 显示节点信息
        if subgraph.nodes:
            modules = set(node.properties.get('module', 'unknown') for node in subgraph.nodes)
            print(f"  - 模块: {', '.join(modules)}")
            
            node_names = [node.label for node in subgraph.nodes]
            print(f"  - 节点: {', '.join(node_names)}")
    
    return subgraphs


def demonstrate_graph_merging():
    """演示图合并功能"""
    print("\n" + "=" * 60)
    print("图合并功能演示")
    print("=" * 60)
    
    # 创建两个独立的图
    graph1 = CodeGraph(
        nodes=[
            GraphNode(id="g1n1", label="AuthService", type="class",
                     properties={"module": "auth", "complexity": 7}),
            GraphNode(id="g1n2", label="login", type="method",
                     properties={"module": "auth", "complexity": 3})
        ],
        edges=[
            GraphEdge(id="g1e1", source_id="g1n1", target_id="g1n2", type="contains")
        ],
        metadata=GraphMetadata(languages=["Python"], file_count=1)
    )
    
    graph2 = CodeGraph(
        nodes=[
            GraphNode(id="g2n1", label="UserModel", type="class",
                     properties={"module": "models", "complexity": 5}),
            GraphNode(id="g2n2", label="save", type="method",
                     properties={"module": "models", "complexity": 2})
        ],
        edges=[
            GraphEdge(id="g2e1", source_id="g2n1", target_id="g2n2", type="contains")
        ],
        metadata=GraphMetadata(languages=["Java"], file_count=1)
    )
    
    print(f"图1: {len(graph1.nodes)} 个节点, {len(graph1.edges)} 条边, 语言: {graph1.metadata.languages}")
    print(f"图2: {len(graph2.nodes)} 个节点, {len(graph2.edges)} 条边, 语言: {graph2.metadata.languages}")
    
    # 合并图
    optimizer = GraphOptimizer()
    merged_graph = optimizer.merge_graphs([graph1, graph2])
    
    print(f"\n合并后的图:")
    print(f"  - 节点数: {len(merged_graph.nodes)}")
    print(f"  - 边数: {len(merged_graph.edges)}")
    print(f"  - 文件数: {merged_graph.metadata.file_count}")
    print(f"  - 支持语言: {', '.join(merged_graph.metadata.languages)}")
    print(f"  - 节点类型分布: {merged_graph.metadata.node_types}")
    
    return merged_graph


def demonstrate_advanced_optimization():
    """演示高级优化功能"""
    print("\n" + "=" * 60)
    print("高级优化功能演示")
    print("=" * 60)
    
    # 创建复杂图用于高级优化
    original_graph = create_sample_unoptimized_graph()
    optimizer = GraphOptimizer()
    
    # 测试不同的优化策略
    strategies = [
        {
            'name': '保守优化',
            'options': {
                'remove_duplicates': True,
                'merge_similar_nodes': False,
                'remove_isolated_nodes': False,
                'optimize_edges': True,
                'compress_chains': False
            }
        },
        {
            'name': '激进优化',
            'options': {
                'remove_duplicates': True,
                'merge_similar_nodes': True,
                'remove_isolated_nodes': True,
                'optimize_edges': True,
                'compress_chains': True
            }
        },
        {
            'name': '仅去重',
            'options': {
                'remove_duplicates': True,
                'merge_similar_nodes': False,
                'remove_isolated_nodes': False,
                'optimize_edges': False,
                'compress_chains': False
            }
        }
    ]
    
    print(f"原始图: {len(original_graph.nodes)} 个节点, {len(original_graph.edges)} 条边")
    
    for strategy in strategies:
        print(f"\n{strategy['name']}:")
        
        # 重置优化器统计
        test_optimizer = GraphOptimizer()
        optimized = test_optimizer.optimize_graph(original_graph, strategy['options'])
        stats = test_optimizer.get_optimization_stats()
        
        print(f"  - 结果: {len(optimized.nodes)} 个节点, {len(optimized.edges)} 条边")
        print(f"  - 节点减少: {len(original_graph.nodes) - len(optimized.nodes)}")
        print(f"  - 边减少: {len(original_graph.edges) - len(optimized.edges)}")
        print(f"  - 统计: 移除节点{stats['nodes_removed']}, 合并节点{stats['nodes_merged']}, 合并边{stats['edges_merged']}")


def main():
    """主函数"""
    try:
        # 演示基础优化
        original_graph, optimized_graph = demonstrate_basic_optimization()
        
        # 演示图分割
        subgraphs = demonstrate_graph_splitting()
        
        # 演示图合并
        merged_graph = demonstrate_graph_merging()
        
        # 演示高级优化
        demonstrate_advanced_optimization()
        
        print("\n" + "=" * 60)
        print("演示完成! 图优化器功能正常运行。")
        print("=" * 60)
        
        # 总结
        print(f"\n总结:")
        print(f"- 基础优化: 将 {len(original_graph.nodes)} 个节点优化为 {len(optimized_graph.nodes)} 个")
        print(f"- 图分割: 识别出 {len(subgraphs)} 个连通分量")
        print(f"- 图合并: 成功合并多个图并保持元数据一致性")
        print(f"- 高级优化: 提供多种优化策略以适应不同需求")
        
    except Exception as e:
        print(f"\n❌ 演示过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())