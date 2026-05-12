#!/usr/bin/env python3
"""
影响可视化数据生成演示

展示如何使用影响可视化器和分级器生成各种可视化数据结构，
包括影响程度分级、排序和多种可视化格式。
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.codenexus.services.impact_analyzer import (
    ImpactAnalysisResult, ImpactNode, ImpactPath, ImpactLevel, ChangeType
)
from src.codenexus.services.impact_visualizer import (
    ImpactVisualizer, VisualizationLayout
)
from src.codenexus.services.impact_grader import (
    ImpactGrader, GradingCriteria, SortOrder, GradingRule, SortingConfig
)


def create_sample_analysis_result():
    """创建示例影响分析结果"""
    # 创建受影响节点
    affected_nodes = [
        ImpactNode(
            node_id="UserService",
            node_name="UserService",
            node_type="class",
            impact_level=ImpactLevel.HIGH,
            impact_score=0.85,
            distance_from_change=1
        ),
        ImpactNode(
            node_id="UserController",
            node_name="UserController",
            node_type="class",
            impact_level=ImpactLevel.HIGH,
            impact_score=0.78,
            distance_from_change=1
        ),
        ImpactNode(
            node_id="getUserById",
            node_name="getUserById",
            node_type="method",
            impact_level=ImpactLevel.MEDIUM,
            impact_score=0.65,
            distance_from_change=2
        ),
        ImpactNode(
            node_id="UserRepository",
            node_name="UserRepository",
            node_type="interface",
            impact_level=ImpactLevel.CRITICAL,
            impact_score=0.92,
            distance_from_change=1
        ),
        ImpactNode(
            node_id="validateUser",
            node_name="validateUser",
            node_type="method",
            impact_level=ImpactLevel.MEDIUM,
            impact_score=0.58,
            distance_from_change=2
        ),
        ImpactNode(
            node_id="UserModel",
            node_name="UserModel",
            node_type="class",
            impact_level=ImpactLevel.LOW,
            impact_score=0.35,
            distance_from_change=3
        )
    ]
    
    # 创建关键路径
    critical_paths = [
        ImpactPath(
            source_node_id="User",
            target_node_id="UserService",
            path_nodes=["User", "UserService"],
            path_length=1,
            impact_strength=0.9,
            relationship_types=["depends"]
        ),
        ImpactPath(
            source_node_id="User",
            target_node_id="UserController",
            path_nodes=["User", "UserService", "UserController"],
            path_length=2,
            impact_strength=0.8,
            relationship_types=["depends", "calls"]
        ),
        ImpactPath(
            source_node_id="User",
            target_node_id="getUserById",
            path_nodes=["User", "UserService", "getUserById"],
            path_length=2,
            impact_strength=0.7,
            relationship_types=["depends", "calls"]
        )
    ]
    
    # 创建影响分析结果
    return ImpactAnalysisResult(
        changed_node_id="User",
        change_type=ChangeType.MODIFY,
        total_affected_nodes=len(affected_nodes),
        impact_summary={
            ImpactLevel.CRITICAL: 1,
            ImpactLevel.HIGH: 2,
            ImpactLevel.MEDIUM: 2,
            ImpactLevel.LOW: 1
        },
        affected_nodes=affected_nodes,
        critical_paths=critical_paths,
        analysis_metadata={
            'max_depth': 3,
            'analysis_timestamp': '2024-01-01T10:00:00'
        }
    )


def demo_basic_visualization():
    """演示基础可视化数据生成"""
    print("=== 基础可视化数据生成演示 ===")
    
    # 创建示例数据
    analysis_result = create_sample_analysis_result()
    visualizer = ImpactVisualizer()
    
    # 生成基础可视化数据
    viz_data = visualizer.generate_visualization_data(
        analysis_result,
        layout_type=VisualizationLayout.FORCE_DIRECTED,
        canvas_width=1000,
        canvas_height=800,
        include_clusters=True
    )
    
    print(f"生成的可视化数据:")
    print(f"  - 节点数量: {len(viz_data.nodes)}")
    print(f"  - 边数量: {len(viz_data.edges)}")
    print(f"  - 集群数量: {len(viz_data.clusters)}")
    print(f"  - 布局类型: {viz_data.layout_type.value}")
    print(f"  - 画布大小: {viz_data.canvas_width}x{viz_data.canvas_height}")
    
    # 显示节点信息
    print(f"\n节点详情:")
    for node in viz_data.nodes[:3]:  # 只显示前3个
        print(f"  - {node.name} ({node.type}): 影响级别={node.impact_level.name}, 大小={node.size:.1f}")
    
    print()


def demo_impact_ranking():
    """演示影响程度排序"""
    print("=== 影响程度排序演示 ===")
    
    analysis_result = create_sample_analysis_result()
    visualizer = ImpactVisualizer()
    
    # 按影响分数排序
    ranking_data = visualizer.create_impact_ranking_data(
        analysis_result,
        sort_by="impact_score",
        group_by="impact_level"
    )
    
    print("按影响分数排序的前5个节点:")
    for i, node in enumerate(ranking_data['sorted_nodes'][:5]):
        print(f"  {i+1}. {node['node_name']} ({node['node_type']})")
        print(f"     影响级别: {node['impact_level']}, 分数: {node['impact_score']:.2f}")
    
    print(f"\n按影响级别分组:")
    for level, nodes in ranking_data['grouped_nodes'].items():
        print(f"  {level}: {len(nodes)} 个节点")
    
    print(f"\n统计信息:")
    stats = ranking_data['statistics']
    print(f"  总节点数: {stats['total_nodes']}")
    print(f"  最高影响分数: {stats['top_impact_score']:.2f}")
    print(f"  平均影响分数: {stats['avg_impact_score']:.2f}")
    
    print()


def demo_impact_distribution():
    """演示影响级别分布"""
    print("=== 影响级别分布演示 ===")
    
    analysis_result = create_sample_analysis_result()
    visualizer = ImpactVisualizer()
    
    distribution_data = visualizer.create_impact_level_distribution(analysis_result)
    
    print("影响级别分布:")
    for level_data in distribution_data['distribution']:
        if level_data['count'] > 0:
            print(f"  {level_data['level']}: {level_data['count']} 个节点 "
                  f"({level_data['percentage']:.1f}%), "
                  f"平均分数: {level_data['avg_score']:.2f}")
    
    print(f"\n最常见级别: {distribution_data['most_common_level']}")
    print(f"总节点数: {distribution_data['total_nodes']}")
    
    print()


def demo_layered_view():
    """演示分层影响视图"""
    print("=== 分层影响视图演示 ===")
    
    analysis_result = create_sample_analysis_result()
    visualizer = ImpactVisualizer()
    
    layered_data = visualizer.create_layered_impact_view(analysis_result)
    
    print("分层影响视图:")
    for layer in layered_data['layers']:
        print(f"  {layer['layer_name']} (距离: {layer['layer_index']})")
        print(f"    节点数量: {layer['node_count']}")
        print(f"    平均影响分数: {layer['avg_impact_score']:.2f}")
        print(f"    最高影响分数: {layer['max_impact_score']:.2f}")
        
        # 显示该层的前3个节点
        for i, node in enumerate(layer['nodes'][:3]):
            print(f"      {i+1}. {node['node_name']} ({node['node_type']}) - {node['impact_score']:.2f}")
        
        if len(layer['nodes']) > 3:
            print(f"      ... 还有 {len(layer['nodes']) - 3} 个节点")
        print()
    
    print(f"总层数: {layered_data['total_layers']}")
    print(f"最大距离: {layered_data['max_distance']}")
    
    print()


def demo_impact_grading():
    """演示影响分级功能"""
    print("=== 影响分级功能演示 ===")
    
    analysis_result = create_sample_analysis_result()
    grader = ImpactGrader()
    
    # 使用默认规则进行分级
    graded_nodes = grader.grade_impact_nodes(analysis_result)
    
    print("分级结果:")
    for node in graded_nodes:
        original_level = node.node.impact_level.name
        final_level = node.final_grade.name
        changed = "✓" if original_level != final_level else ""
        
        print(f"  {node.node.node_name} ({node.node.node_type})")
        print(f"    原始级别: {original_level} → 最终级别: {final_level} {changed}")
        print(f"    分级分数: {node.grade_score:.2f}")
        print(f"    维度分数: 影响={node.criteria_scores.get('impact_score', 0):.2f}, "
              f"距离={node.criteria_scores.get('distance_from_change', 0):.2f}, "
              f"类型={node.criteria_scores.get('node_type', 0):.2f}")
        print()
    
    # 创建分级分布报告
    report = grader.create_grade_distribution_report(graded_nodes)
    print(f"分级统计:")
    print(f"  总节点数: {report['total_nodes']}")
    print(f"  级别变更: {report['grade_changes']} 个节点 ({report['change_percentage']:.1f}%)")
    
    print()


def demo_multi_criteria_ranking():
    """演示多维度排名"""
    print("=== 多维度排名演示 ===")
    
    analysis_result = create_sample_analysis_result()
    grader = ImpactGrader()
    
    # 模拟连接度数据
    connectivity_data = {
        "UserService": 8,
        "UserController": 6,
        "getUserById": 3,
        "UserRepository": 12,
        "validateUser": 4,
        "UserModel": 2
    }
    
    graded_nodes = grader.grade_impact_nodes(analysis_result, connectivity_data=connectivity_data)
    
    # 创建多维度排名
    ranking = grader.create_multi_criteria_ranking(graded_nodes)
    
    print("综合排名 (前5名):")
    for i, node_data in enumerate(ranking['comprehensive_ranking'][:5]):
        print(f"  {node_data['rank']}. {node_data['node_name']}")
        print(f"     最终级别: {node_data['final_grade']}")
        print(f"     综合分数: {node_data['grade_score']:.2f}")
        
        breakdown = node_data['criteria_breakdown']
        print(f"     维度分解: 影响={breakdown.get('impact_score', 0):.2f}, "
              f"距离={breakdown.get('distance_from_change', 0):.2f}, "
              f"类型={breakdown.get('node_type', 0):.2f}, "
              f"连接={breakdown.get('connectivity', 0):.2f}")
        print()
    
    print("各维度排名 (前3名):")
    for criteria, ranking_list in ranking['criteria_rankings'].items():
        print(f"  {criteria}:")
        for i, node_data in enumerate(ranking_list[:3]):
            print(f"    {i+1}. {node_data['node_name']}: {node_data['score']:.2f}")
        print()


def demo_path_visualization():
    """演示影响路径可视化"""
    print("=== 影响路径可视化演示 ===")
    
    analysis_result = create_sample_analysis_result()
    visualizer = ImpactVisualizer()
    
    path_data = visualizer.create_impact_path_visualization(analysis_result, max_paths=5)
    
    print("关键影响路径:")
    for path in path_data['paths']:
        print(f"  路径 {path['path_rank']}: {' → '.join(path['path_nodes'])}")
        print(f"    影响强度: {path['impact_strength']:.2f} ({path['strength_level']})")
        print(f"    路径长度: {path['path_length']}")
        print(f"    关系类型: {' → '.join(path['relationship_types'])}")
        print()
    
    print(f"路径统计:")
    print(f"  总路径数: {path_data['total_paths']}")
    print(f"  最大强度: {path_data['max_strength']:.2f}")
    print(f"  平均强度: {path_data['avg_strength']:.2f}")
    
    if 'strength_distribution' in path_data:
        print(f"  强度分布: {path_data['strength_distribution']}")
    
    print()


def main():
    """主函数"""
    print("codenexus 影响可视化数据生成演示")
    print("=" * 50)
    print()
    
    try:
        # 运行各种演示
        demo_basic_visualization()
        demo_impact_ranking()
        demo_impact_distribution()
        demo_layered_view()
        demo_impact_grading()
        demo_multi_criteria_ranking()
        demo_path_visualization()
        
        print("=" * 50)
        print("所有演示完成！")
        print()
        print("这个演示展示了 codenexus 影响可视化数据生成的主要功能:")
        print("1. 基础可视化数据结构生成")
        print("2. 影响程度分级和排序")
        print("3. 影响级别分布分析")
        print("4. 分层影响视图")
        print("5. 智能分级算法")
        print("6. 多维度排名系统")
        print("7. 影响路径可视化")
        print()
        print("这些功能为前端可视化界面提供了丰富的数据支持，")
        print("能够帮助开发者直观地理解代码变更的影响范围和程度。")
        
    except Exception as e:
        print(f"演示过程中出现错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()