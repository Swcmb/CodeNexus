"""
影响分析边界情况属性测试

**Feature: code-weaver, Property 4: 影响分析准确性**

测试影响分析在边界情况下的准确性：
- 空图、单节点图、循环依赖等特殊情况
- 极值输入和异常情况的处理
"""

import pytest
from hypothesis import given, strategies as st, assume, settings, HealthCheck
from typing import List, Dict, Set, Tuple
import random

from src.codenexus.services.impact_analyzer import (
    ImpactAnalyzer, ChangeType, ImpactLevel, ImpactAnalysisResult
)
from src.codenexus.database.mock_database import MockGraphDatabase
from src.codenexus.database.query_service import GraphQueryService
from src.codenexus.models.core import CodeGraph, GraphNode, GraphEdge, GraphMetadata
from src.codenexus.exceptions import codenexusError


class TestImpactAnalysisEdgeCases:
    """影响分析边界情况测试类"""
    
    def create_analyzer_setup(self):
        """创建影响分析器设置"""
        database = MockGraphDatabase()
        query_service = GraphQueryService(database)
        analyzer = ImpactAnalyzer(query_service)
        return analyzer, database
    
    def test_empty_graph_impact_analysis(self):
        """
        **Feature: code-weaver, Property 4: 影响分析准确性**
        
        测试空图的影响分析：
        - 空图应该正确处理，不产生错误
        """
        analyzer, database = self.create_analyzer_setup()
        
        # 创建空图
        empty_graph = CodeGraph(
            id='empty_graph',
            nodes=[],
            edges=[],
            metadata=GraphMetadata(
                node_count=0,
                edge_count=0,
                file_count=0,
                languages=[],
                node_types={},
                edge_types={}
            )
        )
        
        graph_name = database.store_graph(empty_graph)
        
        # 尝试分析不存在的节点应该抛出异常
        with pytest.raises(codenexusError):
            analyzer.analyze_impact(
                graph_name=graph_name,
                changed_node_id='nonexistent_node',
                change_type=ChangeType.MODIFY
            )
    
    def test_single_node_graph_impact_analysis(self):
        """
        **Feature: code-weaver, Property 4: 影响分析准确性**
        
        测试单节点图的影响分析：
        - 单节点图应该返回空的影响结果
        """
        analyzer, database = self.create_analyzer_setup()
        
        # 创建单节点图
        single_node = GraphNode(
            id='single_node',
            label='SingleNode',
            type='class',
            properties={'name': 'SingleNode', 'complexity': 1}
        )
        
        single_graph = CodeGraph(
            id='single_graph',
            nodes=[single_node],
            edges=[],
            metadata=GraphMetadata(
                node_count=1,
                edge_count=0,
                file_count=1,
                languages=['python'],
                node_types={'class': 1},
                edge_types={}
            )
        )
        
        graph_name = database.store_graph(single_graph)
        
        # 分析单节点
        result = analyzer.analyze_impact(
            graph_name=graph_name,
            changed_node_id='single_node',
            change_type=ChangeType.MODIFY
        )
        
        # 验证结果
        assert result.changed_node_id == 'single_node'
        assert result.total_affected_nodes == 0  # 没有其他节点受影响
        assert len(result.affected_nodes) == 0
        assert all(count == 0 for count in result.impact_summary.values())
    
    @given(st.integers(min_value=3, max_value=10))
    @settings(max_examples=15, deadline=None)
    def test_circular_dependency_impact_analysis(self, cycle_size):
        """
        **Feature: code-weaver, Property 4: 影响分析准确性**
        
        测试循环依赖的影响分析：
        - 循环依赖应该被正确处理，不产生无限循环
        """
        analyzer, database = self.create_analyzer_setup()
        
        # 创建循环依赖图
        nodes = []
        edges = []
        
        for i in range(cycle_size):
            node = GraphNode(
                id=f'node_{i}',
                label=f'Node{i}',
                type='class',
                properties={'name': f'Node{i}', 'complexity': 1}
            )
            nodes.append(node)
            
            # 创建循环边
            next_i = (i + 1) % cycle_size
            edge = GraphEdge(
                id=f'edge_{i}',
                source_id=f'node_{i}',
                target_id=f'node_{next_i}',
                type='depends',
                properties={'strength': 0.8}
            )
            edges.append(edge)
        
        # 创建图谱
        cycle_graph = CodeGraph(
            id='cycle_graph',
            nodes=nodes,
            edges=edges,
            metadata=GraphMetadata(
                node_count=len(nodes),
                edge_count=len(edges),
                file_count=len(nodes),
                languages=['python'],
                node_types={'class': len(nodes)},
                edge_types={'depends': len(edges)}
            )
        )
        
        graph_name = database.store_graph(cycle_graph)
        
        # 分析循环中的一个节点
        result = analyzer.analyze_impact(
            graph_name=graph_name,
            changed_node_id='node_0',
            change_type=ChangeType.MODIFY,
            max_depth=5
        )
        
        # 验证结果
        assert isinstance(result, ImpactAnalysisResult)
        assert result.changed_node_id == 'node_0'
        # 在循环依赖中，可能没有受影响的节点（取决于实现）
        assert result.total_affected_nodes >= 0
        assert result.total_affected_nodes <= cycle_size - 1  # 不包括自身
        
        # 验证没有无限循环（测试应该在合理时间内完成）
        for affected_node in result.affected_nodes:
            assert affected_node.distance_from_change <= 5  # 受深度限制
            
        # 验证基本结构正确性
        assert len(result.affected_nodes) == result.total_affected_nodes
        assert isinstance(result.impact_summary, dict)
        assert isinstance(result.critical_paths, list)
    
    @given(st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))))
    @settings(max_examples=20, deadline=None)
    def test_unicode_node_names_impact_analysis(self, unicode_name):
        """
        **Feature: code-weaver, Property 4: 影响分析准确性**
        
        测试Unicode节点名称的影响分析：
        - 包含Unicode字符的节点名称应该被正确处理
        """
        analyzer, database = self.create_analyzer_setup()
        
        # 创建包含Unicode字符的节点
        nodes = [
            GraphNode(
                id='unicode_node',
                label=unicode_name,
                type='class',
                properties={'name': unicode_name, 'complexity': 1}
            ),
            GraphNode(
                id='normal_node',
                label='NormalNode',
                type='class',
                properties={'name': 'NormalNode', 'complexity': 1}
            )
        ]
        
        edges = [
            GraphEdge(
                id='edge_1',
                source_id='unicode_node',
                target_id='normal_node',
                type='depends',
                properties={'strength': 0.8}
            )
        ]
        
        # 创建图谱
        unicode_graph = CodeGraph(
            id='unicode_graph',
            nodes=nodes,
            edges=edges,
            metadata=GraphMetadata(
                node_count=len(nodes),
                edge_count=len(edges),
                file_count=len(nodes),
                languages=['python'],
                node_types={'class': len(nodes)},
                edge_types={'depends': len(edges)}
            )
        )
        
        graph_name = database.store_graph(unicode_graph)
        
        # 分析Unicode节点
        result = analyzer.analyze_impact(
            graph_name=graph_name,
            changed_node_id='unicode_node',
            change_type=ChangeType.MODIFY
        )
        
        # 验证结果
        assert result.changed_node_id == 'unicode_node'
        assert result.total_affected_nodes >= 0
        
        # 验证Unicode名称被正确处理
        for affected_node in result.affected_nodes:
            assert isinstance(affected_node.node_name, str)
            assert len(affected_node.node_name) > 0
    
    @given(st.integers(min_value=0, max_value=10))
    @settings(max_examples=15, deadline=None)
    def test_extreme_depth_values(self, depth):
        """
        **Feature: code-weaver, Property 4: 影响分析准确性**
        
        测试极值深度参数：
        - 深度为0应该只返回直接依赖
        - 很大的深度值应该被正确处理
        """
        analyzer, database = self.create_analyzer_setup()
        
        # 创建线性链状图
        nodes = []
        edges = []
        chain_length = 5
        
        for i in range(chain_length):
            node = GraphNode(
                id=f'chain_node_{i}',
                label=f'ChainNode{i}',
                type='class',
                properties={'name': f'ChainNode{i}', 'complexity': 1}
            )
            nodes.append(node)
            
            if i > 0:
                edge = GraphEdge(
                    id=f'chain_edge_{i}',
                    source_id=f'chain_node_{i-1}',
                    target_id=f'chain_node_{i}',
                    type='depends',
                    properties={'strength': 0.8}
                )
                edges.append(edge)
        
        # 创建图谱
        chain_graph = CodeGraph(
            id='chain_graph',
            nodes=nodes,
            edges=edges,
            metadata=GraphMetadata(
                node_count=len(nodes),
                edge_count=len(edges),
                file_count=len(nodes),
                languages=['python'],
                node_types={'class': len(nodes)},
                edge_types={'depends': len(edges)}
            )
        )
        
        graph_name = database.store_graph(chain_graph)
        
        # 分析链的起始节点
        result = analyzer.analyze_impact(
            graph_name=graph_name,
            changed_node_id='chain_node_0',
            change_type=ChangeType.MODIFY,
            max_depth=depth
        )
        
        # 验证深度限制
        if depth == 0:
            # 深度为0应该没有受影响的节点（或只有直接相邻的）
            assert result.total_affected_nodes <= 1
        else:
            # 验证所有受影响节点的距离不超过指定深度
            for affected_node in result.affected_nodes:
                assert affected_node.distance_from_change <= depth
    
    def test_complex_metadata_impact_analysis(self):
        """
        **Feature: code-weaver, Property 4: 影响分析准确性**
        
        测试复杂元数据的影响分析：
        - 包含复杂属性的节点应该被正确处理
        """
        analyzer, database = self.create_analyzer_setup()
        
        # 创建包含复杂元数据的节点
        complex_node = GraphNode(
            id='complex_node',
            label='ComplexNode',
            type='class',
            properties={
                'name': 'ComplexNode',
                'complexity': 100,
                'file': '/very/long/path/to/file.py',
                'lines_of_code': 1000,
                'methods': ['method1', 'method2', 'method3'],
                'dependencies': {'external': ['numpy', 'pandas'], 'internal': ['module1', 'module2']},
                'metadata': {
                    'author': 'Developer',
                    'created': '2023-01-01',
                    'modified': '2023-12-01',
                    'version': '1.0.0'
                }
            }
        )
        
        simple_node = GraphNode(
            id='simple_node',
            label='SimpleNode',
            type='function',
            properties={'name': 'SimpleNode', 'complexity': 1}
        )
        
        edge = GraphEdge(
            id='complex_edge',
            source_id='complex_node',
            target_id='simple_node',
            type='calls',
            properties={
                'strength': 0.9,
                'call_count': 50,
                'last_called': '2023-12-01T10:00:00Z'
            }
        )
        
        # 创建图谱
        complex_graph = CodeGraph(
            id='complex_graph',
            nodes=[complex_node, simple_node],
            edges=[edge],
            metadata=GraphMetadata(
                node_count=2,
                edge_count=1,
                file_count=2,
                languages=['python'],
                node_types={'class': 1, 'function': 1},
                edge_types={'calls': 1}
            )
        )
        
        graph_name = database.store_graph(complex_graph)
        
        # 分析复杂节点
        result = analyzer.analyze_impact(
            graph_name=graph_name,
            changed_node_id='complex_node',
            change_type=ChangeType.MODIFY
        )
        
        # 验证结果
        assert result.changed_node_id == 'complex_node'
        assert result.total_affected_nodes >= 0
        
        # 验证复杂元数据不影响分析逻辑
        for affected_node in result.affected_nodes:
            assert affected_node.node_id in ['simple_node']
            assert 0 <= affected_node.impact_score <= 1
    
    @given(st.sampled_from(list(ChangeType)))
    @settings(max_examples=10, deadline=None)
    def test_all_change_types_consistency(self, change_type):
        """
        **Feature: code-weaver, Property 4: 影响分析准确性**
        
        测试所有变更类型的一致性：
        - 所有变更类型都应该产生有效的结果
        """
        analyzer, database = self.create_analyzer_setup()
        
        # 创建简单的测试图
        nodes = [
            GraphNode(
                id='source_node',
                label='SourceNode',
                type='class',
                properties={'name': 'SourceNode', 'complexity': 5}
            ),
            GraphNode(
                id='target_node',
                label='TargetNode',
                type='class',
                properties={'name': 'TargetNode', 'complexity': 3}
            )
        ]
        
        edges = [
            GraphEdge(
                id='test_edge',
                source_id='source_node',
                target_id='target_node',
                type='depends',
                properties={'strength': 0.8}
            )
        ]
        
        # 创建图谱
        test_graph = CodeGraph(
            id='test_graph',
            nodes=nodes,
            edges=edges,
            metadata=GraphMetadata(
                node_count=len(nodes),
                edge_count=len(edges),
                file_count=len(nodes),
                languages=['python'],
                node_types={'class': len(nodes)},
                edge_types={'depends': len(edges)}
            )
        )
        
        graph_name = database.store_graph(test_graph)
        
        # 测试每种变更类型
        result = analyzer.analyze_impact(
            graph_name=graph_name,
            changed_node_id='source_node',
            change_type=change_type
        )
        
        # 验证基本结果结构
        assert isinstance(result, ImpactAnalysisResult)
        assert result.changed_node_id == 'source_node'
        assert result.change_type == change_type
        assert result.total_affected_nodes >= 0
        assert len(result.affected_nodes) == result.total_affected_nodes
        assert isinstance(result.impact_summary, dict)
        assert isinstance(result.critical_paths, list)
        
        # 验证风险评估也能处理所有变更类型
        risk_assessment = analyzer.assess_change_risk(
            graph_name=graph_name,
            changed_node_id='source_node',
            change_type=change_type
        )
        
        assert 'risk_level' in risk_assessment
        assert 'risk_score' in risk_assessment
        assert 0 <= risk_assessment['risk_score'] <= 1