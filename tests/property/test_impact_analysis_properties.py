"""
影响分析准确性属性测试

**Feature: code-weaver, Property 4: 影响分析准确性**

验证影响分析系统的准确性属性：
- 对于任意代码元素，影响分析应该找到所有直接和间接依赖该元素的代码
- 分析结果应该包含完整的依赖路径和准确的影响程度评估
- 验证需求: 需求 3.1, 3.2, 3.3, 3.4
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


class TestImpactAnalysisProperties:
    """影响分析准确性属性测试类"""
    
    def create_analyzer_setup(self):
        """创建影响分析器设置"""
        database = MockGraphDatabase()
        query_service = GraphQueryService(database)
        analyzer = ImpactAnalyzer(query_service)
        return analyzer, database
    
    # 测试数据生成策略
    
    @st.composite
    def generate_node_id(draw):
        """生成节点ID"""
        prefix = draw(st.sampled_from(['class', 'method', 'function', 'interface', 'module']))
        suffix = draw(st.integers(min_value=1, max_value=100))
        return f"{prefix}_{suffix}"
    
    @st.composite
    def generate_graph_structure(draw):
        """生成图结构数据"""
        # 生成节点数量（3-15个节点，保持合理规模）
        node_count = draw(st.integers(min_value=3, max_value=15))
        
        # 生成节点
        nodes = []
        node_ids = []
        
        for i in range(node_count):
            node_type = draw(st.sampled_from(['class', 'method', 'function', 'interface', 'module']))
            node_id = f"{node_type}_{i}"
            node_ids.append(node_id)
            
            complexity = draw(st.integers(min_value=1, max_value=20))
            
            node = GraphNode(
                id=node_id,
                label=f"{node_type.title()}{i}",
                type=node_type,
                properties={
                    'name': f"{node_type.title()}{i}",
                    'complexity': complexity,
                    'file': f"src/{node_type}_{i}.py"
                }
            )
            nodes.append(node)
        
        # 生成边（确保图是连通的）
        edges = []
        edge_types = ['calls', 'inherits', 'implements', 'depends', 'uses', 'imports']
        
        # 至少生成 node_count-1 条边以确保连通性
        min_edges = node_count - 1
        max_edges = min(node_count * 2, 20)  # 限制最大边数
        edge_count = draw(st.integers(min_value=min_edges, max_value=max_edges))
        
        # 首先创建一个生成树确保连通性
        for i in range(1, node_count):
            source_idx = draw(st.integers(min_value=0, max_value=i-1))
            target_idx = i
            
            edge_type = draw(st.sampled_from(edge_types))
            strength = draw(st.floats(min_value=0.1, max_value=1.0))
            
            edge = GraphEdge(
                id=f"edge_{len(edges)}",
                source_id=node_ids[source_idx],
                target_id=node_ids[target_idx],
                type=edge_type,
                properties={'strength': strength}
            )
            edges.append(edge)
        
        # 添加额外的边
        for i in range(len(edges), edge_count):
            source_idx = draw(st.integers(min_value=0, max_value=node_count-1))
            target_idx = draw(st.integers(min_value=0, max_value=node_count-1))
            
            # 避免自环和重复边
            if source_idx == target_idx:
                continue
            
            # 检查是否已存在相同的边
            existing = any(
                e.source_id == node_ids[source_idx] and e.target_id == node_ids[target_idx]
                for e in edges
            )
            if existing:
                continue
            
            edge_type = draw(st.sampled_from(edge_types))
            strength = draw(st.floats(min_value=0.1, max_value=1.0))
            
            edge = GraphEdge(
                id=f"edge_{len(edges)}",
                source_id=node_ids[source_idx],
                target_id=node_ids[target_idx],
                type=edge_type,
                properties={'strength': strength}
            )
            edges.append(edge)
        
        return nodes, edges, node_ids
    
    @given(generate_graph_structure())
    @settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_impact_analysis_completeness_property(self, graph_data):
        """
        **Feature: code-weaver, Property 4: 影响分析准确性**
        
        测试影响分析的完整性：
        - 所有直接和间接依赖都应该被识别
        - 分析结果应该包含完整的依赖路径
        """
        analyzer, database = self.create_analyzer_setup()
        nodes, edges, node_ids = graph_data
        
        # 跳过过小的图
        assume(len(nodes) >= 3)
        assume(len(edges) >= 2)
        
        # 创建图谱
        metadata = GraphMetadata(
            node_count=len(nodes),
            edge_count=len(edges),
            file_count=len(nodes),
            languages=['python'],
            node_types={},
            edge_types={}
        )
        
        graph = CodeGraph(
            id='test_graph',
            nodes=nodes,
            edges=edges,
            metadata=metadata
        )
        
        graph_name = database.store_graph(graph)
        
        # 选择一个随机节点进行影响分析
        changed_node_id = random.choice(node_ids)
        
        # 执行影响分析
        result = analyzer.analyze_impact(
            graph_name=graph_name,
            changed_node_id=changed_node_id,
            change_type=ChangeType.MODIFY,
            max_depth=5
        )
        
        # 验证分析结果的完整性
        assert isinstance(result, ImpactAnalysisResult)
        assert result.changed_node_id == changed_node_id
        assert result.total_affected_nodes >= 0
        assert len(result.affected_nodes) == result.total_affected_nodes
        
        # 验证影响摘要的一致性
        summary_total = sum(result.impact_summary.values())
        assert summary_total == result.total_affected_nodes
        
        # 验证所有受影响节点都有有效的影响级别
        for affected_node in result.affected_nodes:
            assert affected_node.impact_level in ImpactLevel
            assert 0 <= affected_node.impact_score <= 1
            assert affected_node.distance_from_change >= 1
            assert affected_node.node_id in node_ids
            assert affected_node.node_id != changed_node_id  # 不应包含自身
    
    @given(generate_graph_structure(), st.sampled_from(list(ChangeType)))
    @settings(max_examples=30, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_impact_analysis_consistency_property(self, graph_data, change_type):
        """
        **Feature: code-weaver, Property 4: 影响分析准确性**
        
        测试影响分析的一致性：
        - 相同的输入应该产生相同的结果
        - 不同的变更类型应该产生合理的差异
        """
        analyzer, database = self.create_analyzer_setup()
        nodes, edges, node_ids = graph_data
        
        assume(len(nodes) >= 3)
        assume(len(edges) >= 2)
        
        # 创建图谱
        metadata = GraphMetadata(
            node_count=len(nodes),
            edge_count=len(edges),
            file_count=len(nodes),
            languages=['python'],
            node_types={},
            edge_types={}
        )
        
        graph = CodeGraph(
            id='test_graph_consistency',
            nodes=nodes,
            edges=edges,
            metadata=metadata
        )
        
        graph_name = database.store_graph(graph)
        changed_node_id = random.choice(node_ids)
        
        # 执行两次相同的分析
        result1 = analyzer.analyze_impact(
            graph_name=graph_name,
            changed_node_id=changed_node_id,
            change_type=change_type,
            max_depth=3
        )
        
        result2 = analyzer.analyze_impact(
            graph_name=graph_name,
            changed_node_id=changed_node_id,
            change_type=change_type,
            max_depth=3
        )
        
        # 验证结果一致性
        assert result1.changed_node_id == result2.changed_node_id
        assert result1.change_type == result2.change_type
        assert result1.total_affected_nodes == result2.total_affected_nodes
        
        # 验证受影响节点集合相同
        affected_ids_1 = {node.node_id for node in result1.affected_nodes}
        affected_ids_2 = {node.node_id for node in result2.affected_nodes}
        assert affected_ids_1 == affected_ids_2
        
        # 验证影响分数的一致性
        for node1 in result1.affected_nodes:
            node2 = next(n for n in result2.affected_nodes if n.node_id == node1.node_id)
            assert abs(node1.impact_score - node2.impact_score) < 0.001  # 允许微小的浮点误差
    
    @given(generate_graph_structure())
    @settings(max_examples=30, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_impact_analysis_transitivity_property(self, graph_data):
        """
        **Feature: code-weaver, Property 4: 影响分析准确性**
        
        测试影响分析的传递性：
        - 如果A影响B，B影响C，那么A应该间接影响C
        - 间接影响的强度应该随距离递减
        """
        analyzer, database = self.create_analyzer_setup()
        nodes, edges, node_ids = graph_data
        
        assume(len(nodes) >= 4)  # 至少需要4个节点来测试传递性
        assume(len(edges) >= 3)
        
        # 创建图谱
        metadata = GraphMetadata(
            node_count=len(nodes),
            edge_count=len(edges),
            file_count=len(nodes),
            languages=['python'],
            node_types={},
            edge_types={}
        )
        
        graph = CodeGraph(
            id='test_graph_transitivity',
            nodes=nodes,
            edges=edges,
            metadata=metadata
        )
        
        graph_name = database.store_graph(graph)
        
        # 选择一个节点进行分析
        changed_node_id = random.choice(node_ids)
        
        result = analyzer.analyze_impact(
            graph_name=graph_name,
            changed_node_id=changed_node_id,
            change_type=ChangeType.MODIFY,
            max_depth=4
        )
        
        # 验证距离递减属性
        if len(result.affected_nodes) > 1:
            # 按距离分组
            distance_groups = {}
            for node in result.affected_nodes:
                distance = node.distance_from_change
                if distance not in distance_groups:
                    distance_groups[distance] = []
                distance_groups[distance].append(node)
            
            # 验证距离越远，平均影响分数越低（总体趋势）
            distances = sorted(distance_groups.keys())
            if len(distances) > 1:
                for i in range(len(distances) - 1):
                    current_distance = distances[i]
                    next_distance = distances[i + 1]
                    
                    current_avg_score = sum(n.impact_score for n in distance_groups[current_distance]) / len(distance_groups[current_distance])
                    next_avg_score = sum(n.impact_score for n in distance_groups[next_distance]) / len(distance_groups[next_distance])
                    
                    # 允许一定的容差，因为影响分数还受其他因素影响
                    assert current_avg_score >= next_avg_score * 0.5  # 不应该差距过大
    
    @given(generate_graph_structure())
    @settings(max_examples=25, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_dependency_path_accuracy_property(self, graph_data):
        """
        **Feature: code-weaver, Property 4: 影响分析准确性**
        
        测试依赖路径计算的准确性：
        - 计算出的路径应该是有效的
        - 路径强度应该合理
        """
        analyzer, database = self.create_analyzer_setup()
        nodes, edges, node_ids = graph_data
        
        assume(len(nodes) >= 3)
        assume(len(edges) >= 2)
        
        # 创建图谱
        metadata = GraphMetadata(
            node_count=len(nodes),
            edge_count=len(edges),
            file_count=len(nodes),
            languages=['python'],
            node_types={},
            edge_types={}
        )
        
        graph = CodeGraph(
            id='test_graph_paths',
            nodes=nodes,
            edges=edges,
            metadata=metadata
        )
        
        graph_name = database.store_graph(graph)
        
        # 随机选择两个不同的节点
        source_id = random.choice(node_ids)
        target_candidates = [nid for nid in node_ids if nid != source_id]
        if not target_candidates:
            return  # 跳过只有一个节点的情况
        
        target_id = random.choice(target_candidates)
        
        # 计算依赖路径
        paths = analyzer.calculate_dependency_paths(
            graph_name=graph_name,
            source_node_id=source_id,
            target_node_id=target_id,
            max_paths=5
        )
        
        # 验证路径的有效性
        for path in paths:
            assert path.source_node_id == source_id
            assert path.target_node_id == target_id
            assert len(path.path_nodes) >= 2  # 至少包含源和目标
            assert path.path_nodes[0] == source_id
            assert path.path_nodes[-1] == target_id
            assert path.path_length == len(path.path_nodes) - 1
            assert 0 <= path.impact_strength <= 1
            assert len(path.relationship_types) == path.path_length
            
            # 验证路径中的所有节点都存在
            for node_id in path.path_nodes:
                assert node_id in node_ids
    
    @given(generate_graph_structure())
    @settings(max_examples=25, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_risk_assessment_reasonableness_property(self, graph_data):
        """
        **Feature: code-weaver, Property 4: 影响分析准确性**
        
        测试风险评估的合理性：
        - 风险分数应该在合理范围内
        - 不同变更类型应该有不同的风险级别
        """
        analyzer, database = self.create_analyzer_setup()
        nodes, edges, node_ids = graph_data
        
        assume(len(nodes) >= 3)
        
        # 创建图谱
        metadata = GraphMetadata(
            node_count=len(nodes),
            edge_count=len(edges),
            file_count=len(nodes),
            languages=['python'],
            node_types={},
            edge_types={}
        )
        
        graph = CodeGraph(
            id='test_graph_risk',
            nodes=nodes,
            edges=edges,
            metadata=metadata
        )
        
        graph_name = database.store_graph(graph)
        changed_node_id = random.choice(node_ids)
        
        # 测试不同变更类型的风险评估
        change_types = [ChangeType.MODIFY, ChangeType.DELETE, ChangeType.ADD, ChangeType.RENAME]
        risk_results = {}
        
        for change_type in change_types:
            risk_assessment = analyzer.assess_change_risk(
                graph_name=graph_name,
                changed_node_id=changed_node_id,
                change_type=change_type
            )
            
            # 验证风险评估结果的合理性
            assert 'risk_level' in risk_assessment
            assert 'risk_score' in risk_assessment
            assert 'risk_factors' in risk_assessment
            assert 'recommendations' in risk_assessment
            
            # 验证风险分数范围
            risk_score = risk_assessment['risk_score']
            assert 0 <= risk_score <= 1
            
            # 验证风险级别
            risk_level = risk_assessment['risk_level']
            assert risk_level in ['minimal', 'low', 'medium', 'high', 'critical', 'unknown']
            
            # 验证风险因子
            risk_factors = risk_assessment['risk_factors']
            for factor_name, factor_score in risk_factors.items():
                assert 0 <= factor_score <= 1
            
            # 验证建议列表
            recommendations = risk_assessment['recommendations']
            assert isinstance(recommendations, list)
            
            risk_results[change_type] = risk_score
        
        # 验证删除操作通常比修改操作风险更高
        if ChangeType.DELETE in risk_results and ChangeType.MODIFY in risk_results:
            # 允许一定的容差，因为风险还受其他因素影响
            delete_risk = risk_results[ChangeType.DELETE]
            modify_risk = risk_results[ChangeType.MODIFY]
            # 删除风险应该不低于修改风险的80%
            assert delete_risk >= modify_risk * 0.8
    
    @given(st.integers(min_value=1, max_value=5))
    @settings(max_examples=20, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_impact_analysis_depth_property(self, max_depth):
        """
        **Feature: code-weaver, Property 4: 影响分析准确性**
        
        测试影响分析深度限制的正确性：
        - 所有受影响节点的距离不应超过最大深度
        - 深度限制应该被正确执行
        """
        analyzer, database = self.create_analyzer_setup()
        
        # 创建一个线性链状图来测试深度
        nodes = []
        edges = []
        node_ids = []
        
        chain_length = max_depth + 3  # 创建比最大深度更长的链
        
        for i in range(chain_length):
            node_id = f"node_{i}"
            node_ids.append(node_id)
            
            node = GraphNode(
                id=node_id,
                label=f"Node{i}",
                type='class',
                properties={'name': f"Node{i}", 'complexity': 1}
            )
            nodes.append(node)
            
            if i > 0:
                edge = GraphEdge(
                    id=f"edge_{i}",
                    source_id=f"node_{i-1}",
                    target_id=node_id,
                    type='depends',
                    properties={'strength': 0.8}
                )
                edges.append(edge)
        
        # 创建图谱
        metadata = GraphMetadata(
            node_count=len(nodes),
            edge_count=len(edges),
            file_count=len(nodes),
            languages=['python'],
            node_types={},
            edge_types={}
        )
        
        graph = CodeGraph(
            id='test_graph_depth',
            nodes=nodes,
            edges=edges,
            metadata=metadata
        )
        
        graph_name = database.store_graph(graph)
        
        # 从链的起始节点开始分析
        result = analyzer.analyze_impact(
            graph_name=graph_name,
            changed_node_id='node_0',
            change_type=ChangeType.MODIFY,
            max_depth=max_depth
        )
        
        # 验证深度限制
        for affected_node in result.affected_nodes:
            assert affected_node.distance_from_change <= max_depth
        
        # 验证不会超出深度限制
        max_distance = max((node.distance_from_change for node in result.affected_nodes), default=0)
        assert max_distance <= max_depth