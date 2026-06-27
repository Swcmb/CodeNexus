"""
影响可视化数据生成模块

提供影响分析结果的可视化数据结构生成功能，包括：
- 影响图谱数据结构
- 影响程度分级和排序
- 可视化布局数据
- 交互式图表数据
"""

from typing import List, Dict, Set, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
import logging
import math
from collections import defaultdict

from .impact_analyzer import (
    ImpactAnalysisResult, ImpactNode, ImpactPath, ImpactLevel, ChangeType
)
from ..exceptions import codenexusError


class VisualizationLayout(Enum):
    """可视化布局类型"""
    FORCE_DIRECTED = "force_directed"
    HIERARCHICAL = "hierarchical"
    CIRCULAR = "circular"
    TREE = "tree"


class NodeShape(Enum):
    """节点形状"""
    CIRCLE = "circle"
    RECTANGLE = "rectangle"
    DIAMOND = "diamond"
    TRIANGLE = "triangle"
    HEXAGON = "hexagon"


@dataclass
class VisualNode:
    """可视化节点"""
    id: str
    name: str
    type: str
    impact_level: ImpactLevel
    impact_score: float
    distance_from_change: int
    
    # 视觉属性
    x: float = 0.0
    y: float = 0.0
    size: float = 10.0
    color: str = "#cccccc"
    shape: NodeShape = NodeShape.CIRCLE
    opacity: float = 1.0
    
    # 交互属性
    is_highlighted: bool = False
    is_selected: bool = False
    tooltip: str = ""
    
    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class VisualEdge:
    """可视化边"""
    id: str
    source_id: str
    target_id: str
    relationship_type: str
    impact_strength: float
    
    # 视觉属性
    width: float = 1.0
    color: str = "#999999"
    opacity: float = 0.8
    style: str = "solid"  # solid, dashed, dotted
    
    # 交互属性
    is_highlighted: bool = False
    tooltip: str = ""
    
    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class VisualCluster:
    """可视化集群"""
    id: str
    name: str
    node_ids: List[str]
    cluster_type: str
    
    # 视觉属性
    x: float = 0.0
    y: float = 0.0
    width: float = 100.0
    height: float = 100.0
    color: str = "#f0f0f0"
    border_color: str = "#cccccc"
    opacity: float = 0.3


@dataclass
class ImpactVisualizationData:
    """影响可视化数据"""
    nodes: List[VisualNode]
    edges: List[VisualEdge]
    clusters: List[VisualCluster]
    
    # 布局信息
    layout_type: VisualizationLayout
    canvas_width: float = 800.0
    canvas_height: float = 600.0
    
    # 统计信息
    total_nodes: int = 0
    total_edges: int = 0
    impact_distribution: Dict[ImpactLevel, int] = field(default_factory=dict)
    
    # 交互配置
    zoom_level: float = 1.0
    center_x: float = 0.0
    center_y: float = 0.0
    
    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)


class ImpactVisualizer:
    """
    影响可视化器
    
    将影响分析结果转换为可视化数据结构，提供：
    - 影响图谱可视化数据生成
    - 影响程度分级和颜色映射
    - 布局算法和位置计算
    - 交互式图表数据结构
    """
    
    def __init__(self):
        """初始化影响可视化器"""
        self.logger = logging.getLogger(__name__)
        
        # 影响级别颜色映射
        self.impact_colors = {
            ImpactLevel.NONE: "#e8e8e8",
            ImpactLevel.LOW: "#90EE90",
            ImpactLevel.MEDIUM: "#FFD700", 
            ImpactLevel.HIGH: "#FF8C00",
            ImpactLevel.CRITICAL: "#FF4500"
        }
        
        # 节点类型形状映射
        self.node_shapes = {
            'class': NodeShape.RECTANGLE,
            'interface': NodeShape.DIAMOND,
            'method': NodeShape.CIRCLE,
            'function': NodeShape.CIRCLE,
            'variable': NodeShape.TRIANGLE,
            'field': NodeShape.TRIANGLE,
            'module': NodeShape.HEXAGON,
            'namespace': NodeShape.HEXAGON
        }
        
        # 关系类型样式映射
        self.edge_styles = {
            'calls': {'color': '#4169E1', 'style': 'solid'},
            'inherits': {'color': '#8B008B', 'style': 'solid'},
            'implements': {'color': '#8B008B', 'style': 'dashed'},
            'depends': {'color': '#32CD32', 'style': 'solid'},
            'imports': {'color': '#FF6347', 'style': 'dotted'},
            'composition': {'color': '#FF1493', 'style': 'solid'},
            'aggregation': {'color': '#FF69B4', 'style': 'dashed'},
            'uses': {'color': '#20B2AA', 'style': 'dotted'}
        }
    
    def generate_visualization_data(
        self,
        analysis_result: ImpactAnalysisResult,
        layout_type: VisualizationLayout = VisualizationLayout.FORCE_DIRECTED,
        canvas_width: float = 800.0,
        canvas_height: float = 600.0,
        include_clusters: bool = True
    ) -> ImpactVisualizationData:
        """
        生成影响可视化数据
        
        Args:
            analysis_result: 影响分析结果
            layout_type: 布局类型
            canvas_width: 画布宽度
            canvas_height: 画布高度
            include_clusters: 是否包含集群
            
        Returns:
            可视化数据结构
        """
        try:
            self.logger.info("开始生成影响可视化数据")
            
            # 创建可视化节点
            visual_nodes = self._create_visual_nodes(analysis_result)
            
            # 创建可视化边
            visual_edges = self._create_visual_edges(analysis_result)
            
            # 创建集群（如果需要）
            visual_clusters = []
            if include_clusters:
                visual_clusters = self._create_visual_clusters(visual_nodes)
            
            # 应用布局算法
            self._apply_layout(visual_nodes, visual_edges, layout_type, canvas_width, canvas_height)
            
            # 生成可视化数据
            viz_data = ImpactVisualizationData(
                nodes=visual_nodes,
                edges=visual_edges,
                clusters=visual_clusters,
                layout_type=layout_type,
                canvas_width=canvas_width,
                canvas_height=canvas_height,
                total_nodes=len(visual_nodes),
                total_edges=len(visual_edges),
                impact_distribution=analysis_result.impact_summary,
                metadata={
                    'changed_node_id': analysis_result.changed_node_id,
                    'change_type': analysis_result.change_type.value,
                    'analysis_timestamp': analysis_result.analysis_metadata.get('analysis_timestamp'),
                    'max_depth': analysis_result.analysis_metadata.get('max_depth', 5)
                }
            )
            
            self.logger.info(f"可视化数据生成完成，包含 {len(visual_nodes)} 个节点和 {len(visual_edges)} 条边")
            return viz_data
            
        except Exception as e:
            self.logger.error(f"生成可视化数据失败: {str(e)}")
            raise codenexusError(f"生成可视化数据失败: {str(e)}")
    
    def create_impact_heatmap_data(
        self,
        analysis_result: ImpactAnalysisResult,
        grid_size: int = 20
    ) -> Dict[str, Any]:
        """
        创建影响热力图数据
        
        Args:
            analysis_result: 影响分析结果
            grid_size: 网格大小
            
        Returns:
            热力图数据
        """
        try:
            # 按影响程度分组节点
            impact_groups = defaultdict(list)
            for node in analysis_result.affected_nodes:
                impact_groups[node.impact_level].append(node)
            
            # 创建热力图数据
            heatmap_data = []
            
            for level, nodes in impact_groups.items():
                for i, node in enumerate(nodes):
                    x = i % grid_size
                    y = i // grid_size
                    
                    heatmap_data.append({
                        'x': x,
                        'y': y,
                        'value': node.impact_score,
                        'level': level.name,
                        'node_id': node.node_id,
                        'node_name': node.node_name,
                        'node_type': node.node_type
                    })
            
            return {
                'data': heatmap_data,
                'grid_size': grid_size,
                'max_value': max([d['value'] for d in heatmap_data]) if heatmap_data else 1.0,
                'min_value': min([d['value'] for d in heatmap_data]) if heatmap_data else 0.0,
                'color_scale': [
                    {'level': level.name, 'color': color}
                    for level, color in self.impact_colors.items()
                ]
            }
            
        except Exception as e:
            self.logger.error(f"创建热力图数据失败: {str(e)}")
            return {'data': [], 'grid_size': grid_size}
    
    def create_impact_timeline_data(
        self,
        analysis_results: List[ImpactAnalysisResult]
    ) -> Dict[str, Any]:
        """
        创建影响时间线数据
        
        Args:
            analysis_results: 多个影响分析结果
            
        Returns:
            时间线数据
        """
        try:
            timeline_data = []
            
            for result in analysis_results:
                timestamp = result.analysis_metadata.get('analysis_timestamp', '')
                
                timeline_data.append({
                    'timestamp': timestamp,
                    'changed_node_id': result.changed_node_id,
                    'change_type': result.change_type.value,
                    'total_affected': result.total_affected_nodes,
                    'impact_summary': {
                        level.name: count for level, count in result.impact_summary.items()
                    },
                    'critical_count': result.impact_summary.get(ImpactLevel.CRITICAL, 0),
                    'high_count': result.impact_summary.get(ImpactLevel.HIGH, 0)
                })
            
            # 按时间排序
            timeline_data.sort(key=lambda x: x['timestamp'])
            
            return {
                'timeline': timeline_data,
                'total_changes': len(timeline_data),
                'date_range': {
                    'start': timeline_data[0]['timestamp'] if timeline_data else '',
                    'end': timeline_data[-1]['timestamp'] if timeline_data else ''
                }
            }
            
        except Exception as e:
            self.logger.error(f"创建时间线数据失败: {str(e)}")
            return {'timeline': [], 'total_changes': 0}
    
    def create_impact_matrix_data(
        self,
        analysis_result: ImpactAnalysisResult
    ) -> Dict[str, Any]:
        """
        创建影响矩阵数据
        
        Args:
            analysis_result: 影响分析结果
            
        Returns:
            影响矩阵数据
        """
        try:
            # 按节点类型分组
            type_groups = defaultdict(list)
            for node in analysis_result.affected_nodes:
                type_groups[node.node_type].append(node)
            
            # 创建矩阵数据
            matrix_data = []
            type_names = list(type_groups.keys())
            
            for i, type1 in enumerate(type_names):
                for j, type2 in enumerate(type_names):
                    # 计算类型间的影响强度
                    impact_strength = self._calculate_type_impact_strength(
                        type_groups[type1], type_groups[type2], analysis_result
                    )
                    
                    matrix_data.append({
                        'source_type': type1,
                        'target_type': type2,
                        'impact_strength': impact_strength,
                        'x': i,
                        'y': j
                    })
            
            return {
                'matrix': matrix_data,
                'type_names': type_names,
                'size': len(type_names)
            }
            
        except Exception as e:
            self.logger.error(f"创建影响矩阵数据失败: {str(e)}")
            return {'matrix': [], 'type_names': [], 'size': 0}
    
    def _create_visual_nodes(self, analysis_result: ImpactAnalysisResult) -> List[VisualNode]:
        """创建可视化节点"""
        visual_nodes = []
        
        # 添加变更节点（中心节点）
        changed_node = VisualNode(
            id=analysis_result.changed_node_id,
            name=analysis_result.changed_node_id,
            type="changed",
            impact_level=ImpactLevel.CRITICAL,
            impact_score=1.0,
            distance_from_change=0,
            size=20.0,
            color="#FF0000",
            shape=NodeShape.DIAMOND,
            is_highlighted=True,
            tooltip=f"变更节点: {analysis_result.change_type.value}"
        )
        visual_nodes.append(changed_node)
        
        # 添加受影响节点
        for node in analysis_result.affected_nodes:
            visual_node = VisualNode(
                id=node.node_id,
                name=node.node_name,
                type=node.node_type,
                impact_level=node.impact_level,
                impact_score=node.impact_score,
                distance_from_change=node.distance_from_change,
                size=self._calculate_node_size(node.impact_score),
                color=self.impact_colors[node.impact_level],
                shape=self.node_shapes.get(node.node_type, NodeShape.CIRCLE),
                tooltip=self._create_node_tooltip(node)
            )
            visual_nodes.append(visual_node)
        
        return visual_nodes
    
    def _create_visual_edges(self, analysis_result: ImpactAnalysisResult) -> List[VisualEdge]:
        """创建可视化边"""
        visual_edges = []
        edge_id_counter = 0
        
        # 从关键路径创建边
        for path in analysis_result.critical_paths:
            for i in range(len(path.path_nodes) - 1):
                source_id = path.path_nodes[i]
                target_id = path.path_nodes[i + 1]
                
                # 获取关系类型
                rel_type = (path.relationship_types[i] 
                           if i < len(path.relationship_types) 
                           else 'unknown')
                
                # 获取样式
                style_config = self.edge_styles.get(rel_type, {'color': '#999999', 'style': 'solid'})
                
                visual_edge = VisualEdge(
                    id=f"edge_{edge_id_counter}",
                    source_id=source_id,
                    target_id=target_id,
                    relationship_type=rel_type,
                    impact_strength=path.impact_strength,
                    width=self._calculate_edge_width(path.impact_strength),
                    color=style_config['color'],
                    style=style_config['style'],
                    opacity=min(0.8, path.impact_strength + 0.3),
                    tooltip=f"{rel_type}: {path.impact_strength:.2f}"
                )
                visual_edges.append(visual_edge)
                edge_id_counter += 1
        
        return visual_edges
    
    def _create_visual_clusters(self, nodes: List[VisualNode]) -> List[VisualCluster]:
        """创建可视化集群"""
        clusters = []
        
        # 按节点类型分组
        type_groups = defaultdict(list)
        for node in nodes:
            if node.type != "changed":  # 排除变更节点
                type_groups[node.type].append(node.id)
        
        cluster_id = 0
        for node_type, node_ids in type_groups.items():
            if len(node_ids) > 1:  # 只为包含多个节点的类型创建集群
                cluster = VisualCluster(
                    id=f"cluster_{cluster_id}",
                    name=f"{node_type} 组件",
                    node_ids=node_ids,
                    cluster_type=node_type,
                    color=self._get_cluster_color(node_type),
                    border_color=self._get_cluster_border_color(node_type)
                )
                clusters.append(cluster)
                cluster_id += 1
        
        return clusters
    
    def _apply_layout(
        self,
        nodes: List[VisualNode],
        edges: List[VisualEdge],
        layout_type: VisualizationLayout,
        canvas_width: float,
        canvas_height: float
    ):
        """应用布局算法"""
        if layout_type == VisualizationLayout.FORCE_DIRECTED:
            self._apply_force_directed_layout(nodes, edges, canvas_width, canvas_height)
        elif layout_type == VisualizationLayout.HIERARCHICAL:
            self._apply_hierarchical_layout(nodes, edges, canvas_width, canvas_height)
        elif layout_type == VisualizationLayout.CIRCULAR:
            self._apply_circular_layout(nodes, canvas_width, canvas_height)
        elif layout_type == VisualizationLayout.TREE:
            self._apply_tree_layout(nodes, edges, canvas_width, canvas_height)
    
    def _apply_force_directed_layout(
        self,
        nodes: List[VisualNode],
        edges: List[VisualEdge],
        canvas_width: float,
        canvas_height: float
    ):
        """应用力导向布局"""
        # 简化的力导向布局算法
        center_x = canvas_width / 2
        center_y = canvas_height / 2
        
        # 找到变更节点并放在中心
        changed_node = None
        for node in nodes:
            if node.type == "changed":
                node.x = center_x
                node.y = center_y
                changed_node = node
                break
        
        # 按距离分层放置其他节点
        if changed_node:
            distance_groups = defaultdict(list)
            for node in nodes:
                if node.type != "changed":
                    distance_groups[node.distance_from_change].append(node)
            
            for distance, group_nodes in distance_groups.items():
                radius = 80 + distance * 60  # 基础半径 + 距离增量
                angle_step = 2 * math.pi / len(group_nodes)
                
                for i, node in enumerate(group_nodes):
                    angle = i * angle_step
                    node.x = center_x + radius * math.cos(angle)
                    node.y = center_y + radius * math.sin(angle)
    
    def _apply_hierarchical_layout(
        self,
        nodes: List[VisualNode],
        edges: List[VisualEdge],
        canvas_width: float,
        canvas_height: float
    ):
        """应用层次布局"""
        # 按距离分层
        distance_groups = defaultdict(list)
        for node in nodes:
            distance_groups[node.distance_from_change].append(node)
        
        max_distance = max(distance_groups.keys()) if distance_groups else 0
        layer_height = canvas_height / (max_distance + 1)
        
        for distance, group_nodes in distance_groups.items():
            y = distance * layer_height + layer_height / 2
            node_width = canvas_width / len(group_nodes)
            
            for i, node in enumerate(group_nodes):
                node.x = i * node_width + node_width / 2
                node.y = y
    
    def _apply_circular_layout(
        self,
        nodes: List[VisualNode],
        canvas_width: float,
        canvas_height: float
    ):
        """应用圆形布局"""
        center_x = canvas_width / 2
        center_y = canvas_height / 2
        radius = min(canvas_width, canvas_height) / 3
        
        # 变更节点放在中心
        for node in nodes:
            if node.type == "changed":
                node.x = center_x
                node.y = center_y
                break
        
        # 其他节点按圆形排列
        other_nodes = [n for n in nodes if n.type != "changed"]
        if other_nodes:
            angle_step = 2 * math.pi / len(other_nodes)
            
            for i, node in enumerate(other_nodes):
                angle = i * angle_step
                node.x = center_x + radius * math.cos(angle)
                node.y = center_y + radius * math.sin(angle)
    
    def _apply_tree_layout(
        self,
        nodes: List[VisualNode],
        edges: List[VisualEdge],
        canvas_width: float,
        canvas_height: float
    ):
        """应用树形布局"""
        # 简化的树形布局，类似层次布局但考虑父子关系
        self._apply_hierarchical_layout(nodes, edges, canvas_width, canvas_height)
    
    def _calculate_node_size(self, impact_score: float) -> float:
        """计算节点大小"""
        min_size = 8.0
        max_size = 25.0
        return min_size + (max_size - min_size) * impact_score
    
    def _calculate_edge_width(self, impact_strength: float) -> float:
        """计算边宽度"""
        min_width = 1.0
        max_width = 5.0
        return min_width + (max_width - min_width) * impact_strength
    
    def _create_node_tooltip(self, node: ImpactNode) -> str:
        """创建节点提示信息"""
        return (f"节点: {node.node_name}\n"
                f"类型: {node.node_type}\n"
                f"影响级别: {node.impact_level.name}\n"
                f"影响分数: {node.impact_score:.2f}\n"
                f"距离: {node.distance_from_change}")
    
    def _get_cluster_color(self, node_type: str) -> str:
        """获取集群颜色"""
        cluster_colors = {
            'class': '#E6F3FF',
            'interface': '#FFE6F3',
            'method': '#F3FFE6',
            'function': '#F3FFE6',
            'variable': '#FFFEE6',
            'field': '#FFFEE6',
            'module': '#F0E6FF',
            'namespace': '#F0E6FF'
        }
        return cluster_colors.get(node_type, '#F5F5F5')
    
    def _get_cluster_border_color(self, node_type: str) -> str:
        """获取集群边框颜色"""
        border_colors = {
            'class': '#4169E1',
            'interface': '#8B008B',
            'method': '#32CD32',
            'function': '#32CD32',
            'variable': '#FFD700',
            'field': '#FFD700',
            'module': '#9370DB',
            'namespace': '#9370DB'
        }
        return border_colors.get(node_type, '#CCCCCC')
    
    def create_impact_ranking_data(
        self,
        analysis_result: ImpactAnalysisResult,
        sort_by: str = "impact_score",
        group_by: str = "impact_level"
    ) -> Dict[str, Any]:
        """
        创建影响程度排序数据
        
        Args:
            analysis_result: 影响分析结果
            sort_by: 排序字段 (impact_score, distance_from_change, node_type)
            group_by: 分组字段 (impact_level, node_type, distance_from_change)
            
        Returns:
            排序和分级数据
        """
        try:
            # 复制节点列表以避免修改原数据
            nodes = analysis_result.affected_nodes.copy()
            
            # 排序节点
            if sort_by == "impact_score":
                nodes.sort(key=lambda x: x.impact_score, reverse=True)
            elif sort_by == "distance_from_change":
                nodes.sort(key=lambda x: x.distance_from_change)
            elif sort_by == "node_type":
                nodes.sort(key=lambda x: x.node_type)
            elif sort_by == "node_name":
                nodes.sort(key=lambda x: x.node_name)
            
            # 分组节点
            groups = defaultdict(list)
            for node in nodes:
                if group_by == "impact_level":
                    groups[node.impact_level.name].append(node)
                elif group_by == "node_type":
                    groups[node.node_type].append(node)
                elif group_by == "distance_from_change":
                    groups[f"距离_{node.distance_from_change}"].append(node)
            
            # 生成排序数据
            ranking_data = {
                'sorted_nodes': [
                    {
                        'node_id': node.node_id,
                        'node_name': node.node_name,
                        'node_type': node.node_type,
                        'impact_level': node.impact_level.name,
                        'impact_score': node.impact_score,
                        'distance_from_change': node.distance_from_change,
                        'rank': i + 1
                    }
                    for i, node in enumerate(nodes)
                ],
                'grouped_nodes': {
                    group_name: [
                        {
                            'node_id': node.node_id,
                            'node_name': node.node_name,
                            'node_type': node.node_type,
                            'impact_level': node.impact_level.name,
                            'impact_score': node.impact_score,
                            'distance_from_change': node.distance_from_change
                        }
                        for node in group_nodes
                    ]
                    for group_name, group_nodes in groups.items()
                },
                'statistics': {
                    'total_nodes': len(nodes),
                    'groups_count': len(groups),
                    'sort_by': sort_by,
                    'group_by': group_by,
                    'top_impact_score': nodes[0].impact_score if nodes else 0.0,
                    'avg_impact_score': sum(n.impact_score for n in nodes) / len(nodes) if nodes else 0.0
                }
            }
            
            return ranking_data
            
        except Exception as e:
            self.logger.error(f"创建影响排序数据失败: {str(e)}")
            return {'sorted_nodes': [], 'grouped_nodes': {}, 'statistics': {}}
    
    def create_impact_level_distribution(
        self,
        analysis_result: ImpactAnalysisResult
    ) -> Dict[str, Any]:
        """
        创建影响级别分布数据
        
        Args:
            analysis_result: 影响分析结果
            
        Returns:
            影响级别分布数据
        """
        try:
            # 统计各级别节点数量
            level_counts = defaultdict(int)
            level_scores = defaultdict(list)
            
            for node in analysis_result.affected_nodes:
                level_counts[node.impact_level.name] += 1
                level_scores[node.impact_level.name].append(node.impact_score)
            
            # 计算各级别统计信息
            distribution_data = []
            total_nodes = len(analysis_result.affected_nodes)
            
            for level in ImpactLevel:
                level_name = level.name
                count = level_counts[level_name]
                scores = level_scores[level_name]
                
                distribution_data.append({
                    'level': level_name,
                    'level_value': level.value,
                    'count': count,
                    'percentage': (count / total_nodes * 100) if total_nodes > 0 else 0.0,
                    'avg_score': sum(scores) / len(scores) if scores else 0.0,
                    'max_score': max(scores) if scores else 0.0,
                    'min_score': min(scores) if scores else 0.0,
                    'color': self.impact_colors[level]
                })
            
            # 按级别值排序（从高到低）
            distribution_data.sort(key=lambda x: x['level_value'], reverse=True)
            
            return {
                'distribution': distribution_data,
                'total_nodes': total_nodes,
                'most_common_level': max(level_counts.items(), key=lambda x: x[1])[0] if level_counts else 'NONE',
                'summary': analysis_result.impact_summary
            }
            
        except Exception as e:
            self.logger.error(f"创建影响级别分布数据失败: {str(e)}")
            return {'distribution': [], 'total_nodes': 0}
    
    def create_impact_path_visualization(
        self,
        analysis_result: ImpactAnalysisResult,
        max_paths: int = 10
    ) -> Dict[str, Any]:
        """
        创建影响路径可视化数据
        
        Args:
            analysis_result: 影响分析结果
            max_paths: 最大路径数量
            
        Returns:
            影响路径可视化数据
        """
        try:
            # 选择最重要的路径
            sorted_paths = sorted(
                analysis_result.critical_paths,
                key=lambda x: x.impact_strength,
                reverse=True
            )[:max_paths]
            
            path_data = []
            for i, path in enumerate(sorted_paths):
                path_info = {
                    'path_id': f"path_{i}",
                    'source_node_id': path.source_node_id,
                    'target_node_id': path.target_node_id,
                    'path_nodes': path.path_nodes,
                    'path_length': path.path_length,
                    'impact_strength': path.impact_strength,
                    'relationship_types': path.relationship_types,
                    'path_rank': i + 1,
                    'strength_level': self._classify_path_strength(path.impact_strength),
                    'path_segments': []
                }
                
                # 创建路径段信息
                for j in range(len(path.path_nodes) - 1):
                    segment = {
                        'from_node': path.path_nodes[j],
                        'to_node': path.path_nodes[j + 1],
                        'relationship_type': (path.relationship_types[j] 
                                            if j < len(path.relationship_types) 
                                            else 'unknown'),
                        'segment_index': j
                    }
                    path_info['path_segments'].append(segment)
                
                path_data.append(path_info)
            
            return {
                'paths': path_data,
                'total_paths': len(sorted_paths),
                'max_strength': max([p.impact_strength for p in sorted_paths]) if sorted_paths else 0.0,
                'avg_strength': (sum([p.impact_strength for p in sorted_paths]) / len(sorted_paths)) if sorted_paths else 0.0,
                'strength_distribution': self._calculate_path_strength_distribution(sorted_paths)
            }
            
        except Exception as e:
            self.logger.error(f"创建影响路径可视化数据失败: {str(e)}")
            return {'paths': [], 'total_paths': 0}
    
    def create_layered_impact_view(
        self,
        analysis_result: ImpactAnalysisResult
    ) -> Dict[str, Any]:
        """
        创建分层影响视图数据
        
        Args:
            analysis_result: 影响分析结果
            
        Returns:
            分层影响视图数据
        """
        try:
            # 按距离分层
            layers = defaultdict(list)
            for node in analysis_result.affected_nodes:
                layers[node.distance_from_change].append(node)
            
            # 为每层排序节点（按影响分数）
            for distance, nodes in layers.items():
                nodes.sort(key=lambda x: x.impact_score, reverse=True)
            
            # 生成分层数据
            layer_data = []
            max_distance = max(layers.keys()) if layers else 0
            
            for distance in range(max_distance + 1):
                layer_nodes = layers.get(distance, [])
                
                layer_info = {
                    'layer_index': distance,
                    'layer_name': f"第{distance}层" if distance > 0 else "变更源",
                    'node_count': len(layer_nodes),
                    'nodes': [
                        {
                            'node_id': node.node_id,
                            'node_name': node.node_name,
                            'node_type': node.node_type,
                            'impact_level': node.impact_level.name,
                            'impact_score': node.impact_score,
                            'layer_rank': i + 1
                        }
                        for i, node in enumerate(layer_nodes)
                    ],
                    'avg_impact_score': (sum(n.impact_score for n in layer_nodes) / len(layer_nodes)) if layer_nodes else 0.0,
                    'max_impact_score': max([n.impact_score for n in layer_nodes]) if layer_nodes else 0.0,
                    'impact_level_distribution': self._get_layer_impact_distribution(layer_nodes)
                }
                
                layer_data.append(layer_info)
            
            return {
                'layers': layer_data,
                'total_layers': len(layer_data),
                'max_distance': max_distance,
                'total_nodes': sum(len(layer['nodes']) for layer in layer_data)
            }
            
        except Exception as e:
            self.logger.error(f"创建分层影响视图数据失败: {str(e)}")
            return {'layers': [], 'total_layers': 0}
    
    def _classify_path_strength(self, strength: float) -> str:
        """分类路径强度"""
        if strength >= 0.8:
            return "very_strong"
        elif strength >= 0.6:
            return "strong"
        elif strength >= 0.4:
            return "medium"
        elif strength >= 0.2:
            return "weak"
        else:
            return "very_weak"
    
    def _calculate_path_strength_distribution(self, paths: List[ImpactPath]) -> Dict[str, int]:
        """计算路径强度分布"""
        distribution = defaultdict(int)
        for path in paths:
            strength_level = self._classify_path_strength(path.impact_strength)
            distribution[strength_level] += 1
        return dict(distribution)
    
    def _get_layer_impact_distribution(self, nodes: List[ImpactNode]) -> Dict[str, int]:
        """获取层级影响分布"""
        distribution = defaultdict(int)
        for node in nodes:
            distribution[node.impact_level.name] += 1
        return dict(distribution)

    def _calculate_type_impact_strength(
        self,
        source_nodes: List[ImpactNode],
        target_nodes: List[ImpactNode],
        analysis_result: ImpactAnalysisResult
    ) -> float:
        """计算类型间影响强度"""
        if not source_nodes or not target_nodes:
            return 0.0
        
        # 计算平均影响分数
        source_avg = sum(node.impact_score for node in source_nodes) / len(source_nodes)
        target_avg = sum(node.impact_score for node in target_nodes) / len(target_nodes)
        
        # 计算连接强度（基于关键路径）
        connection_strength = 0.0
        connection_count = 0
        
        for path in analysis_result.critical_paths:
            source_in_path = any(node.node_id in path.path_nodes for node in source_nodes)
            target_in_path = any(node.node_id in path.path_nodes for node in target_nodes)
            
            if source_in_path and target_in_path:
                connection_strength += path.impact_strength
                connection_count += 1
        
        if connection_count > 0:
            connection_strength /= connection_count
        
        # 综合计算
        return (source_avg + target_avg) / 2 * 0.7 + connection_strength * 0.3