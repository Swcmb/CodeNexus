"""
影响分级器单元测试
"""

import pytest
from unittest.mock import Mock, patch

from src.codenexus.services.impact_grader import (
    ImpactGrader, GradingCriteria, SortOrder, GradingRule, SortingConfig, GradedNode
)
from src.codenexus.services.impact_analyzer import (
    ImpactAnalysisResult, ImpactNode, ImpactPath, ImpactLevel, ChangeType
)


class TestImpactGrader:
    """影响分级器测试类"""
    
    def setup_method(self):
        """设置测试环境"""
        self.grader = ImpactGrader()
        
        # 创建测试节点
        self.test_nodes = [
            ImpactNode(
                node_id="node1",
                node_name="TestClass1",
                node_type="class",
                impact_level=ImpactLevel.HIGH,
                impact_score=0.8,
                distance_from_change=1
            ),
            ImpactNode(
                node_id="node2",
                node_name="TestMethod1",
                node_type="method",
                impact_level=ImpactLevel.MEDIUM,
                impact_score=0.6,
                distance_from_change=2
            ),
            ImpactNode(
                node_id="node3",
                node_name="TestInterface1",
                node_type="interface",
                impact_level=ImpactLevel.LOW,
                impact_score=0.3,
                distance_from_change=3
            )
        ]
        
        # 创建测试分析结果
        self.test_analysis_result = ImpactAnalysisResult(
            changed_node_id="changed_node",
            change_type=ChangeType.MODIFY,
            total_affected_nodes=3,
            impact_summary={
                ImpactLevel.HIGH: 1,
                ImpactLevel.MEDIUM: 1,
                ImpactLevel.LOW: 1
            },
            affected_nodes=self.test_nodes,
            critical_paths=[]
        )
    
    def test_grade_impact_nodes_default_rules(self):
        """测试使用默认规则进行节点分级"""
        graded_nodes = self.grader.grade_impact_nodes(self.test_analysis_result)
        
        # 验证基本结构
        assert len(graded_nodes) == 3
        assert all(isinstance(node, GradedNode) for node in graded_nodes)
        
        # 验证分级结果
        for graded_node in graded_nodes:
            assert hasattr(graded_node, 'final_grade')
            assert hasattr(graded_node, 'grade_score')
            assert hasattr(graded_node, 'criteria_scores')
            assert isinstance(graded_node.criteria_scores, dict)
            
            # 验证维度分数
            assert GradingCriteria.IMPACT_SCORE in graded_node.criteria_scores
            assert GradingCriteria.DISTANCE in graded_node.criteria_scores
            assert GradingCriteria.NODE_TYPE in graded_node.criteria_scores
            assert GradingCriteria.CONNECTIVITY in graded_node.criteria_scores
    
    def test_grade_impact_nodes_custom_rules(self):
        """测试使用自定义规则进行节点分级"""
        custom_rules = [
            GradingRule(GradingCriteria.IMPACT_SCORE, 0.6),
            GradingRule(GradingCriteria.NODE_TYPE, 0.4)
        ]
        
        graded_nodes = self.grader.grade_impact_nodes(
            self.test_analysis_result,
            grading_rules=custom_rules
        )
        
        # 验证使用了自定义规则
        assert len(graded_nodes) == 3
        
        # 验证分级结果受自定义规则影响
        for graded_node in graded_nodes:
            assert graded_node.grade_score >= 0.0
            assert graded_node.grade_score <= 1.0
    
    def test_sort_graded_nodes_by_score(self):
        """测试按分数排序分级节点"""
        graded_nodes = self.grader.grade_impact_nodes(self.test_analysis_result)
        
        sorting_config = SortingConfig(
            primary_criteria=GradingCriteria.IMPACT_SCORE,
            primary_order=SortOrder.DESCENDING
        )
        
        sorted_nodes = self.grader.sort_graded_nodes(graded_nodes, sorting_config)
        
        # 验证排序结果
        assert len(sorted_nodes) == 3
        
        # 验证按分数降序排列
        for i in range(len(sorted_nodes) - 1):
            assert sorted_nodes[i].grade_score >= sorted_nodes[i + 1].grade_score
        
        # 验证排名
        for i, node in enumerate(sorted_nodes):
            assert node.rank == i + 1
    
    def test_sort_graded_nodes_by_distance(self):
        """测试按距离排序分级节点"""
        graded_nodes = self.grader.grade_impact_nodes(self.test_analysis_result)
        
        sorting_config = SortingConfig(
            primary_criteria=GradingCriteria.DISTANCE,
            primary_order=SortOrder.ASCENDING
        )
        
        sorted_nodes = self.grader.sort_graded_nodes(graded_nodes, sorting_config)
        
        # 验证按距离升序排列
        for i in range(len(sorted_nodes) - 1):
            assert sorted_nodes[i].node.distance_from_change <= sorted_nodes[i + 1].node.distance_from_change
    
    def test_sort_graded_nodes_multi_criteria(self):
        """测试多维度排序"""
        graded_nodes = self.grader.grade_impact_nodes(self.test_analysis_result)
        
        sorting_config = SortingConfig(
            primary_criteria=GradingCriteria.IMPACT_SCORE,
            primary_order=SortOrder.DESCENDING,
            secondary_criteria=GradingCriteria.DISTANCE,
            secondary_order=SortOrder.ASCENDING
        )
        
        sorted_nodes = self.grader.sort_graded_nodes(graded_nodes, sorting_config)
        
        # 验证排序结果
        assert len(sorted_nodes) == 3
        assert all(node.rank > 0 for node in sorted_nodes)
    
    def test_create_grade_distribution_report(self):
        """测试创建分级分布报告"""
        graded_nodes = self.grader.grade_impact_nodes(self.test_analysis_result)
        
        report = self.grader.create_grade_distribution_report(graded_nodes)
        
        # 验证报告结构
        assert "distribution" in report
        assert "total_nodes" in report
        assert "grade_changes" in report
        assert "change_percentage" in report
        assert "grade_transition_matrix" in report
        assert "top_nodes" in report
        
        # 验证分布数据
        distribution = report["distribution"]
        assert len(distribution) == len(ImpactLevel)
        
        for level_data in distribution:
            assert "level" in level_data
            assert "count" in level_data
            assert "percentage" in level_data
            assert "avg_score" in level_data
        
        # 验证总节点数
        assert report["total_nodes"] == 3
    
    def test_create_multi_criteria_ranking(self):
        """测试创建多维度排名"""
        graded_nodes = self.grader.grade_impact_nodes(self.test_analysis_result)
        
        ranking = self.grader.create_multi_criteria_ranking(graded_nodes)
        
        # 验证排名结构
        assert "criteria_rankings" in ranking
        assert "comprehensive_ranking" in ranking
        assert "weights_used" in ranking
        assert "total_nodes" in ranking
        
        # 验证维度排名
        criteria_rankings = ranking["criteria_rankings"]
        assert GradingCriteria.IMPACT_SCORE.value in criteria_rankings
        assert GradingCriteria.DISTANCE.value in criteria_rankings
        assert GradingCriteria.NODE_TYPE.value in criteria_rankings
        
        # 验证综合排名
        comprehensive_ranking = ranking["comprehensive_ranking"]
        assert len(comprehensive_ranking) == 3
        
        for rank_data in comprehensive_ranking:
            assert "node_id" in rank_data
            assert "final_grade" in rank_data
            assert "grade_score" in rank_data
            assert "rank" in rank_data
            assert "criteria_breakdown" in rank_data
    
    def test_grading_criteria_enum(self):
        """测试分级标准枚举"""
        assert GradingCriteria.IMPACT_SCORE.value == "impact_score"
        assert GradingCriteria.DISTANCE.value == "distance_from_change"
        assert GradingCriteria.NODE_TYPE.value == "node_type"
        assert GradingCriteria.CONNECTIVITY.value == "connectivity"
        assert GradingCriteria.COMBINED.value == "combined"
    
    def test_sort_order_enum(self):
        """测试排序顺序枚举"""
        assert SortOrder.ASCENDING.value == "asc"
        assert SortOrder.DESCENDING.value == "desc"
    
    def test_grading_rule_dataclass(self):
        """测试分级规则数据类"""
        rule = GradingRule(
            criteria=GradingCriteria.IMPACT_SCORE,
            weight=0.5,
            threshold_critical=0.9,
            threshold_high=0.7,
            threshold_medium=0.5,
            threshold_low=0.3
        )
        
        assert rule.criteria == GradingCriteria.IMPACT_SCORE
        assert rule.weight == 0.5
        assert rule.threshold_critical == 0.9
        assert rule.threshold_high == 0.7
        assert rule.threshold_medium == 0.5
        assert rule.threshold_low == 0.3
    
    def test_sorting_config_dataclass(self):
        """测试排序配置数据类"""
        config = SortingConfig(
            primary_criteria=GradingCriteria.IMPACT_SCORE,
            primary_order=SortOrder.DESCENDING,
            secondary_criteria=GradingCriteria.DISTANCE,
            secondary_order=SortOrder.ASCENDING
        )
        
        assert config.primary_criteria == GradingCriteria.IMPACT_SCORE
        assert config.primary_order == SortOrder.DESCENDING
        assert config.secondary_criteria == GradingCriteria.DISTANCE
        assert config.secondary_order == SortOrder.ASCENDING
    
    def test_graded_node_dataclass(self):
        """测试分级节点数据类"""
        node = self.test_nodes[0]
        graded_node = GradedNode(
            node=node,
            final_grade=ImpactLevel.CRITICAL,
            grade_score=0.9,
            criteria_scores={GradingCriteria.IMPACT_SCORE: 0.8},
            rank=1
        )
        
        assert graded_node.node == node
        assert graded_node.final_grade == ImpactLevel.CRITICAL
        assert graded_node.grade_score == 0.9
        assert graded_node.rank == 1
        assert GradingCriteria.IMPACT_SCORE in graded_node.criteria_scores
    
    def test_node_type_weights(self):
        """测试节点类型权重"""
        # 验证接口权重最高
        assert self.grader.node_type_weights['interface'] == 1.0
        
        # 验证类权重较高
        assert self.grader.node_type_weights['class'] == 0.9
        
        # 验证变量权重较低
        assert self.grader.node_type_weights['variable'] == 0.5
    
    def test_calculate_criteria_scores(self):
        """测试计算维度分数"""
        node = self.test_nodes[0]  # class节点
        connectivity_data = {"node1": 5, "node2": 3, "node3": 1}
        
        scores = self.grader._calculate_criteria_scores(
            node, self.test_analysis_result, connectivity_data
        )
        
        # 验证所有维度都有分数
        assert GradingCriteria.IMPACT_SCORE in scores
        assert GradingCriteria.DISTANCE in scores
        assert GradingCriteria.NODE_TYPE in scores
        assert GradingCriteria.CONNECTIVITY in scores
        
        # 验证分数范围
        for score in scores.values():
            assert 0.0 <= score <= 1.0
        
        # 验证影响分数维度
        assert scores[GradingCriteria.IMPACT_SCORE] == node.impact_score
        
        # 验证节点类型维度
        assert scores[GradingCriteria.NODE_TYPE] == self.grader.node_type_weights['class']
    
    def test_score_to_grade_conversion(self):
        """测试分数到级别的转换"""
        rule = GradingRule(GradingCriteria.IMPACT_SCORE, 1.0)
        
        assert self.grader._score_to_grade(0.9, rule) == ImpactLevel.CRITICAL
        assert self.grader._score_to_grade(0.7, rule) == ImpactLevel.HIGH
        assert self.grader._score_to_grade(0.5, rule) == ImpactLevel.MEDIUM
        assert self.grader._score_to_grade(0.3, rule) == ImpactLevel.LOW
        assert self.grader._score_to_grade(0.1, rule) == ImpactLevel.NONE
    
    def test_get_sort_value(self):
        """测试获取排序值"""
        graded_node = GradedNode(
            node=self.test_nodes[0],
            final_grade=ImpactLevel.HIGH,
            grade_score=0.8,
            criteria_scores={GradingCriteria.IMPACT_SCORE: 0.8}
        )
        
        # 测试不同维度的排序值
        assert self.grader._get_sort_value(graded_node, GradingCriteria.IMPACT_SCORE) == 0.8
        assert self.grader._get_sort_value(graded_node, GradingCriteria.DISTANCE) == 1
        assert self.grader._get_sort_value(graded_node, GradingCriteria.NODE_TYPE) == 0.9
        assert self.grader._get_sort_value(graded_node, GradingCriteria.COMBINED) == 0.8
    
    def test_grade_with_connectivity_data(self):
        """测试带连接度数据的分级"""
        connectivity_data = {
            "node1": 10,  # 高连接度
            "node2": 5,   # 中等连接度
            "node3": 1    # 低连接度
        }
        
        graded_nodes = self.grader.grade_impact_nodes(
            self.test_analysis_result,
            connectivity_data=connectivity_data
        )
        
        # 验证连接度影响分级
        node1_graded = next(n for n in graded_nodes if n.node.node_id == "node1")
        node3_graded = next(n for n in graded_nodes if n.node.node_id == "node3")
        
        # 高连接度节点的连接度分数应该更高
        assert (node1_graded.criteria_scores[GradingCriteria.CONNECTIVITY] > 
                node3_graded.criteria_scores[GradingCriteria.CONNECTIVITY])
    
    def test_empty_nodes_handling(self):
        """测试空节点列表的处理"""
        empty_result = ImpactAnalysisResult(
            changed_node_id="test",
            change_type=ChangeType.MODIFY,
            total_affected_nodes=0,
            impact_summary={},
            affected_nodes=[],
            critical_paths=[]
        )
        
        graded_nodes = self.grader.grade_impact_nodes(empty_result)
        assert len(graded_nodes) == 0
        
        report = self.grader.create_grade_distribution_report(graded_nodes)
        assert report["total_nodes"] == 0
        
        ranking = self.grader.create_multi_criteria_ranking(graded_nodes)
        assert ranking["total_nodes"] == 0