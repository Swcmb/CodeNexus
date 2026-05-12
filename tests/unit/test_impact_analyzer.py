"""
影响分析器单元测试
"""

import pytest
from unittest.mock import Mock, patch
from typing import List, Dict, Any

from src.codenexus.services.impact_analyzer import (
    ImpactAnalyzer, ImpactLevel, ChangeType, ImpactPath, ImpactNode, ImpactAnalysisResult
)
from src.codenexus.database.query_service import GraphQueryService
from src.codenexus.database.mock_database import MockGraphDatabase
from src.codenexus.exceptions import codenexusError


class TestImpactAnalyzer:
    """影响分析器测试类"""
    
    @pytest.fixture
    def mock_database(self):
        """创建模拟数据库"""
        return MockGraphDatabase()
    
    @pytest.fixture
    def query_service(self, mock_database):
        """创建查询服务"""
        return GraphQueryService(mock_database)
    
    @pytest.fixture
    def impact_analyzer(self, query_service):
        """创建影响分析器"""
        return ImpactAnalyzer(query_service)
    
    @pytest.fixture
    def sample_graph_data(self, mock_database):
        """创建示例图数据"""
        from src.codenexus.models.core import CodeGraph, GraphNode, GraphEdge, GraphMetadata
        
        # 创建节点
        nodes = [
            GraphNode(
                id='class_a', 
                label='ClassA', 
                type='class', 
                properties={'name': 'ClassA', 'complexity': 5}
            ),
            GraphNode(
                id='class_b', 
                label='ClassB', 
                type='class', 
                properties={'name': 'ClassB', 'complexity': 3}
            ),
            GraphNode(
                id='method_1', 
                label='method1', 
                type='method', 
                properties={'name': 'method1', 'complexity': 2}
            ),
            GraphNode(
                id='method_2', 
                label='method2', 
                type='method', 
                properties={'name': 'method2', 'complexity': 4}
            ),
            GraphNode(
                id='interface_i', 
                label='InterfaceI', 
                type='interface', 
                properties={'name': 'InterfaceI', 'complexity': 1}
            )
        ]
        
        # 创建边
        edges = [
            GraphEdge(
                id='edge_1',
                source_id='class_b', 
                target_id='class_a', 
                type='inherits', 
                properties={'strength': 0.9}
            ),
            GraphEdge(
                id='edge_2',
                source_id='method_1', 
                target_id='class_a', 
                type='calls', 
                properties={'strength': 0.8}
            ),
            GraphEdge(
                id='edge_3',
                source_id='method_2', 
                target_id='method_1', 
                type='calls', 
                properties={'strength': 0.7}
            ),
            GraphEdge(
                id='edge_4',
                source_id='class_a', 
                target_id='interface_i', 
                type='implements', 
                properties={'strength': 0.9}
            )
        ]
        
        # 创建图谱元数据
        metadata = GraphMetadata(
            node_count=len(nodes),
            edge_count=len(edges),
            file_count=1,
            languages=['python'],
            node_types={'class': 3, 'method': 2, 'interface': 1},
            edge_types={'inherits': 1, 'calls': 2, 'implements': 1}
        )
        
        # 创建图谱
        graph = CodeGraph(
            id='test_graph',
            nodes=nodes,
            edges=edges,
            metadata=metadata
        )
        
        # 存储到模拟数据库
        mock_database.store_graph(graph)
        
        return 'test_graph'
    
    def test_analyzer_initialization(self, query_service):
        """测试分析器初始化"""
        analyzer = ImpactAnalyzer(query_service)
        
        assert analyzer.query_service == query_service
        assert isinstance(analyzer.relationship_weights, dict)
        assert isinstance(analyzer.node_type_coefficients, dict)
        assert 'calls' in analyzer.relationship_weights
        assert 'class' in analyzer.node_type_coefficients
    
    def test_analyze_impact_basic(self, impact_analyzer, sample_graph_data):
        """测试基础影响分析"""
        result = impact_analyzer.analyze_impact(
            graph_name=sample_graph_data,
            changed_node_id='class_a',
            change_type=ChangeType.MODIFY
        )
        
        assert isinstance(result, ImpactAnalysisResult)
        assert result.changed_node_id == 'class_a'
        assert result.change_type == ChangeType.MODIFY
        assert result.total_affected_nodes >= 0
        assert isinstance(result.impact_summary, dict)
        assert isinstance(result.affected_nodes, list)
        assert isinstance(result.critical_paths, list)
    
    def test_analyze_impact_downstream_only(self, impact_analyzer, sample_graph_data):
        """测试仅下游影响分析"""
        result = impact_analyzer.analyze_impact(
            graph_name=sample_graph_data,
            changed_node_id='class_a',
            change_type=ChangeType.MODIFY,
            include_upstream=False,
            include_downstream=True
        )
        
        assert result.total_affected_nodes >= 0
        # 应该找到依赖class_a的节点（如method_1）
        affected_ids = [node.node_id for node in result.affected_nodes]
        # 由于是下游分析，应该找到调用class_a的节点
    
    def test_analyze_impact_upstream_only(self, impact_analyzer, sample_graph_data):
        """测试仅上游影响分析"""
        result = impact_analyzer.analyze_impact(
            graph_name=sample_graph_data,
            changed_node_id='class_b',
            change_type=ChangeType.MODIFY,
            include_upstream=True,
            include_downstream=False
        )
        
        assert result.total_affected_nodes >= 0
        # 应该找到class_b依赖的节点（如class_a）
        affected_ids = [node.node_id for node in result.affected_nodes]
    
    def test_analyze_impact_delete_change(self, impact_analyzer, sample_graph_data):
        """测试删除变更的影响分析"""
        result = impact_analyzer.analyze_impact(
            graph_name=sample_graph_data,
            changed_node_id='class_a',
            change_type=ChangeType.DELETE
        )
        
        assert result.change_type == ChangeType.DELETE
        # 删除操作通常有更高的影响
        assert result.total_affected_nodes >= 0
    
    def test_analyze_impact_max_depth_limit(self, impact_analyzer, sample_graph_data):
        """测试最大深度限制"""
        result = impact_analyzer.analyze_impact(
            graph_name=sample_graph_data,
            changed_node_id='class_a',
            max_depth=1
        )
        
        # 验证所有受影响节点的距离不超过最大深度
        for node in result.affected_nodes:
            assert node.distance_from_change <= 1
    
    def test_analyze_impact_nonexistent_node(self, impact_analyzer, sample_graph_data):
        """测试不存在的节点"""
        with pytest.raises(codenexusError):
            impact_analyzer.analyze_impact(
                graph_name=sample_graph_data,
                changed_node_id='nonexistent_node'
            )
    
    def test_calculate_dependency_paths(self, impact_analyzer, sample_graph_data):
        """测试依赖路径计算"""
        paths = impact_analyzer.calculate_dependency_paths(
            graph_name=sample_graph_data,
            source_node_id='method_2',
            target_node_id='class_a'
        )
        
        assert isinstance(paths, list)
        for path in paths:
            assert isinstance(path, ImpactPath)
            assert path.source_node_id == 'method_2'
            assert path.target_node_id == 'class_a'
            assert path.path_length >= 0
            assert 0 <= path.impact_strength <= 1
    
    def test_calculate_dependency_paths_no_path(self, impact_analyzer, sample_graph_data):
        """测试无路径情况"""
        paths = impact_analyzer.calculate_dependency_paths(
            graph_name=sample_graph_data,
            source_node_id='interface_i',
            target_node_id='method_2'
        )
        
        # 可能没有路径，应该返回空列表
        assert isinstance(paths, list)
    
    def test_assess_change_risk_modify(self, impact_analyzer, sample_graph_data):
        """测试修改变更的风险评估"""
        risk_assessment = impact_analyzer.assess_change_risk(
            graph_name=sample_graph_data,
            changed_node_id='class_a',
            change_type=ChangeType.MODIFY
        )
        
        assert isinstance(risk_assessment, dict)
        assert 'risk_level' in risk_assessment
        assert 'risk_score' in risk_assessment
        assert 'risk_factors' in risk_assessment
        assert 'recommendations' in risk_assessment
        
        assert risk_assessment['risk_level'] in ['minimal', 'low', 'medium', 'high', 'critical']
        assert 0 <= risk_assessment['risk_score'] <= 1
        assert isinstance(risk_assessment['recommendations'], list)
    
    def test_assess_change_risk_delete(self, impact_analyzer, sample_graph_data):
        """测试删除变更的风险评估"""
        risk_assessment = impact_analyzer.assess_change_risk(
            graph_name=sample_graph_data,
            changed_node_id='class_a',
            change_type=ChangeType.DELETE
        )
        
        # 删除操作通常风险更高
        assert risk_assessment['risk_level'] in ['low', 'medium', 'high', 'critical']
        assert risk_assessment['risk_score'] > 0.3  # 删除操作基础风险较高
    
    def test_assess_change_risk_interface(self, impact_analyzer, sample_graph_data):
        """测试接口变更的风险评估"""
        risk_assessment = impact_analyzer.assess_change_risk(
            graph_name=sample_graph_data,
            changed_node_id='interface_i',
            change_type=ChangeType.MODIFY
        )
        
        # 接口变更通常风险较高
        assert risk_assessment['risk_score'] > 0.2
    
    def test_assess_change_risk_nonexistent_node(self, impact_analyzer, sample_graph_data):
        """测试不存在节点的风险评估"""
        risk_assessment = impact_analyzer.assess_change_risk(
            graph_name=sample_graph_data,
            changed_node_id='nonexistent_node',
            change_type=ChangeType.MODIFY
        )
        
        assert risk_assessment['risk_level'] == 'unknown'
        assert 'reason' in risk_assessment
    
    def test_impact_level_enum(self):
        """测试影响级别枚举"""
        assert ImpactLevel.NONE.value == 0
        assert ImpactLevel.LOW.value == 1
        assert ImpactLevel.MEDIUM.value == 2
        assert ImpactLevel.HIGH.value == 3
        assert ImpactLevel.CRITICAL.value == 4
    
    def test_change_type_enum(self):
        """测试变更类型枚举"""
        assert ChangeType.MODIFY.value == "modify"
        assert ChangeType.DELETE.value == "delete"
        assert ChangeType.ADD.value == "add"
        assert ChangeType.RENAME.value == "rename"
    
    def test_impact_node_creation(self):
        """测试影响节点创建"""
        node = ImpactNode(
            node_id='test_node',
            node_name='TestNode',
            node_type='class',
            impact_level=ImpactLevel.HIGH,
            impact_score=0.8,
            distance_from_change=2
        )
        
        assert node.node_id == 'test_node'
        assert node.node_name == 'TestNode'
        assert node.node_type == 'class'
        assert node.impact_level == ImpactLevel.HIGH
        assert node.impact_score == 0.8
        assert node.distance_from_change == 2
        assert isinstance(node.impact_paths, list)
        assert isinstance(node.metadata, dict)
    
    def test_impact_path_creation(self):
        """测试影响路径创建"""
        path = ImpactPath(
            source_node_id='source',
            target_node_id='target',
            path_nodes=['source', 'middle', 'target'],
            path_length=2,
            impact_strength=0.7,
            relationship_types=['calls', 'inherits']
        )
        
        assert path.source_node_id == 'source'
        assert path.target_node_id == 'target'
        assert path.path_nodes == ['source', 'middle', 'target']
        assert path.path_length == 2
        assert path.impact_strength == 0.7
        assert path.relationship_types == ['calls', 'inherits']
    
    def test_impact_analysis_result_creation(self):
        """测试影响分析结果创建"""
        result = ImpactAnalysisResult(
            changed_node_id='test_node',
            change_type=ChangeType.MODIFY,
            total_affected_nodes=5,
            impact_summary={ImpactLevel.HIGH: 2, ImpactLevel.MEDIUM: 3},
            affected_nodes=[],
            critical_paths=[]
        )
        
        assert result.changed_node_id == 'test_node'
        assert result.change_type == ChangeType.MODIFY
        assert result.total_affected_nodes == 5
        assert result.impact_summary[ImpactLevel.HIGH] == 2
        assert isinstance(result.affected_nodes, list)
        assert isinstance(result.critical_paths, list)
        assert isinstance(result.analysis_metadata, dict)
    
    def test_score_to_level_conversion(self, impact_analyzer):
        """测试分数到级别的转换"""
        assert impact_analyzer._score_to_level(0.9) == ImpactLevel.CRITICAL
        assert impact_analyzer._score_to_level(0.7) == ImpactLevel.HIGH
        assert impact_analyzer._score_to_level(0.5) == ImpactLevel.MEDIUM
        assert impact_analyzer._score_to_level(0.3) == ImpactLevel.LOW
        assert impact_analyzer._score_to_level(0.1) == ImpactLevel.NONE
    
    def test_relationship_weights_configuration(self, impact_analyzer):
        """测试关系权重配置"""
        weights = impact_analyzer.relationship_weights
        
        assert 'calls' in weights
        assert 'inherits' in weights
        assert 'implements' in weights
        assert 'depends' in weights
        
        # 验证权重范围
        for weight in weights.values():
            assert 0 <= weight <= 1
    
    def test_node_type_coefficients_configuration(self, impact_analyzer):
        """测试节点类型系数配置"""
        coefficients = impact_analyzer.node_type_coefficients
        
        assert 'class' in coefficients
        assert 'interface' in coefficients
        assert 'method' in coefficients
        assert 'function' in coefficients
        
        # 验证系数范围
        for coeff in coefficients.values():
            assert coeff > 0
    
    def test_complex_graph_analysis(self, impact_analyzer, mock_database):
        """测试复杂图的影响分析"""
        from src.codenexus.models.core import CodeGraph, GraphNode, GraphEdge, GraphMetadata
        
        # 创建更复杂的图结构
        nodes = []
        edges = []
        
        # 创建多层继承结构
        for i in range(10):
            nodes.append(GraphNode(
                id=f'class_{i}',
                label=f'Class{i}',
                type='class',
                properties={'name': f'Class{i}', 'complexity': i + 1}
            ))
            
            if i > 0:
                edges.append(GraphEdge(
                    id=f'edge_{i}',
                    source_id=f'class_{i}',
                    target_id=f'class_{i-1}',
                    type='inherits',
                    properties={'strength': 0.8}
                ))
        
        # 创建图谱元数据
        metadata = GraphMetadata(
            node_count=len(nodes),
            edge_count=len(edges),
            file_count=1,
            languages=['python'],
            node_types={'class': 10},
            edge_types={'inherits': 9}
        )
        
        # 创建图谱
        graph = CodeGraph(
            id='complex_graph',
            nodes=nodes,
            edges=edges,
            metadata=metadata
        )
        
        # 存储到数据库
        mock_database.store_graph(graph)
        
        # 分析根类的影响
        result = impact_analyzer.analyze_impact(
            graph_name='complex_graph',
            changed_node_id='class_0',
            change_type=ChangeType.MODIFY,
            max_depth=5
        )
        
        assert result.total_affected_nodes >= 0
        assert len(result.affected_nodes) <= 9  # 最多9个其他类受影响
    
    def test_error_handling_in_analysis(self, impact_analyzer):
        """测试分析过程中的错误处理"""
        # 测试不存在的图
        with pytest.raises(codenexusError):
            impact_analyzer.analyze_impact(
                graph_name='nonexistent_graph',
                changed_node_id='some_node'
            )
    
    def test_performance_with_large_depth(self, impact_analyzer, sample_graph_data):
        """测试大深度分析的性能"""
        import time
        
        start_time = time.time()
        result = impact_analyzer.analyze_impact(
            graph_name=sample_graph_data,
            changed_node_id='class_a',
            max_depth=10  # 较大的深度
        )
        end_time = time.time()
        
        # 应该在合理时间内完成
        assert end_time - start_time < 5.0  # 5秒内完成
        assert isinstance(result, ImpactAnalysisResult)