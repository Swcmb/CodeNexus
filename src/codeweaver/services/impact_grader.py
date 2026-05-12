"""
影响程度分级器模块

提供影响分析结果的分级和排序功能，包括：
- 影响程度自动分级
- 多维度排序算法
- 影响权重计算
- 分级规则配置
"""

from typing import List, Dict, Set, Optional, Tuple, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import logging
from collections import defaultdict

from .impact_analyzer import ImpactAnalysisResult, ImpactNode, ImpactPath, ImpactLevel, ChangeType
from ..exceptions import codenexusError


class GradingCriteria(Enum):
    """分级标准"""
    IMPACT_SCORE = "impact_score"
    DISTANCE = "distance_from_change"
    NODE_TYPE = "node_type"
    CONNECTIVITY = "connectivity"
    COMPLEXITY = "complexity"
    COMBINED = "combined"


class SortOrder(Enum):
    """排序顺序"""
    ASCENDING = "asc"
    DESCENDING = "desc"


@dataclass
class GradingRule:
    """分级规则"""
    criteria: GradingCriteria
    weight: float
    threshold_critical: float = 0.8
    threshold_high: float = 0.6
    threshold_medium: float = 0.4
    threshold_low: float = 0.2


@dataclass
class SortingConfig:
    """排序配置"""
    primary_criteria: GradingCriteria
    primary_order: SortOrder = SortOrder.DESCENDING
    secondary_criteria: Optional[GradingCriteria] = None
    secondary_order: SortOrder = SortOrder.ASCENDING


@dataclass
class GradedNode:
    """分级后的节点"""
    node: ImpactNode
    final_grade: ImpactLevel
    grade_score: float
    criteria_scores: Dict[GradingCriteria, float] = field(default_factory=dict)
    rank: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


class ImpactGrader:
    """
    影响程度分级器
    
    提供影响分析结果的智能分级和排序功能，支持：
    - 多维度影响评估
    - 自定义分级规则
    - 灵活的排序策略
    - 权重配置管理
    """
    
    def __init__(self):
        """初始化影响分级器"""
        self.logger = logging.getLogger(__name__)
        
        # 默认分级规则
        self.default_rules = [
            GradingRule(GradingCriteria.IMPACT_SCORE, 0.4),
            GradingRule(GradingCriteria.DISTANCE, 0.2),
            GradingRule(GradingCriteria.NODE_TYPE, 0.2),
            GradingRule(GradingCriteria.CONNECTIVITY, 0.2)
        ]
        
        # 节点类型权重
        self.node_type_weights = {
            'interface': 1.0,
            'class': 0.9,
            'module': 0.8,
            'namespace': 0.8,
            'method': 0.7,
            'function': 0.7,
            'variable': 0.5,
            'field': 0.5
        }
    
    def grade_impact_nodes(
        self,
        analysis_result: ImpactAnalysisResult,
        grading_rules: Optional[List[GradingRule]] = None,
        connectivity_data: Optional[Dict[str, int]] = None
    ) -> List[GradedNode]:
        """
        对影响节点进行分级
        
        Args:
            analysis_result: 影响分析结果
            grading_rules: 自定义分级规则
            connectivity_data: 节点连接度数据
            
        Returns:
            分级后的节点列表
        """
        try:
            self.logger.info("开始对影响节点进行分级")
            
            rules = grading_rules or self.default_rules
            graded_nodes = []
            
            for node in analysis_result.affected_nodes:
                # 计算各维度分数
                criteria_scores = self._calculate_criteria_scores(
                    node, analysis_result, connectivity_data
                )
                
                # 计算综合分数
                final_score = self._calculate_weighted_score(criteria_scores, rules)
                
                # 确定最终级别
                final_grade = self._score_to_grade(final_score, rules[0])  # 使用第一个规则的阈值
                
                graded_node = GradedNode(
                    node=node,
                    final_grade=final_grade,
                    grade_score=final_score,
                    criteria_scores=criteria_scores,
                    metadata={
                        'original_level': node.impact_level,
                        'grade_changed': final_grade != node.impact_level,
                        'grading_timestamp': self._get_timestamp()
                    }
                )
                graded_nodes.append(graded_node)
            
            self.logger.info(f"完成 {len(graded_nodes)} 个节点的分级")
            return graded_nodes
            
        except Exception as e:
            self.logger.error(f"节点分级失败: {str(e)}")
            raise codenexusError(f"节点分级失败: {str(e)}")
    
    def sort_graded_nodes(
        self,
        graded_nodes: List[GradedNode],
        sorting_config: SortingConfig
    ) -> List[GradedNode]:
        """
        对分级节点进行排序
        
        Args:
            graded_nodes: 分级后的节点列表
            sorting_config: 排序配置
            
        Returns:
            排序后的节点列表
        """
        try:
            self.logger.info("开始对分级节点进行排序")
            
            # 创建排序键函数
            def sort_key(graded_node: GradedNode) -> Tuple:
                primary_value = self._get_sort_value(graded_node, sorting_config.primary_criteria)
                
                if sorting_config.secondary_criteria:
                    secondary_value = self._get_sort_value(graded_node, sorting_config.secondary_criteria)
                    return (primary_value, secondary_value)
                else:
                    return (primary_value,)
            
            # 执行排序
            sorted_nodes = sorted(
                graded_nodes,
                key=sort_key,
                reverse=(sorting_config.primary_order == SortOrder.DESCENDING)
            )
            
            # 更新排名
            for i, node in enumerate(sorted_nodes):
                node.rank = i + 1
            
            self.logger.info(f"完成 {len(sorted_nodes)} 个节点的排序")
            return sorted_nodes
            
        except Exception as e:
            self.logger.error(f"节点排序失败: {str(e)}")
            raise codenexusError(f"节点排序失败: {str(e)}")
    
    def create_grade_distribution_report(
        self,
        graded_nodes: List[GradedNode]
    ) -> Dict[str, Any]:
        """
        创建分级分布报告
        
        Args:
            graded_nodes: 分级后的节点列表
            
        Returns:
            分级分布报告
        """
        try:
            # 统计各级别分布
            grade_counts = defaultdict(int)
            grade_scores = defaultdict(list)
            original_vs_new = defaultdict(lambda: defaultdict(int))
            
            for graded_node in graded_nodes:
                final_grade = graded_node.final_grade.name
                original_grade = graded_node.node.impact_level.name
                
                grade_counts[final_grade] += 1
                grade_scores[final_grade].append(graded_node.grade_score)
                original_vs_new[original_grade][final_grade] += 1
            
            # 生成分布数据
            distribution = []
            total_nodes = len(graded_nodes)
            
            for level in ImpactLevel:
                level_name = level.name
                count = grade_counts[level_name]
                scores = grade_scores[level_name]
                
                distribution.append({
                    'level': level_name,
                    'level_value': level.value,
                    'count': count,
                    'percentage': (count / total_nodes * 100) if total_nodes > 0 else 0.0,
                    'avg_score': sum(scores) / len(scores) if scores else 0.0,
                    'max_score': max(scores) if scores else 0.0,
                    'min_score': min(scores) if scores else 0.0
                })
            
            # 计算分级变化统计
            grade_changes = sum(1 for node in graded_nodes if node.metadata.get('grade_changed', False))
            
            return {
                'distribution': distribution,
                'total_nodes': total_nodes,
                'grade_changes': grade_changes,
                'change_percentage': (grade_changes / total_nodes * 100) if total_nodes > 0 else 0.0,
                'grade_transition_matrix': dict(original_vs_new),
                'top_nodes': [
                    {
                        'node_id': node.node.node_id,
                        'node_name': node.node.node_name,
                        'final_grade': node.final_grade.name,
                        'grade_score': node.grade_score,
                        'rank': node.rank
                    }
                    for node in sorted(graded_nodes, key=lambda x: x.grade_score, reverse=True)[:10]
                ]
            }
            
        except Exception as e:
            self.logger.error(f"创建分级分布报告失败: {str(e)}")
            return {'distribution': [], 'total_nodes': 0}
    
    def create_multi_criteria_ranking(
        self,
        graded_nodes: List[GradedNode],
        criteria_weights: Optional[Dict[GradingCriteria, float]] = None
    ) -> Dict[str, Any]:
        """
        创建多维度排名
        
        Args:
            graded_nodes: 分级后的节点列表
            criteria_weights: 维度权重
            
        Returns:
            多维度排名数据
        """
        try:
            weights = criteria_weights or {
                GradingCriteria.IMPACT_SCORE: 0.4,
                GradingCriteria.DISTANCE: 0.2,
                GradingCriteria.NODE_TYPE: 0.2,
                GradingCriteria.CONNECTIVITY: 0.2
            }
            
            # 为每个维度创建排名
            criteria_rankings = {}
            
            for criteria in weights.keys():
                sorted_by_criteria = sorted(
                    graded_nodes,
                    key=lambda x: x.criteria_scores.get(criteria, 0.0),
                    reverse=True
                )
                
                criteria_rankings[criteria.value] = [
                    {
                        'node_id': node.node.node_id,
                        'node_name': node.node.node_name,
                        'score': node.criteria_scores.get(criteria, 0.0),
                        'rank': i + 1
                    }
                    for i, node in enumerate(sorted_by_criteria)
                ]
            
            # 计算综合排名
            comprehensive_ranking = sorted(
                graded_nodes,
                key=lambda x: x.grade_score,
                reverse=True
            )
            
            return {
                'criteria_rankings': criteria_rankings,
                'comprehensive_ranking': [
                    {
                        'node_id': node.node.node_id,
                        'node_name': node.node.node_name,
                        'final_grade': node.final_grade.name,
                        'grade_score': node.grade_score,
                        'rank': i + 1,
                        'criteria_breakdown': node.criteria_scores
                    }
                    for i, node in enumerate(comprehensive_ranking)
                ],
                'weights_used': {k.value: v for k, v in weights.items()},
                'total_nodes': len(graded_nodes)
            }
            
        except Exception as e:
            self.logger.error(f"创建多维度排名失败: {str(e)}")
            return {'criteria_rankings': {}, 'comprehensive_ranking': []}
    
    def _calculate_criteria_scores(
        self,
        node: ImpactNode,
        analysis_result: ImpactAnalysisResult,
        connectivity_data: Optional[Dict[str, int]] = None
    ) -> Dict[GradingCriteria, float]:
        """计算各维度分数"""
        scores = {}
        
        # 影响分数维度
        scores[GradingCriteria.IMPACT_SCORE] = node.impact_score
        
        # 距离维度（距离越近分数越高）
        max_distance = max([n.distance_from_change for n in analysis_result.affected_nodes])
        if max_distance > 0:
            scores[GradingCriteria.DISTANCE] = 1.0 - (node.distance_from_change / max_distance)
        else:
            scores[GradingCriteria.DISTANCE] = 1.0
        
        # 节点类型维度
        scores[GradingCriteria.NODE_TYPE] = self.node_type_weights.get(node.node_type, 0.5)
        
        # 连接度维度
        if connectivity_data and node.node_id in connectivity_data:
            max_connectivity = max(connectivity_data.values()) if connectivity_data else 1
            scores[GradingCriteria.CONNECTIVITY] = connectivity_data[node.node_id] / max_connectivity
        else:
            scores[GradingCriteria.CONNECTIVITY] = 0.5  # 默认中等连接度
        
        return scores
    
    def _calculate_weighted_score(
        self,
        criteria_scores: Dict[GradingCriteria, float],
        rules: List[GradingRule]
    ) -> float:
        """计算加权分数"""
        total_score = 0.0
        total_weight = 0.0
        
        for rule in rules:
            if rule.criteria in criteria_scores:
                score = criteria_scores[rule.criteria]
                total_score += score * rule.weight
                total_weight += rule.weight
        
        return total_score / total_weight if total_weight > 0 else 0.0
    
    def _score_to_grade(self, score: float, rule: GradingRule) -> ImpactLevel:
        """将分数转换为级别"""
        if score >= rule.threshold_critical:
            return ImpactLevel.CRITICAL
        elif score >= rule.threshold_high:
            return ImpactLevel.HIGH
        elif score >= rule.threshold_medium:
            return ImpactLevel.MEDIUM
        elif score >= rule.threshold_low:
            return ImpactLevel.LOW
        else:
            return ImpactLevel.NONE
    
    def _get_sort_value(self, graded_node: GradedNode, criteria: GradingCriteria) -> float:
        """获取排序值"""
        if criteria == GradingCriteria.IMPACT_SCORE:
            return graded_node.grade_score
        elif criteria == GradingCriteria.DISTANCE:
            return graded_node.node.distance_from_change
        elif criteria == GradingCriteria.NODE_TYPE:
            return self.node_type_weights.get(graded_node.node.node_type, 0.5)
        elif criteria == GradingCriteria.COMBINED:
            return graded_node.grade_score
        else:
            return graded_node.criteria_scores.get(criteria, 0.0)
    
    def _get_timestamp(self) -> str:
        """获取当前时间戳"""
        from datetime import datetime
        return datetime.now().isoformat()