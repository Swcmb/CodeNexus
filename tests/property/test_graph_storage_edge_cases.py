"""
图数据库存储一致性的边界情况属性测试

测试各种边界情况和复杂场景下的存储一致性。
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from hypothesis.strategies import composite

from src.codenexus.models.core import (
    CodeElement, ElementType, Relationship, RelationType, ParseResult
)
from src.codenexus.graph.graph_builder import GraphBuilder
from tests.property.test_graph_storage_properties import MockGraphDatabase


@composite
def unicode_text_strategy(draw):
    """生成包含Unicode字符的文本策略"""
    return draw(st.text(
        min_size=1, 
        max_size=50,
        alphabet=st.characters(
            whitelist_categories=('Lu', 'Ll', 'Nd', 'Pc'),
            whitelist_characters='中文测试αβγδεζηθικλμνξοπρστυφχψω'
        )
    ))


@composite
def special_characters_element_strategy(draw):
    """生成包含特殊字符的CodeElement策略"""
    return CodeElement(
        name=draw(unicode_text_strategy()),
        type=draw(st.sampled_from(list(ElementType))),
        file_path=draw(st.text(min_size=1, max_size=100)),
        line_number=draw(st.integers(min_value=1, max_value=10000)),
        complexity=draw(st.integers(min_value=0, max_value=100)),
        docstring=draw(st.one_of(st.none(), unicode_text_strategy())),
        metadata={
            'special_chars': draw(st.text(alphabet='!@#$%^&*()[]{}|;:,.<>?')),
            'unicode_value': draw(unicode_text_strategy()),
            'nested_dict': {
                'key1': draw(st.text()),
                'key2': draw(st.integers()),
                'key3': draw(st.booleans())
            }
        }
    )


@composite
def complex_relationship_strategy(draw, element_ids):
    """生成复杂关系策略"""
    assume(len(element_ids) >= 2)
    
    source_id = draw(st.sampled_from(element_ids))
    target_id = draw(st.sampled_from([eid for eid in element_ids if eid != source_id]))
    
    return Relationship(
        source_id=source_id,
        target_id=target_id,
        type=draw(st.sampled_from(list(RelationType))),
        line_number=draw(st.integers(min_value=1, max_value=10000)),
        context=draw(unicode_text_strategy()),
        metadata={
            'call_count': draw(st.integers(min_value=0, max_value=1000)),
            'confidence': draw(st.floats(min_value=0.0, max_value=1.0)),
            'tags': draw(st.lists(st.text(max_size=20), max_size=5)),
            'unicode_context': draw(unicode_text_strategy()),
            'special_data': {
                'nested_list': draw(st.lists(st.integers(), max_size=10)),
                'boolean_flag': draw(st.booleans())
            }
        }
    )


class TestGraphStorageEdgeCases:
    """图数据库存储边界情况测试"""
    
    def setup_method(self):
        """测试前的设置"""
        self.builder = GraphBuilder()
        self.mock_db = MockGraphDatabase()
    
    @given(st.lists(special_characters_element_strategy(), min_size=1, max_size=5))
    @settings(max_examples=30, deadline=None)
    def test_unicode_and_special_characters_consistency(self, elements):
        """
        **Feature: code-weaver, Property 2: 图数据库存储一致性**
        
        测试包含Unicode字符和特殊字符的元素存储一致性
        """
        # 创建包含特殊字符的解析结果
        parse_result = ParseResult(
            file_path="unicode_test_文件.py",
            language="Python",
            elements=elements,
            relationships=[]
        )
        
        # 构建和存储图谱
        original_graph = self.builder.build_graph([parse_result])
        graph_id = self.mock_db.store_graph(original_graph)
        retrieved_graph = self.mock_db.retrieve_graph(graph_id)
        
        # 验证Unicode字符和特殊字符的一致性
        assert retrieved_graph is not None
        assert len(retrieved_graph.nodes) == len(original_graph.nodes)
        
        # 验证每个节点的Unicode内容
        original_nodes_by_id = {node.id: node for node in original_graph.nodes}
        retrieved_nodes_by_id = {node.id: node for node in retrieved_graph.nodes}
        
        for node_id in original_nodes_by_id:
            original_node = original_nodes_by_id[node_id]
            retrieved_node = retrieved_nodes_by_id[node_id]
            
            # 验证Unicode标签
            assert original_node.label == retrieved_node.label
            
            # 验证元数据中的特殊字符
            if 'special_chars' in original_node.properties:
                assert 'special_chars' in retrieved_node.properties
                assert original_node.properties['special_chars'] == retrieved_node.properties['special_chars']
            
            if 'unicode_value' in original_node.properties:
                assert 'unicode_value' in retrieved_node.properties
                assert original_node.properties['unicode_value'] == retrieved_node.properties['unicode_value']
    
    @given(st.lists(special_characters_element_strategy(), min_size=2, max_size=4))
    @settings(max_examples=20, deadline=None)
    def test_complex_metadata_consistency(self, elements):
        """
        测试复杂元数据结构的存储一致性
        """
        element_ids = [elem.id for elem in elements]
        
        # 生成复杂关系
        relationships = []
        if len(element_ids) >= 2:
            for i in range(min(3, len(element_ids) - 1)):
                rel = Relationship(
                    source_id=element_ids[i],
                    target_id=element_ids[i + 1],
                    type=RelationType.CALLS,
                    metadata={
                        'complex_data': {
                            'nested_dict': {
                                'level1': {
                                    'level2': {
                                        'value': f'deep_value_{i}',
                                        'number': i * 10,
                                        'list': [1, 2, 3, i]
                                    }
                                }
                            },
                            'unicode_list': [f'项目_{j}' for j in range(3)],
                            'mixed_types': [i, f'string_{i}', True, None]
                        }
                    }
                )
                relationships.append(rel)
        
        parse_result = ParseResult(
            file_path="complex_metadata_test.py",
            elements=elements,
            relationships=relationships
        )
        
        # 构建和存储图谱
        original_graph = self.builder.build_graph([parse_result])
        graph_id = self.mock_db.store_graph(original_graph)
        retrieved_graph = self.mock_db.retrieve_graph(graph_id)
        
        # 验证复杂元数据的一致性
        assert retrieved_graph is not None
        
        # 验证边的复杂元数据
        original_edges_by_id = {edge.id: edge for edge in original_graph.edges}
        retrieved_edges_by_id = {edge.id: edge for edge in retrieved_graph.edges}
        
        for edge_id in original_edges_by_id:
            original_edge = original_edges_by_id[edge_id]
            retrieved_edge = retrieved_edges_by_id[edge_id]
            
            if 'complex_data' in original_edge.properties:
                assert 'complex_data' in retrieved_edge.properties
                
                original_complex = original_edge.properties['complex_data']
                retrieved_complex = retrieved_edge.properties['complex_data']
                
                # 验证嵌套字典
                if 'nested_dict' in original_complex:
                    assert 'nested_dict' in retrieved_complex
                    assert original_complex['nested_dict'] == retrieved_complex['nested_dict']
                
                # 验证Unicode列表
                if 'unicode_list' in original_complex:
                    assert 'unicode_list' in retrieved_complex
                    assert original_complex['unicode_list'] == retrieved_complex['unicode_list']
                
                # 验证混合类型列表
                if 'mixed_types' in original_complex:
                    assert 'mixed_types' in retrieved_complex
                    assert original_complex['mixed_types'] == retrieved_complex['mixed_types']
    
    def test_circular_relationships_consistency(self):
        """
        测试循环关系的存储一致性
        """
        # 创建循环关系的元素
        elements = [
            CodeElement(name="ClassA", type=ElementType.CLASS, file_path="a.py"),
            CodeElement(name="ClassB", type=ElementType.CLASS, file_path="b.py"),
            CodeElement(name="ClassC", type=ElementType.CLASS, file_path="c.py")
        ]
        
        # 创建循环关系: A -> B -> C -> A
        relationships = [
            Relationship(
                source_id=elements[0].id,
                target_id=elements[1].id,
                type=RelationType.DEPENDS,
                context="A depends on B"
            ),
            Relationship(
                source_id=elements[1].id,
                target_id=elements[2].id,
                type=RelationType.DEPENDS,
                context="B depends on C"
            ),
            Relationship(
                source_id=elements[2].id,
                target_id=elements[0].id,
                type=RelationType.DEPENDS,
                context="C depends on A (circular)"
            )
        ]
        
        parse_result = ParseResult(
            file_path="circular_test.py",
            elements=elements,
            relationships=relationships
        )
        
        # 构建和存储图谱
        original_graph = self.builder.build_graph([parse_result])
        graph_id = self.mock_db.store_graph(original_graph)
        retrieved_graph = self.mock_db.retrieve_graph(graph_id)
        
        # 验证循环关系的一致性
        assert retrieved_graph is not None
        assert len(retrieved_graph.edges) == len(original_graph.edges)
        
        # 验证循环结构完整性
        retrieved_edges = retrieved_graph.edges
        
        # 检查是否保持了循环结构
        edge_pairs = [(edge.source_id, edge.target_id) for edge in retrieved_edges]
        
        # 验证每个节点都有入边和出边（除了可能的优化）
        node_ids = [node.id for node in retrieved_graph.nodes]
        
        for node_id in node_ids:
            # 检查是否有从该节点出发的边或到达该节点的边
            has_outgoing = any(source_id == node_id for source_id, _ in edge_pairs)
            has_incoming = any(target_id == node_id for _, target_id in edge_pairs)
            
            # 在循环结构中，每个节点应该至少有一个连接
            assert has_outgoing or has_incoming, f"节点 {node_id} 应该至少有一个连接"
    
    def test_self_referencing_relationships_consistency(self):
        """
        测试自引用关系的存储一致性
        """
        # 创建自引用的元素
        element = CodeElement(
            name="RecursiveClass",
            type=ElementType.CLASS,
            file_path="recursive.py",
            metadata={'description': '递归类'}
        )
        
        # 创建自引用关系
        self_relationship = Relationship(
            source_id=element.id,
            target_id=element.id,
            type=RelationType.CALLS,
            context="Recursive method call",
            metadata={'recursion_depth': 5}
        )
        
        parse_result = ParseResult(
            file_path="self_reference_test.py",
            elements=[element],
            relationships=[self_relationship]
        )
        
        # 构建和存储图谱
        original_graph = self.builder.build_graph([parse_result])
        graph_id = self.mock_db.store_graph(original_graph)
        retrieved_graph = self.mock_db.retrieve_graph(graph_id)
        
        # 验证自引用关系的一致性
        assert retrieved_graph is not None
        assert len(retrieved_graph.nodes) == len(original_graph.nodes)
        assert len(retrieved_graph.edges) == len(original_graph.edges)
        
        # 验证自引用边
        if len(retrieved_graph.edges) > 0:
            self_edge = retrieved_graph.edges[0]
            assert self_edge.source_id == self_edge.target_id
            assert 'recursion_depth' in self_edge.properties
            assert self_edge.properties['recursion_depth'] == 5
    
    def test_extreme_values_consistency(self):
        """
        测试极值情况的存储一致性
        """
        # 创建包含极值的元素
        extreme_element = CodeElement(
            name="ExtremeElement",
            type=ElementType.CLASS,
            file_path="extreme.py",
            line_number=999999,  # 极大行号
            complexity=0,  # 极小复杂度
            metadata={
                'max_int': 2**31 - 1,
                'min_int': -(2**31),
                'max_float': 1.7976931348623157e+308,
                'min_float': 2.2250738585072014e-308,
                'empty_string': '',
                'very_long_string': 'x' * 10000,
                'empty_list': [],
                'empty_dict': {}
            }
        )
        
        parse_result = ParseResult(
            file_path="extreme_values_test.py",
            elements=[extreme_element],
            relationships=[]
        )
        
        # 构建和存储图谱
        original_graph = self.builder.build_graph([parse_result])
        graph_id = self.mock_db.store_graph(original_graph)
        retrieved_graph = self.mock_db.retrieve_graph(graph_id)
        
        # 验证极值的一致性
        assert retrieved_graph is not None
        assert len(retrieved_graph.nodes) == 1
        
        original_node = original_graph.nodes[0]
        retrieved_node = retrieved_graph.nodes[0]
        
        # 验证极值属性
        extreme_keys = ['max_int', 'min_int', 'max_float', 'min_float', 
                       'empty_string', 'very_long_string', 'empty_list', 'empty_dict']
        
        for key in extreme_keys:
            if key in original_node.properties:
                assert key in retrieved_node.properties
                assert original_node.properties[key] == retrieved_node.properties[key]
    
    def test_null_and_none_values_consistency(self):
        """
        测试空值和None值的存储一致性
        """
        # 创建包含None值的元素
        element_with_nones = CodeElement(
            name="ElementWithNones",
            type=ElementType.CLASS,
            file_path="none_test.py",
            docstring=None,  # None值
            return_type=None,  # None值
            metadata={
                'nullable_field': None,
                'optional_data': None,
                'mixed_list': [1, None, 'text', None],
                'dict_with_nones': {
                    'key1': 'value1',
                    'key2': None,
                    'key3': 'value3'
                }
            }
        )
        
        parse_result = ParseResult(
            file_path="none_values_test.py",
            elements=[element_with_nones],
            relationships=[]
        )
        
        # 构建和存储图谱
        original_graph = self.builder.build_graph([parse_result])
        graph_id = self.mock_db.store_graph(original_graph)
        retrieved_graph = self.mock_db.retrieve_graph(graph_id)
        
        # 验证None值的一致性
        assert retrieved_graph is not None
        assert len(retrieved_graph.nodes) == 1
        
        original_node = original_graph.nodes[0]
        retrieved_node = retrieved_graph.nodes[0]
        
        # 验证None值属性
        none_keys = ['nullable_field', 'optional_data', 'mixed_list', 'dict_with_nones']
        
        for key in none_keys:
            if key in original_node.properties:
                assert key in retrieved_node.properties
                assert original_node.properties[key] == retrieved_node.properties[key]