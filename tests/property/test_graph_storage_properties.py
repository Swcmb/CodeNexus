"""
图数据库存储一致性的属性测试

**Feature: code-weaver, Property 2: 图数据库存储一致性**
*对于任意* 解析结果，转换为图结构并存储到数据库后，查询得到的数据应该与原始解析结果保持一致，不丢失任何元素或关系信息
**验证需求: 需求 1.2, 1.3**
"""

from typing import Dict, List, Optional, Set
import pytest
from hypothesis import given, strategies as st, settings, assume
from hypothesis.strategies import composite

from src.codenexus.models.core import (
    CodeElement, ElementType, Relationship, RelationType, ParseResult, CodeGraph
)
from src.codenexus.graph.graph_builder import GraphBuilder


# 模拟图数据库接口
class MockGraphDatabase:
    """模拟图数据库，用于测试存储一致性"""
    
    def __init__(self):
        self.stored_graphs: Dict[str, CodeGraph] = {}
        self.node_storage: Dict[str, Dict] = {}
        self.edge_storage: Dict[str, Dict] = {}
    
    def store_graph(self, graph: CodeGraph) -> str:
        """存储图到数据库"""
        graph_id = graph.id
        
        # 模拟存储过程中的序列化/反序列化
        serialized_graph = self._serialize_graph(graph)
        deserialized_graph = self._deserialize_graph(serialized_graph)
        
        self.stored_graphs[graph_id] = deserialized_graph
        
        # 分别存储节点和边
        for node in deserialized_graph.nodes:
            self.node_storage[node.id] = self._serialize_node(node)
        
        for edge in deserialized_graph.edges:
            self.edge_storage[edge.id] = self._serialize_edge(edge)
        
        return graph_id
    
    def retrieve_graph(self, graph_id: str) -> Optional[CodeGraph]:
        """从数据库检索图"""
        return self.stored_graphs.get(graph_id)
    
    def query_nodes(self, graph_id: str, node_type: Optional[str] = None) -> List[Dict]:
        """查询节点"""
        if graph_id not in self.stored_graphs:
            return []
        
        graph = self.stored_graphs[graph_id]
        nodes = []
        
        for node in graph.nodes:
            if node_type is None or node.type == node_type:
                nodes.append(self._serialize_node(node))
        
        return nodes
    
    def query_edges(self, graph_id: str, edge_type: Optional[str] = None) -> List[Dict]:
        """查询边"""
        if graph_id not in self.stored_graphs:
            return []
        
        graph = self.stored_graphs[graph_id]
        edges = []
        
        for edge in graph.edges:
            if edge_type is None or edge.type == edge_type:
                edges.append(self._serialize_edge(edge))
        
        return edges
    
    def _serialize_graph(self, graph: CodeGraph) -> Dict:
        """序列化图"""
        return {
            'id': graph.id,
            'nodes': [self._serialize_node(node) for node in graph.nodes],
            'edges': [self._serialize_edge(edge) for edge in graph.edges],
            'metadata': {
                'node_count': graph.metadata.node_count,
                'edge_count': graph.metadata.edge_count,
                'file_count': graph.metadata.file_count,
                'languages': graph.metadata.languages,
                'node_types': graph.metadata.node_types,
                'edge_types': graph.metadata.edge_types,
                'creation_time': graph.metadata.creation_time,
                'version': graph.metadata.version
            }
        }
    
    def _deserialize_graph(self, data: Dict) -> CodeGraph:
        """反序列化图"""
        from src.codenexus.models.core import GraphNode, GraphEdge, GraphMetadata
        
        nodes = [self._deserialize_node(node_data) for node_data in data['nodes']]
        edges = [self._deserialize_edge(edge_data) for edge_data in data['edges']]
        
        metadata = GraphMetadata(
            node_count=data['metadata']['node_count'],
            edge_count=data['metadata']['edge_count'],
            file_count=data['metadata']['file_count'],
            languages=data['metadata']['languages'],
            node_types=data['metadata']['node_types'],
            edge_types=data['metadata']['edge_types'],
            creation_time=data['metadata']['creation_time'],
            version=data['metadata']['version']
        )
        
        return CodeGraph(
            id=data['id'],
            nodes=nodes,
            edges=edges,
            metadata=metadata
        )
    
    def _serialize_node(self, node) -> Dict:
        """序列化节点"""
        return {
            'id': node.id,
            'label': node.label,
            'type': node.type,
            'properties': node.properties.copy()
        }
    
    def _deserialize_node(self, data: Dict):
        """反序列化节点"""
        from src.codenexus.models.core import GraphNode
        return GraphNode(
            id=data['id'],
            label=data['label'],
            type=data['type'],
            properties=data['properties']
        )
    
    def _serialize_edge(self, edge) -> Dict:
        """序列化边"""
        return {
            'id': edge.id,
            'source_id': edge.source_id,
            'target_id': edge.target_id,
            'type': edge.type,
            'properties': edge.properties.copy()
        }
    
    def _deserialize_edge(self, data: Dict):
        """反序列化边"""
        from src.codenexus.models.core import GraphEdge
        return GraphEdge(
            id=data['id'],
            source_id=data['source_id'],
            target_id=data['target_id'],
            type=data['type'],
            properties=data['properties']
        )


# Hypothesis策略定义
@composite
def element_type_strategy(draw):
    """生成ElementType策略"""
    return draw(st.sampled_from(list(ElementType)))


@composite
def relation_type_strategy(draw):
    """生成RelationType策略"""
    return draw(st.sampled_from(list(RelationType)))


@composite
def code_element_strategy(draw):
    """生成CodeElement策略"""
    return CodeElement(
        name=draw(st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd')))),
        type=draw(element_type_strategy()),
        file_path=draw(st.text(min_size=1, max_size=100, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Pc')))),
        line_number=draw(st.integers(min_value=1, max_value=10000)),
        complexity=draw(st.integers(min_value=0, max_value=100)),
        visibility=draw(st.sampled_from(['public', 'private', 'protected', 'internal'])),
        is_abstract=draw(st.booleans()),
        is_static=draw(st.booleans())
    )


@composite
def relationship_strategy(draw, element_ids):
    """生成Relationship策略"""
    assume(len(element_ids) >= 2)
    
    source_id = draw(st.sampled_from(element_ids))
    target_id = draw(st.sampled_from([eid for eid in element_ids if eid != source_id]))
    
    return Relationship(
        source_id=source_id,
        target_id=target_id,
        type=draw(relation_type_strategy()),
        line_number=draw(st.integers(min_value=1, max_value=10000)),
        context=draw(st.text(max_size=200))
    )


@composite
def parse_result_strategy(draw):
    """生成ParseResult策略"""
    # 生成1-10个元素
    num_elements = draw(st.integers(min_value=1, max_value=10))
    elements = [draw(code_element_strategy()) for _ in range(num_elements)]
    element_ids = [elem.id for elem in elements]
    
    # 生成0-5个关系
    num_relationships = draw(st.integers(min_value=0, max_value=min(5, len(element_ids))))
    relationships = []
    
    if num_relationships > 0 and len(element_ids) >= 2:
        relationships = [draw(relationship_strategy(element_ids)) for _ in range(num_relationships)]
    
    return ParseResult(
        file_path=draw(st.text(min_size=1, max_size=100)),
        language=draw(st.sampled_from(['Python', 'Java', 'JavaScript', 'C#'])),
        elements=elements,
        relationships=relationships,
        parse_time=draw(st.floats(min_value=0.001, max_value=10.0))
    )


class TestGraphStorageProperties:
    """图数据库存储一致性属性测试"""
    
    def setup_method(self):
        """测试前的设置"""
        self.builder = GraphBuilder()
        self.mock_db = MockGraphDatabase()
    
    @given(st.lists(parse_result_strategy(), min_size=1, max_size=3))
    @settings(max_examples=100, deadline=None)
    def test_graph_storage_consistency_property(self, parse_results):
        """
        **Feature: code-weaver, Property 2: 图数据库存储一致性**
        
        属性：对于任意解析结果，转换为图结构并存储到数据库后，
        查询得到的数据应该与原始解析结果保持一致，不丢失任何元素或关系信息
        """
        # 构建原始图谱
        original_graph = self.builder.build_graph(parse_results)
        
        # 存储到模拟数据库
        graph_id = self.mock_db.store_graph(original_graph)
        
        # 从数据库检索图谱
        retrieved_graph = self.mock_db.retrieve_graph(graph_id)
        
        # 验证图谱一致性
        assert retrieved_graph is not None, "检索的图谱不应为空"
        
        # 验证基本属性
        assert retrieved_graph.id == original_graph.id, "图谱ID应该保持一致"
        assert len(retrieved_graph.nodes) == len(original_graph.nodes), "节点数量应该保持一致"
        assert len(retrieved_graph.edges) == len(original_graph.edges), "边数量应该保持一致"
        
        # 验证元数据一致性
        assert retrieved_graph.metadata.node_count == original_graph.metadata.node_count
        assert retrieved_graph.metadata.edge_count == original_graph.metadata.edge_count
        assert retrieved_graph.metadata.file_count == original_graph.metadata.file_count
        assert retrieved_graph.metadata.languages == original_graph.metadata.languages
        assert retrieved_graph.metadata.version == original_graph.metadata.version
        
        # 验证节点一致性
        original_nodes_by_id = {node.id: node for node in original_graph.nodes}
        retrieved_nodes_by_id = {node.id: node for node in retrieved_graph.nodes}
        
        assert set(original_nodes_by_id.keys()) == set(retrieved_nodes_by_id.keys()), "节点ID集合应该相同"
        
        for node_id in original_nodes_by_id:
            original_node = original_nodes_by_id[node_id]
            retrieved_node = retrieved_nodes_by_id[node_id]
            
            assert original_node.label == retrieved_node.label, f"节点{node_id}的标签应该一致"
            assert original_node.type == retrieved_node.type, f"节点{node_id}的类型应该一致"
            
            # 验证关键属性
            key_properties = ['name', 'file_path', 'line_number', 'complexity']
            for prop in key_properties:
                if prop in original_node.properties:
                    assert prop in retrieved_node.properties, f"节点{node_id}应该包含属性{prop}"
                    assert original_node.properties[prop] == retrieved_node.properties[prop], \
                        f"节点{node_id}的属性{prop}应该一致"
        
        # 验证边一致性
        original_edges_by_id = {edge.id: edge for edge in original_graph.edges}
        retrieved_edges_by_id = {edge.id: edge for edge in retrieved_graph.edges}
        
        assert set(original_edges_by_id.keys()) == set(retrieved_edges_by_id.keys()), "边ID集合应该相同"
        
        for edge_id in original_edges_by_id:
            original_edge = original_edges_by_id[edge_id]
            retrieved_edge = retrieved_edges_by_id[edge_id]
            
            assert original_edge.source_id == retrieved_edge.source_id, f"边{edge_id}的源节点应该一致"
            assert original_edge.target_id == retrieved_edge.target_id, f"边{edge_id}的目标节点应该一致"
            assert original_edge.type == retrieved_edge.type, f"边{edge_id}的类型应该一致"
            
            # 验证关键属性
            key_properties = ['relationship_id', 'line_number', 'context', 'strength']
            for prop in key_properties:
                if prop in original_edge.properties:
                    assert prop in retrieved_edge.properties, f"边{edge_id}应该包含属性{prop}"
                    assert original_edge.properties[prop] == retrieved_edge.properties[prop], \
                        f"边{edge_id}的属性{prop}应该一致"
    
    @given(st.lists(parse_result_strategy(), min_size=1, max_size=2))
    @settings(max_examples=50, deadline=None)
    def test_node_query_consistency_property(self, parse_results):
        """
        属性：查询特定类型的节点应该返回所有该类型的节点，且信息完整
        """
        # 构建和存储图谱
        original_graph = self.builder.build_graph(parse_results)
        graph_id = self.mock_db.store_graph(original_graph)
        
        # 统计原始图谱中各类型节点的数量
        original_node_types = {}
        for node in original_graph.nodes:
            node_type = node.type
            if node_type not in original_node_types:
                original_node_types[node_type] = []
            original_node_types[node_type].append(node)
        
        # 查询每种类型的节点
        for node_type, expected_nodes in original_node_types.items():
            queried_nodes = self.mock_db.query_nodes(graph_id, node_type)
            
            # 验证查询结果数量
            assert len(queried_nodes) == len(expected_nodes), \
                f"查询{node_type}类型节点的数量应该与原始数量一致"
            
            # 验证查询结果内容
            queried_node_ids = {node['id'] for node in queried_nodes}
            expected_node_ids = {node.id for node in expected_nodes}
            
            assert queried_node_ids == expected_node_ids, \
                f"查询{node_type}类型节点的ID集合应该与原始ID集合一致"
            
            # 验证节点信息完整性
            for queried_node in queried_nodes:
                original_node = next(n for n in expected_nodes if n.id == queried_node['id'])
                
                assert queried_node['label'] == original_node.label
                assert queried_node['type'] == original_node.type
                
                # 验证关键属性存在
                key_properties = ['name', 'file_path', 'line_number']
                for prop in key_properties:
                    if prop in original_node.properties:
                        assert prop in queried_node['properties'], \
                            f"查询结果应该包含属性{prop}"
    
    @given(st.lists(parse_result_strategy(), min_size=1, max_size=2))
    @settings(max_examples=50, deadline=None)
    def test_edge_query_consistency_property(self, parse_results):
        """
        属性：查询特定类型的边应该返回所有该类型的边，且关系信息完整
        """
        # 构建和存储图谱
        original_graph = self.builder.build_graph(parse_results)
        
        # 如果没有边，跳过测试
        if len(original_graph.edges) == 0:
            return
        
        graph_id = self.mock_db.store_graph(original_graph)
        
        # 统计原始图谱中各类型边的数量
        original_edge_types = {}
        for edge in original_graph.edges:
            edge_type = edge.type
            if edge_type not in original_edge_types:
                original_edge_types[edge_type] = []
            original_edge_types[edge_type].append(edge)
        
        # 查询每种类型的边
        for edge_type, expected_edges in original_edge_types.items():
            queried_edges = self.mock_db.query_edges(graph_id, edge_type)
            
            # 验证查询结果数量
            assert len(queried_edges) == len(expected_edges), \
                f"查询{edge_type}类型边的数量应该与原始数量一致"
            
            # 验证查询结果内容
            queried_edge_ids = {edge['id'] for edge in queried_edges}
            expected_edge_ids = {edge.id for edge in expected_edges}
            
            assert queried_edge_ids == expected_edge_ids, \
                f"查询{edge_type}类型边的ID集合应该与原始ID集合一致"
            
            # 验证边信息完整性
            for queried_edge in queried_edges:
                original_edge = next(e for e in expected_edges if e.id == queried_edge['id'])
                
                assert queried_edge['source_id'] == original_edge.source_id
                assert queried_edge['target_id'] == original_edge.target_id
                assert queried_edge['type'] == original_edge.type
    
    @given(parse_result_strategy())
    @settings(max_examples=50, deadline=None)
    def test_round_trip_consistency_property(self, parse_result):
        """
        属性：单个解析结果的往返一致性 - 构建图谱、存储、检索后应该保持完全一致
        """
        # 构建原始图谱
        original_graph = self.builder.build_graph([parse_result])
        
        # 存储并检索
        graph_id = self.mock_db.store_graph(original_graph)
        retrieved_graph = self.mock_db.retrieve_graph(graph_id)
        
        # 验证完全一致性
        assert retrieved_graph is not None
        
        # 验证图谱结构完全相同
        self._assert_graphs_equal(original_graph, retrieved_graph)
    
    def _assert_graphs_equal(self, graph1: CodeGraph, graph2: CodeGraph):
        """断言两个图谱完全相等"""
        assert graph1.id == graph2.id
        assert len(graph1.nodes) == len(graph2.nodes)
        assert len(graph1.edges) == len(graph2.edges)
        
        # 按ID排序后比较
        nodes1_sorted = sorted(graph1.nodes, key=lambda n: n.id)
        nodes2_sorted = sorted(graph2.nodes, key=lambda n: n.id)
        
        for n1, n2 in zip(nodes1_sorted, nodes2_sorted):
            assert n1.id == n2.id
            assert n1.label == n2.label
            assert n1.type == n2.type
            # 比较关键属性
            for key in ['name', 'file_path', 'line_number', 'complexity']:
                if key in n1.properties:
                    assert key in n2.properties
                    assert n1.properties[key] == n2.properties[key]
        
        edges1_sorted = sorted(graph1.edges, key=lambda e: e.id)
        edges2_sorted = sorted(graph2.edges, key=lambda e: e.id)
        
        for e1, e2 in zip(edges1_sorted, edges2_sorted):
            assert e1.id == e2.id
            assert e1.source_id == e2.source_id
            assert e1.target_id == e2.target_id
            assert e1.type == e2.type
    
    def test_empty_graph_storage_consistency(self):
        """测试空图谱的存储一致性"""
        from src.codenexus.models.core import CodeGraph, GraphMetadata
        
        # 创建空图谱
        empty_graph = CodeGraph(
            nodes=[],
            edges=[],
            metadata=GraphMetadata()
        )
        
        # 存储并检索
        graph_id = self.mock_db.store_graph(empty_graph)
        retrieved_graph = self.mock_db.retrieve_graph(graph_id)
        
        # 验证空图谱一致性
        assert retrieved_graph is not None
        assert len(retrieved_graph.nodes) == 0
        assert len(retrieved_graph.edges) == 0
        assert retrieved_graph.metadata.node_count == 0
        assert retrieved_graph.metadata.edge_count == 0
    
    def test_large_graph_storage_consistency(self):
        """测试大型图谱的存储一致性"""
        # 创建大型解析结果
        elements = []
        relationships = []
        
        # 创建100个元素
        for i in range(100):
            elements.append(CodeElement(
                name=f"Element{i}",
                type=ElementType.CLASS if i % 2 == 0 else ElementType.METHOD,
                file_path=f"file{i // 10}.py",
                line_number=i + 1,
                complexity=i % 10
            ))
        
        # 创建一些关系
        for i in range(0, 98, 2):
            relationships.append(Relationship(
                source_id=elements[i].id,
                target_id=elements[i + 1].id,
                type=RelationType.CALLS,
                line_number=i + 1,
                context=f"Call from Element{i} to Element{i+1}"
            ))
        
        large_parse_result = ParseResult(
            file_path="large_project",
            language="Python",
            elements=elements,
            relationships=relationships
        )
        
        # 构建和存储大型图谱
        large_graph = self.builder.build_graph([large_parse_result])
        graph_id = self.mock_db.store_graph(large_graph)
        retrieved_graph = self.mock_db.retrieve_graph(graph_id)
        
        # 验证大型图谱一致性
        assert retrieved_graph is not None
        assert len(retrieved_graph.nodes) == len(large_graph.nodes)
        assert len(retrieved_graph.edges) == len(large_graph.edges)
        
        # 验证节点和边的数量统计
        assert retrieved_graph.metadata.node_count == large_graph.metadata.node_count
        assert retrieved_graph.metadata.edge_count == large_graph.metadata.edge_count