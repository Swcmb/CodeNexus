"""
影响可视化器单元测试
"""

import pytest
from unittest.mock import Mock, patch
import math

from src.codenexus.services.impact_visualizer import (
    ImpactVisualizer, ImpactVisualizationData, VisualNode, VisualEdge, VisualCluster,
    VisualizationLayout, NodeShape
)
from src.codenexus.services.impact_analyzer import (
    ImpactAnalysisResult, ImpactNode, ImpactPath, ImpactLevel, ChangeType
)


class TestImpactVisualizer:
    """影响可视化器测试类"""
    
    def setup_method(self):
        """测试前置设置"""
        self.visualizer = ImpactVisualizer()
        
        # 创建测试用的影响分析结果
        self.test_nodes = [
            ImpactNode(
                node_id="node_1",
                node_name="TestClass1",
                node_type="class",
                impact_level=ImpactLevel.HIGH,
                impact_score=0.8,
                distance_from_change=1
            ),
            ImpactNode(
                node_id="node_2",
                node_name="TestMethod1",
                node_type="method",
                impact_level=ImpactLevel.MEDIUM,
                impact_score=0.6,
                distance_from_change=2
            )
        ]
        
        # 创建测试用的影响路径
        self.test_paths = [
            ImpactPath(
                source_node_id="changed_node",
                target_node_id="node_2",
                path_nodes=["changed_node", "node_1", "node_2"],
                relationship_types=["calls", "depends"],
                impact_strength=0.8,
                path_length=3
            )
        ]
        
        # 创建测试用的影响分析结果
        self.test_analysis_result = ImpactAnalysisResult(
            changed_node_id="changed_node",
            change_type=ChangeType.MODIFY,
            total_affected_nodes=2,
            impact_summary={
                ImpactLevel.HIGH: 1,
                ImpactLevel.MEDIUM: 1
            },
            affected_nodes=self.test_nodes,
            critical_paths=self.test_paths
        )
    
    def test_generate_visualization_data(self):
        """测试生成可视化数据"""
        # 执行
        viz_data = self.visualizer.generate_visualization_data(
            self.test_analysis_result,
            layout_type=VisualizationLayout.FORCE_DIRECTED,
            canvas_width=800.0,
            canvas_height=600.0
        )
        
        # 验证
        assert isinstance(viz_data, ImpactVisualizationData)
        assert len(viz_data.nodes) == 3  # 2个受影响节点 + 1个变更节点
        assert len(viz_data.edges) >= 1  # 至少有一条边
        assert viz_data.layout_type == VisualizationLayout.FORCE_DIRECTED
        assert viz_data.canvas_width == 800.0
        assert viz_data.canvas_height == 600.0
        
        # 验证变更节点
        changed_nodes = [n for n in viz_data.nodes if n.type == "changed"]
        assert len(changed_nodes) == 1
        assert changed_nodes[0].id == "changed_node"
        assert changed_nodes[0].is_highlighted
    
    def test_create_visual_nodes(self):
        """测试创建可视化节点"""
        # 执行
        visual_nodes = self.visualizer._create_visual_nodes(self.test_analysis_result)
        
        # 验证
        assert len(visual_nodes) == 3  # 2个受影响节点 + 1个变更节点
        
        # 验证变更节点
        changed_node = next(n for n in visual_nodes if n.type == "changed")
        assert changed_node.id == "changed_node"
        assert changed_node.impact_level == ImpactLevel.CRITICAL
        assert changed_node.is_highlighted
        
        # 验证受影响节点
        affected_nodes = [n for n in visual_nodes if n.type != "changed"]
        assert len(affected_nodes) == 2
        
        node_1 = next(n for n in affected_nodes if n.id == "node_1")
        assert node_1.name == "TestClass1"
        assert node_1.type == "class"
        assert node_1.impact_level == ImpactLevel.HIGH
        assert node_1.shape == NodeShape.RECTANGLE
    
    def test_create_visual_edges(self):
        """测试创建可视化边"""
        # 执行
        visual_edges = self.visualizer._create_visual_edges(self.test_analysis_result)
        
        # 验证
        assert len(visual_edges) >= 2  # 路径中的边数
        
        # 验证边的属性
        for edge in visual_edges:
            assert isinstance(edge, VisualEdge)
            assert edge.source_id in ["changed_node", "node_1", "node_2"]
            assert edge.target_id in ["changed_node", "node_1", "node_2"]
            assert edge.relationship_type in ["calls", "depends"]
            assert 0 <= edge.impact_strength <= 1
    
    def test_create_impact_heatmap_data(self):
        """测试创建影响热力图数据"""
        # 执行
        heatmap_data = self.visualizer.create_impact_heatmap_data(
            self.test_analysis_result,
            grid_size=10
        )
        
        # 验证
        assert "data" in heatmap_data
        assert "grid_size" in heatmap_data
        assert "max_value" in heatmap_data
        assert "min_value" in heatmap_data
        assert "color_scale" in heatmap_data
        
        assert heatmap_data["grid_size"] == 10
        assert len(heatmap_data["data"]) == len(self.test_nodes)
        
        # 验证数据点
        for point in heatmap_data["data"]:
            assert "x" in point
            assert "y" in point
            assert "value" in point
            assert "level" in point
            assert "node_id" in point
    
    def test_create_impact_matrix_data(self):
        """测试创建影响矩阵数据"""
        # 执行
        matrix_data = self.visualizer.create_impact_matrix_data(self.test_analysis_result)
        
        # 验证
        assert "matrix" in matrix_data
        assert "type_names" in matrix_data
        assert "size" in matrix_data
        
        assert len(matrix_data["type_names"]) == 2  # class 和 method
        assert matrix_data["size"] == 2
        assert len(matrix_data["matrix"]) == 4  # 2x2 矩阵
        
        # 验证矩阵数据
        for cell in matrix_data["matrix"]:
            assert "source_type" in cell
            assert "target_type" in cell
            assert "impact_strength" in cell
            assert "x" in cell
            assert "y" in cell
    
    def test_apply_force_directed_layout(self):
        """测试力导向布局"""
        # 准备
        visual_nodes = self.visualizer._create_visual_nodes(self.test_analysis_result)
        visual_edges = self.visualizer._create_visual_edges(self.test_analysis_result)
        
        # 执行
        self.visualizer._apply_force_directed_layout(
            visual_nodes, visual_edges, 800.0, 600.0
        )
        
        # 验证
        changed_node = next(n for n in visual_nodes if n.type == "changed")
        assert changed_node.x == 400.0  # 画布中心
        assert changed_node.y == 300.0  # 画布中心
        
        # 验证其他节点有位置
        for node in visual_nodes:
            if node.type != "changed":
                assert node.x != 0 or node.y != 0
    
    def test_apply_circular_layout(self):
        """测试圆形布局"""
        # 准备
        visual_nodes = self.visualizer._create_visual_nodes(self.test_analysis_result)
        
        # 执行
        self.visualizer._apply_circular_layout(visual_nodes, 800.0, 600.0)
        
        # 验证
        changed_node = next(n for n in visual_nodes if n.type == "changed")
        assert changed_node.x == 400.0  # 画布中心
        assert changed_node.y == 300.0  # 画布中心
        
        # 验证其他节点在圆周上
        other_nodes = [n for n in visual_nodes if n.type != "changed"]
        for node in other_nodes:
            # 计算到中心的距离
            distance = math.sqrt((node.x - 400.0)**2 + (node.y - 300.0)**2)
            expected_radius = min(800.0, 600.0) / 3
            assert abs(distance - expected_radius) < 1.0  # 允许小误差
    
    def test_node_size_calculation(self):
        """测试节点大小计算"""
        # 测试不同影响分数
        size_low = self.visualizer._calculate_node_size(0.1)
        size_high = self.visualizer._calculate_node_size(0.9)
        
        assert size_low < size_high
        assert 8.0 <= size_low <= 25.0
        assert 8.0 <= size_high <= 25.0
    
    def test_edge_width_calculation(self):
        """测试边宽度计算"""
        # 测试不同影响强度
        width_low = self.visualizer._calculate_edge_width(0.1)
        width_high = self.visualizer._calculate_edge_width(0.9)
        
        assert width_low < width_high
        assert 1.0 <= width_low <= 5.0
        assert 1.0 <= width_high <= 5.0
    
    def test_create_impact_ranking_data(self):
        """测试创建影响排序数据"""
        ranking_data = self.visualizer.create_impact_ranking_data(
            self.test_analysis_result,
            sort_by="impact_score",
            group_by="impact_level"
        )
        
        # 验证基本结构
        assert "sorted_nodes" in ranking_data
        assert "grouped_nodes" in ranking_data
        assert "statistics" in ranking_data
        
        # 验证排序（按影响分数降序）
        sorted_nodes = ranking_data["sorted_nodes"]
        assert len(sorted_nodes) == 2
        assert sorted_nodes[0]["impact_score"] >= sorted_nodes[1]["impact_score"]
        
        # 验证分组
        grouped_nodes = ranking_data["grouped_nodes"]
        assert "HIGH" in grouped_nodes
        assert "MEDIUM" in grouped_nodes
        assert len(grouped_nodes["HIGH"]) == 1
        assert len(grouped_nodes["MEDIUM"]) == 1
        
        # 验证统计信息
        stats = ranking_data["statistics"]
        assert stats["total_nodes"] == 2
        assert stats["sort_by"] == "impact_score"
        assert stats["group_by"] == "impact_level"
    
    def test_create_impact_level_distribution(self):
        """测试创建影响级别分布数据"""
        distribution_data = self.visualizer.create_impact_level_distribution(
            self.test_analysis_result
        )
        
        # 验证基本结构
        assert "distribution" in distribution_data
        assert "total_nodes" in distribution_data
        assert "most_common_level" in distribution_data
        
        # 验证分布数据
        distribution = distribution_data["distribution"]
        assert len(distribution) == len(ImpactLevel)
        
        # 验证每个级别的数据结构
        for level_data in distribution:
            assert "level" in level_data
            assert "count" in level_data
            assert "percentage" in level_data
            assert "color" in level_data
        
        # 验证总节点数
        assert distribution_data["total_nodes"] == 2
    
    def test_create_impact_path_visualization(self):
        """测试创建影响路径可视化数据"""
        path_data = self.visualizer.create_impact_path_visualization(
            self.test_analysis_result,
            max_paths=5
        )
        
        # 验证基本结构
        assert "paths" in path_data
        assert "total_paths" in path_data
        assert "max_strength" in path_data
        assert "avg_strength" in path_data
        
        # 验证路径数据
        paths = path_data["paths"]
        assert len(paths) == len(self.test_analysis_result.critical_paths)
        
        # 验证路径结构
        if paths:
            path = paths[0]
            assert "path_id" in path
            assert "source_node_id" in path
            assert "target_node_id" in path
            assert "path_nodes" in path
            assert "impact_strength" in path
            assert "strength_level" in path
            assert "path_segments" in path
    
    def test_create_layered_impact_view(self):
        """测试创建分层影响视图数据"""
        layer_data = self.visualizer.create_layered_impact_view(
            self.test_analysis_result
        )
        
        # 验证基本结构
        assert "layers" in layer_data
        assert "total_layers" in layer_data
        assert "max_distance" in layer_data
        assert "total_nodes" in layer_data
        
        # 验证层级数据
        layers = layer_data["layers"]
        assert len(layers) >= 1  # 至少有一层
        
        # 验证层级结构
        for layer in layers:
            assert "layer_index" in layer
            assert "layer_name" in layer
            assert "node_count" in layer
            assert "nodes" in layer
            assert "avg_impact_score" in layer
            assert "impact_level_distribution" in layer
    
    def test_path_strength_classification(self):
        """测试路径强度分类"""
        assert self.visualizer._classify_path_strength(0.9) == "very_strong"
        assert self.visualizer._classify_path_strength(0.7) == "strong"
        assert self.visualizer._classify_path_strength(0.5) == "medium"
        assert self.visualizer._classify_path_strength(0.3) == "weak"
        assert self.visualizer._classify_path_strength(0.1) == "very_weak"
    
    def test_ranking_with_different_sort_options(self):
        """测试不同排序选项的影响排序"""
        # 按距离排序
        ranking_data = self.visualizer.create_impact_ranking_data(
            self.test_analysis_result,
            sort_by="distance_from_change",
            group_by="node_type"
        )
        
        sorted_nodes = ranking_data["sorted_nodes"]
        assert len(sorted_nodes) == 2
        
        # 验证按距离排序
        for i in range(len(sorted_nodes) - 1):
            assert sorted_nodes[i]["distance_from_change"] <= sorted_nodes[i + 1]["distance_from_change"]
        
        # 验证按节点类型分组
        grouped_nodes = ranking_data["grouped_nodes"]
        assert "class" in grouped_nodes
        assert "method" in grouped_nodes
    
    def test_node_shapes_mapping(self):
        """测试节点类型形状映射"""
        # 验证常见节点类型都有形状映射
        common_types = ['class', 'interface', 'method', 'function', 'variable', 'module']
        for node_type in common_types:
            assert node_type in self.visualizer.node_shapes
            assert isinstance(self.visualizer.node_shapes[node_type], NodeShape)