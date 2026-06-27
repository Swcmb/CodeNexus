"""
影响分析服务模块

提供代码变更影响分析功能，包括：
- 依赖路径计算
- 影响程度评估
- 影响范围分析
- 变更风险评估
"""

from typing import List, Dict, Set, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
import logging
from collections import defaultdict, deque

from ..models.core import CodeGraph, GraphNode, GraphEdge
from ..database.query_service import GraphQueryService
from ..exceptions import codenexusError


class ImpactLevel(Enum):
    """影响程度级别"""
    NONE = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


class ChangeType(Enum):
    """变更类型"""
    MODIFY = "modify"
    DELETE = "delete"
    ADD = "add"
    RENAME = "rename"


@dataclass
class ImpactPath:
    """影响路径"""
    source_node_id: str
    target_node_id: str
    path_nodes: List[str]
    path_length: int
    impact_strength: float
    relationship_types: List[str]


@dataclass
class ImpactNode:
    """受影响的节点"""
    node_id: str
    node_name: str
    node_type: str
    impact_level: ImpactLevel
    impact_score: float
    distance_from_change: int
    impact_paths: List[ImpactPath] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ImpactAnalysisResult:
    """影响分析结果"""
    changed_node_id: str
    change_type: ChangeType
    total_affected_nodes: int
    impact_summary: Dict[ImpactLevel, int]
    affected_nodes: List[ImpactNode]
    critical_paths: List[ImpactPath]
    analysis_metadata: Dict[str, Any] = field(default_factory=dict)


class ImpactAnalyzer:
    """
    影响分析器
    
    分析代码变更对其他代码部分的潜在影响，提供：
    - 依赖路径计算
    - 影响程度评估
    - 影响范围可视化数据
    """
    
    def __init__(self, query_service: GraphQueryService):
        """
        初始化影响分析器
        
        Args:
            query_service: 图查询服务实例
        """
        self.query_service = query_service
        self.logger = logging.getLogger(__name__)
        
        # 关系类型权重配置
        self.relationship_weights = {
            'calls': 0.8,
            'inherits': 0.9,
            'implements': 0.9,
            'depends': 0.7,
            'imports': 0.6,
            'composition': 0.8,
            'aggregation': 0.6,
            'uses': 0.5
        }
        
        # 节点类型影响系数
        self.node_type_coefficients = {
            'class': 1.0,
            'interface': 1.2,
            'method': 0.8,
            'function': 0.8,
            'variable': 0.6,
            'field': 0.6,
            'module': 1.1,
            'namespace': 1.1
        }
    
    def analyze_impact(
        self,
        graph_name: str,
        changed_node_id: str,
        change_type: ChangeType = ChangeType.MODIFY,
        max_depth: int = 5,
        include_upstream: bool = True,
        include_downstream: bool = True
    ) -> ImpactAnalysisResult:
        """
        分析代码变更的影响
        
        Args:
            graph_name: 图谱名称
            changed_node_id: 变更的节点ID
            change_type: 变更类型
            max_depth: 最大分析深度
            include_upstream: 是否包含上游影响
            include_downstream: 是否包含下游影响
            
        Returns:
            影响分析结果
        """
        try:
            self.logger.info(f"开始分析节点 {changed_node_id} 的影响")
            
            # 获取变更节点信息
            changed_node = self._get_node_info(graph_name, changed_node_id)
            if not changed_node:
                raise codenexusError(f"节点 {changed_node_id} 不存在")
            
            # 收集受影响的节点
            affected_nodes = []
            
            if include_downstream:
                # 分析下游影响（依赖此节点的代码）
                downstream_nodes = self._analyze_downstream_impact(
                    graph_name, changed_node_id, max_depth
                )
                affected_nodes.extend(downstream_nodes)
            
            if include_upstream:
                # 分析上游影响（此节点依赖的代码）
                upstream_nodes = self._analyze_upstream_impact(
                    graph_name, changed_node_id, max_depth, change_type
                )
                affected_nodes.extend(upstream_nodes)
            
            # 去重并计算最终影响分数
            unique_nodes = self._merge_and_score_nodes(affected_nodes)
            
            # 识别关键路径
            critical_paths = self._identify_critical_paths(unique_nodes)
            
            # 生成影响摘要
            impact_summary = self._generate_impact_summary(unique_nodes)
            
            # 构建分析结果
            result = ImpactAnalysisResult(
                changed_node_id=changed_node_id,
                change_type=change_type,
                total_affected_nodes=len(unique_nodes),
                impact_summary=impact_summary,
                affected_nodes=unique_nodes,
                critical_paths=critical_paths,
                analysis_metadata={
                    'max_depth': max_depth,
                    'include_upstream': include_upstream,
                    'include_downstream': include_downstream,
                    'changed_node_type': changed_node.get('type', 'unknown'),
                    'analysis_timestamp': self._get_timestamp()
                }
            )
            
            self.logger.info(f"影响分析完成，共发现 {len(unique_nodes)} 个受影响节点")
            return result
            
        except Exception as e:
            self.logger.error(f"影响分析失败: {str(e)}")
            raise codenexusError(f"影响分析失败: {str(e)}")
    
    def calculate_dependency_paths(
        self,
        graph_name: str,
        source_node_id: str,
        target_node_id: str,
        max_paths: int = 10
    ) -> List[ImpactPath]:
        """
        计算两个节点之间的依赖路径
        
        Args:
            graph_name: 图谱名称
            source_node_id: 源节点ID
            target_node_id: 目标节点ID
            max_paths: 最大路径数量
            
        Returns:
            依赖路径列表
        """
        try:
            # 查找所有路径
            path_result = self.query_service.find_all_paths(
                graph_name, source_node_id, target_node_id,
                max_depth=6, max_paths=max_paths
            )
            
            # 从PathResult中提取路径
            paths = path_result.paths if hasattr(path_result, 'paths') else []
            
            impact_paths = []
            for path in paths:
                # 计算路径强度
                path_strength = self._calculate_path_strength(graph_name, path)
                
                # 获取关系类型
                relationship_types = self._get_path_relationship_types(graph_name, path)
                
                impact_path = ImpactPath(
                    source_node_id=source_node_id,
                    target_node_id=target_node_id,
                    path_nodes=path,
                    path_length=len(path) - 1,
                    impact_strength=path_strength,
                    relationship_types=relationship_types
                )
                impact_paths.append(impact_path)
            
            # 按影响强度排序
            impact_paths.sort(key=lambda x: x.impact_strength, reverse=True)
            
            return impact_paths
            
        except Exception as e:
            self.logger.error(f"计算依赖路径失败: {str(e)}")
            return []
    
    def assess_change_risk(
        self,
        graph_name: str,
        changed_node_id: str,
        change_type: ChangeType
    ) -> Dict[str, Any]:
        """
        评估变更风险
        
        Args:
            graph_name: 图谱名称
            changed_node_id: 变更节点ID
            change_type: 变更类型
            
        Returns:
            风险评估结果
        """
        try:
            # 获取节点信息
            node_info = self._get_node_info(graph_name, changed_node_id)
            if not node_info:
                return {'risk_level': 'unknown', 'reason': '节点不存在'}
            
            # 计算基础风险分数
            base_risk = self._calculate_base_risk(node_info, change_type)
            
            # 计算连接度风险
            connectivity_risk = self._calculate_connectivity_risk(graph_name, changed_node_id)
            
            # 计算复杂度风险
            complexity_risk = self._calculate_complexity_risk(node_info)
            
            # 计算历史变更风险
            history_risk = self._calculate_history_risk(node_info)
            
            # 综合风险评估
            total_risk = (
                base_risk * 0.3 +
                connectivity_risk * 0.4 +
                complexity_risk * 0.2 +
                history_risk * 0.1
            )
            
            # 确定风险等级
            if total_risk >= 0.8:
                risk_level = 'critical'
            elif total_risk >= 0.6:
                risk_level = 'high'
            elif total_risk >= 0.4:
                risk_level = 'medium'
            elif total_risk >= 0.2:
                risk_level = 'low'
            else:
                risk_level = 'minimal'
            
            return {
                'risk_level': risk_level,
                'risk_score': total_risk,
                'risk_factors': {
                    'base_risk': base_risk,
                    'connectivity_risk': connectivity_risk,
                    'complexity_risk': complexity_risk,
                    'history_risk': history_risk
                },
                'recommendations': self._generate_risk_recommendations(
                    risk_level, change_type, node_info
                )
            }
            
        except Exception as e:
            self.logger.error(f"风险评估失败: {str(e)}")
            return {'risk_level': 'unknown', 'reason': str(e)}
    
    def _analyze_downstream_impact(
        self,
        graph_name: str,
        node_id: str,
        max_depth: int
    ) -> List[ImpactNode]:
        """分析下游影响（依赖此节点的代码）"""
        affected_nodes = []
        
        # 使用BFS遍历下游节点
        visited = set()
        queue = deque([(node_id, 0)])
        
        while queue:
            current_node, depth = queue.popleft()
            
            if depth >= max_depth or current_node in visited:
                continue
            
            visited.add(current_node)
            
            # 获取依赖当前节点的节点（入边）
            neighbors_result = self.query_service.get_node_neighbors(
                graph_name, current_node, direction='in', depth=1
            )
            neighbors = [node.id for node in neighbors_result.nodes if node.id != current_node]
            
            for neighbor_id in neighbors:
                if neighbor_id not in visited:
                    # 计算影响分数
                    impact_score = self._calculate_impact_score(
                        graph_name, node_id, neighbor_id, depth + 1
                    )
                    
                    # 获取节点信息
                    neighbor_info = self._get_node_info(graph_name, neighbor_id)
                    
                    if neighbor_info and impact_score > 0.1:  # 过滤低影响节点
                        impact_node = ImpactNode(
                            node_id=neighbor_id,
                            node_name=neighbor_info.get('name', neighbor_id),
                            node_type=neighbor_info.get('type', 'unknown'),
                            impact_level=self._score_to_level(impact_score),
                            impact_score=impact_score,
                            distance_from_change=depth + 1
                        )
                        affected_nodes.append(impact_node)
                        
                        # 继续遍历
                        queue.append((neighbor_id, depth + 1))
        
        return affected_nodes
    
    def _analyze_upstream_impact(
        self,
        graph_name: str,
        node_id: str,
        max_depth: int,
        change_type: ChangeType
    ) -> List[ImpactNode]:
        """分析上游影响（此节点依赖的代码）"""
        affected_nodes = []
        
        # 对于删除操作，上游影响更重要
        if change_type == ChangeType.DELETE:
            max_depth = min(max_depth + 1, 6)
        
        # 使用BFS遍历上游节点
        visited = set()
        queue = deque([(node_id, 0)])
        
        while queue:
            current_node, depth = queue.popleft()
            
            if depth >= max_depth or current_node in visited:
                continue
            
            visited.add(current_node)
            
            # 获取当前节点依赖的节点（出边）
            neighbors_result = self.query_service.get_node_neighbors(
                graph_name, current_node, direction='out', depth=1
            )
            neighbors = [node.id for node in neighbors_result.nodes if node.id != current_node]
            
            for neighbor_id in neighbors:
                if neighbor_id not in visited:
                    # 计算影响分数（上游影响通常较小）
                    impact_score = self._calculate_impact_score(
                        graph_name, node_id, neighbor_id, depth + 1
                    ) * 0.7  # 上游影响系数
                    
                    # 获取节点信息
                    neighbor_info = self._get_node_info(graph_name, neighbor_id)
                    
                    if neighbor_info and impact_score > 0.05:  # 更低的阈值
                        impact_node = ImpactNode(
                            node_id=neighbor_id,
                            node_name=neighbor_info.get('name', neighbor_id),
                            node_type=neighbor_info.get('type', 'unknown'),
                            impact_level=self._score_to_level(impact_score),
                            impact_score=impact_score,
                            distance_from_change=depth + 1
                        )
                        affected_nodes.append(impact_node)
                        
                        # 继续遍历（深度较浅）
                        if depth < max_depth - 2:
                            queue.append((neighbor_id, depth + 1))
        
        return affected_nodes
    
    def _calculate_impact_score(
        self,
        graph_name: str,
        source_node_id: str,
        target_node_id: str,
        distance: int
    ) -> float:
        """计算影响分数"""
        try:
            # 距离衰减因子
            distance_factor = 1.0 / (1.0 + distance * 0.3)
            
            # 获取最短路径
            path_result = self.query_service.find_shortest_path(
                graph_name, source_node_id, target_node_id
            )
            
            # 从PathResult中提取路径
            paths = path_result.paths if hasattr(path_result, 'paths') else []
            
            if not paths:
                return 0.0
            
            # 计算路径强度
            path_strength = self._calculate_path_strength(graph_name, paths[0])
            
            # 获取目标节点信息
            target_info = self._get_node_info(graph_name, target_node_id)
            node_type_coeff = self.node_type_coefficients.get(
                target_info.get('type', 'unknown'), 0.5
            )
            
            # 综合计算影响分数
            impact_score = path_strength * distance_factor * node_type_coeff
            
            return min(impact_score, 1.0)
            
        except Exception:
            return 0.1  # 默认最小影响分数
    
    def _calculate_path_strength(self, graph_name: str, path: List[str]) -> float:
        """计算路径强度"""
        if len(path) < 2:
            return 0.0
        
        total_strength = 1.0
        
        for i in range(len(path) - 1):
            source_id = path[i]
            target_id = path[i + 1]
            
            # 获取边信息
            edges = self.query_service.database.query_edges(
                graph_name, source_id=source_id, target_id=target_id
            )
            
            if edges:
                edge = edges[0]
                edge_type = edge.get('type', 'unknown')
                edge_weight = self.relationship_weights.get(edge_type, 0.5)
                edge_strength = edge.get('strength', 0.5)
                
                # 计算边的综合强度
                combined_strength = edge_weight * edge_strength
                total_strength *= combined_strength
            else:
                total_strength *= 0.3  # 默认弱连接
        
        return total_strength
    
    def _get_path_relationship_types(self, graph_name: str, path: List[str]) -> List[str]:
        """获取路径中的关系类型"""
        relationship_types = []
        
        for i in range(len(path) - 1):
            source_id = path[i]
            target_id = path[i + 1]
            
            edges = self.query_service.database.query_edges(
                graph_name, source_id=source_id, target_id=target_id
            )
            
            if edges:
                relationship_types.append(edges[0].get('type', 'unknown'))
            else:
                relationship_types.append('unknown')
        
        return relationship_types
    
    def _get_node_info(self, graph_name: str, node_id: str) -> Optional[Dict[str, Any]]:
        """获取节点信息"""
        try:
            # 查询所有节点，然后过滤
            all_nodes = self.query_service.database.query_nodes(graph_name)
            for node in all_nodes:
                if node.get('id') == node_id:
                    # 将节点信息转换为统一格式
                    return {
                        'id': node.get('id'),
                        'name': node.get('properties', {}).get('name', node.get('id')),
                        'type': node.get('type'),
                        'complexity': node.get('properties', {}).get('complexity', 1),
                        'properties': node.get('properties', {})
                    }
            return None
        except Exception:
            return None
    
    def _merge_and_score_nodes(self, nodes: List[ImpactNode]) -> List[ImpactNode]:
        """合并重复节点并重新计算分数"""
        node_map = {}
        
        for node in nodes:
            if node.node_id in node_map:
                # 合并节点，取最高影响分数
                existing = node_map[node.node_id]
                if node.impact_score > existing.impact_score:
                    existing.impact_score = node.impact_score
                    existing.impact_level = node.impact_level
                existing.distance_from_change = min(
                    existing.distance_from_change, node.distance_from_change
                )
            else:
                node_map[node.node_id] = node
        
        # 按影响分数排序
        unique_nodes = list(node_map.values())
        unique_nodes.sort(key=lambda x: x.impact_score, reverse=True)
        
        return unique_nodes
    
    def _identify_critical_paths(self, nodes: List[ImpactNode]) -> List[ImpactPath]:
        """识别关键路径"""
        critical_paths = []
        
        # 选择高影响节点的路径
        for node in nodes:
            if node.impact_level in [ImpactLevel.HIGH, ImpactLevel.CRITICAL]:
                critical_paths.extend(node.impact_paths[:2])  # 每个节点最多2条路径
        
        # 按影响强度排序并限制数量
        critical_paths.sort(key=lambda x: x.impact_strength, reverse=True)
        return critical_paths[:10]
    
    def _generate_impact_summary(self, nodes: List[ImpactNode]) -> Dict[ImpactLevel, int]:
        """生成影响摘要"""
        summary = {level: 0 for level in ImpactLevel}
        
        for node in nodes:
            summary[node.impact_level] += 1
        
        return summary
    
    def _score_to_level(self, score: float) -> ImpactLevel:
        """将分数转换为影响级别"""
        if score >= 0.8:
            return ImpactLevel.CRITICAL
        elif score >= 0.6:
            return ImpactLevel.HIGH
        elif score >= 0.4:
            return ImpactLevel.MEDIUM
        elif score >= 0.2:
            return ImpactLevel.LOW
        else:
            return ImpactLevel.NONE
    
    def _calculate_base_risk(self, node_info: Dict[str, Any], change_type: ChangeType) -> float:
        """计算基础风险分数"""
        base_risk = 0.3  # 基础风险
        
        # 根据变更类型调整
        if change_type == ChangeType.DELETE:
            base_risk += 0.4
        elif change_type == ChangeType.RENAME:
            base_risk += 0.3
        elif change_type == ChangeType.MODIFY:
            base_risk += 0.2
        
        # 根据节点类型调整
        node_type = node_info.get('type', 'unknown')
        if node_type in ['interface', 'class']:
            base_risk += 0.2
        elif node_type in ['module', 'namespace']:
            base_risk += 0.3
        
        return min(base_risk, 1.0)
    
    def _calculate_connectivity_risk(self, graph_name: str, node_id: str) -> float:
        """计算连接度风险"""
        try:
            # 获取入度和出度
            in_neighbors_result = self.query_service.get_node_neighbors(
                graph_name, node_id, direction='in', depth=1
            )
            out_neighbors_result = self.query_service.get_node_neighbors(
                graph_name, node_id, direction='out', depth=1
            )
            
            in_degree = len([n for n in in_neighbors_result.nodes if n.id != node_id])
            out_degree = len([n for n in out_neighbors_result.nodes if n.id != node_id])
            total_degree = in_degree + out_degree
            
            # 连接度越高，风险越大
            if total_degree >= 20:
                return 0.9
            elif total_degree >= 10:
                return 0.7
            elif total_degree >= 5:
                return 0.5
            elif total_degree >= 2:
                return 0.3
            else:
                return 0.1
                
        except Exception:
            return 0.3
    
    def _calculate_complexity_risk(self, node_info: Dict[str, Any]) -> float:
        """计算复杂度风险"""
        complexity = node_info.get('complexity', 1)
        
        if complexity >= 20:
            return 0.9
        elif complexity >= 10:
            return 0.7
        elif complexity >= 5:
            return 0.5
        else:
            return 0.2
    
    def _calculate_history_risk(self, node_info: Dict[str, Any]) -> float:
        """计算历史变更风险"""
        # 这里可以根据版本控制历史计算
        # 暂时返回默认值
        return 0.3
    
    def _generate_risk_recommendations(
        self,
        risk_level: str,
        change_type: ChangeType,
        node_info: Dict[str, Any]
    ) -> List[str]:
        """生成风险建议"""
        recommendations = []
        
        if risk_level in ['critical', 'high']:
            recommendations.append("建议进行全面的回归测试")
            recommendations.append("考虑分阶段部署变更")
            recommendations.append("准备回滚计划")
        
        if change_type == ChangeType.DELETE:
            recommendations.append("确认所有依赖项已正确处理")
            recommendations.append("检查是否有替代实现")
        
        if node_info.get('type') in ['interface', 'class']:
            recommendations.append("检查所有实现类和子类")
            recommendations.append("验证API兼容性")
        
        return recommendations
    
    def _get_timestamp(self) -> str:
        """获取当前时间戳"""
        from datetime import datetime
        return datetime.now().isoformat()