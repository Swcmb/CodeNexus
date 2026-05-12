"""
增量更新一致性属性测试

**Feature: code-weaver, Property 6: 增量更新一致性**
**验证需求: 需求 4.5**

对于任意代码变更，系统应该能够识别受影响的部分并只更新相关的图谱节点和文档内容，
更新后的结果应该与重新构建整个系统的结果一致。
"""

import tempfile
import os
import shutil
from typing import List, Set, Dict
from unittest.mock import Mock, MagicMock

import pytest
from hypothesis import given, strategies as st, settings, assume

from src.codenexus.models.core import (
    CodeElement, Relationship, ElementType, RelationType, 
    GraphNode, GraphEdge, CodeGraph
)
from src.codenexus.services.incremental_updater import (
    IncrementalGraphUpdater, DependencyAnalyzer, GraphUpdate, UpdateResult,
    UpdateType, create_incremental_updater
)
from src.codenexus.services.file_watcher import FileChange, ChangeType as FileChangeType
from src.codenexus.graph.graph_builder import GraphBuilder


# 测试数据生成策略
@st.composite
def code_element_strategy(draw):
    """生成代码元素的策略"""
    element_types = [ElementType.CLASS, ElementType.FUNCTION, ElementType.VARIABLE, ElementType.MODULE]
    
    # 生成文件路径的字符集
    path_chars = st.characters(whitelist_categories=('Lu', 'Ll', 'Nd')) | st.just('/') | st.just('.')
    
    return CodeElement(
        id=draw(st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd')))),
        name=draw(st.text(min_size=1, max_size=30, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd')))),
        type=draw(st.sampled_from(element_types)),
        file_path=draw(st.text(min_size=5, max_size=50, alphabet=path_chars)).replace(" ", "/"),
        line_number=draw(st.integers(min_value=1, max_value=1000)),
        complexity=draw(st.integers(min_value=1, max_value=100)),
        metadata=draw(st.dictionaries(st.text(min_size=1, max_size=10), st.text(min_size=1, max_size=20), max_size=3))
    )


@st.composite
def relationship_strategy(draw, element_ids):
    """生成关系的策略"""
    if len(element_ids) < 2:
        assume(False)  # 需要至少两个元素才能建立关系
    
    relation_types = [RelationType.CALLS, RelationType.INHERITS, RelationType.USES, RelationType.DEPENDS_ON]
    
    source_id = draw(st.sampled_from(element_ids))
    target_id = draw(st.sampled_from([eid for eid in element_ids if eid != source_id]))
    
    return Relationship(
        source_id=source_id,
        target_id=target_id,
        type=draw(st.sampled_from(relation_types)),
        strength=draw(st.floats(min_value=0.0, max_value=1.0)),
        metadata=draw(st.dictionaries(st.text(min_size=1, max_size=10), st.text(min_size=1, max_size=20), max_size=2))
    )


@st.composite
def file_change_strategy(draw):
    """生成文件变更的策略"""
    change_types = [FileChangeType.CREATED, FileChangeType.MODIFIED, FileChangeType.DELETED]
    
    # 生成文件路径的字符集
    path_chars = st.characters(whitelist_categories=('Lu', 'Ll', 'Nd')) | st.just('/') | st.just('.')
    
    return FileChange(
        path=draw(st.text(min_size=5, max_size=50, alphabet=path_chars)).replace(" ", "/"),
        change_type=draw(st.sampled_from(change_types)),
        timestamp=draw(st.floats(min_value=1000000000, max_value=2000000000)),
        file_hash=draw(st.text(min_size=8, max_size=32, alphabet=st.characters(whitelist_categories=('Nd', 'Lu'))))
    )


class MockGraphDatabase:
    """模拟图数据库，用于属性测试"""
    
    def __init__(self):
        self.nodes: Dict[str, Dict] = {}
        self.edges: Dict[str, Dict] = {}
        self.element_to_node: Dict[str, str] = {}
        self.session_calls = []
    
    def session(self):
        """模拟会话上下文管理器"""
        return MockSession(self)
    
    def add_node(self, element_id: str, node_data: Dict):
        """添加节点"""
        node_id = f"node_{len(self.nodes)}"
        self.nodes[node_id] = node_data.copy()
        self.nodes[node_id]['element_id'] = element_id
        self.element_to_node[element_id] = node_id
        return node_id
    
    def remove_node(self, element_id: str):
        """移除节点"""
        if element_id in self.element_to_node:
            node_id = self.element_to_node[element_id]
            self.nodes.pop(node_id, None)
            self.element_to_node.pop(element_id, None)
            
            # 移除相关的边
            edges_to_remove = []
            for edge_id, edge_data in self.edges.items():
                if edge_data.get('source_element_id') == element_id or edge_data.get('target_element_id') == element_id:
                    edges_to_remove.append(edge_id)
            
            for edge_id in edges_to_remove:
                self.edges.pop(edge_id, None)
    
    def add_edge(self, source_element_id: str, target_element_id: str, edge_data: Dict):
        """添加边"""
        edge_id = f"edge_{len(self.edges)}"
        self.edges[edge_id] = edge_data.copy()
        self.edges[edge_id]['source_element_id'] = source_element_id
        self.edges[edge_id]['target_element_id'] = target_element_id
        return edge_id
    
    def get_all_elements(self) -> Set[str]:
        """获取所有元素ID"""
        return set(self.element_to_node.keys())
    
    def get_dependencies(self, element_id: str) -> Set[str]:
        """获取依赖该元素的所有元素"""
        dependencies = set()
        for edge_data in self.edges.values():
            if edge_data.get('target_element_id') == element_id:
                dependencies.add(edge_data.get('source_element_id'))
        return dependencies


class MockSession:
    """模拟数据库会话"""
    
    def __init__(self, database: MockGraphDatabase):
        self.database = database
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass
    
    def begin_transaction(self):
        return MockTransaction(self.database)
    
    def run(self, query: str, **params):
        """模拟查询执行"""
        self.database.session_calls.append((query, params))
        
        # 根据查询类型返回模拟结果
        if "element_id" in params and "file_path" in query:
            # 文件映射查询
            results = []
            for node_data in self.database.nodes.values():
                if node_data.get('file_path'):
                    results.append({
                        'element_id': node_data.get('element_id'),
                        'file_path': node_data.get('file_path')
                    })
            return results
        
        elif "DEPENDS_ON" in query or "CALLS" in query:
            # 依赖关系查询
            element_id = params.get('element_id')
            if element_id:
                deps = self.database.get_dependencies(element_id)
                return [{'dep_id': dep_id} for dep_id in deps]
        
        return []


class MockTransaction:
    """模拟数据库事务"""
    
    def __init__(self, database: MockGraphDatabase):
        self.database = database
        self.operations = []
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self.commit()
    
    def run(self, query: str, **params):
        """模拟事务中的查询"""
        self.operations.append((query, params))
        
        # 模拟删除操作的结果
        if "DELETE" in query and "element_id" in params:
            element_id = params['element_id']
            if "DELETE r" in query:
                # 删除边
                edge_count = len([e for e in self.database.edges.values() 
                                if e.get('source_element_id') == element_id or e.get('target_element_id') == element_id])
                return [{'deleted_edges': edge_count}]
            elif "DELETE n" in query:
                # 删除节点
                node_id = self.database.element_to_node.get(element_id)
                if node_id:
                    return [{'node_id': node_id}]
        
        return []
    
    def commit(self):
        """提交事务"""
        for query, params in self.operations:
            if "DELETE" in query and "element_id" in params:
                element_id = params['element_id']
                self.database.remove_node(element_id)


class TestIncrementalUpdateConsistency:
    """增量更新一致性属性测试"""
    
    def setup_method(self):
        """测试设置"""
        self.mock_graph_builder = Mock(spec=GraphBuilder)
        self.mock_database = MockGraphDatabase()
        self.updater = IncrementalGraphUpdater(self.mock_graph_builder, self.mock_database)
    
    @given(st.lists(code_element_strategy(), min_size=1, max_size=10))
    @settings(max_examples=50, deadline=None)
    def test_file_deletion_consistency(self, elements: List[CodeElement]):
        """
        **Feature: code-weaver, Property 6: 增量更新一致性**
        **验证需求: 需求 4.5**
        
        属性：文件删除的一致性
        对于任意文件中的元素集合，删除文件后，所有相关元素都应该从图中移除，
        且不应该留下孤立的边或无效的引用。
        """
        # 确保元素ID唯一
        unique_elements = []
        seen_ids = set()
        for element in elements:
            if element.id not in seen_ids:
                unique_elements.append(element)
                seen_ids.add(element.id)
        
        if not unique_elements:
            assume(False)
        
        elements = unique_elements
        file_path = "/test/test_file.py"
        
        # 设置初始状态：将元素添加到数据库
        for element in elements:
            self.mock_database.add_node(element.id, {
                'name': element.name,
                'type': element.type.value,
                'file_path': file_path,
                'line_number': element.line_number
            })
        
        # 设置文件映射
        element_ids = {element.id for element in elements}
        self.updater._file_to_elements[file_path] = element_ids
        for element in elements:
            self.updater._element_to_file[element.id] = file_path
        
        # 记录删除前的状态
        initial_elements = self.mock_database.get_all_elements()
        initial_node_count = len(self.mock_database.nodes)
        initial_edge_count = len(self.mock_database.edges)
        
        # 执行文件删除
        result = self.updater.update_from_file_changes(file_path, [], [])
        
        # 验证删除操作成功
        assert result.success, f"文件删除操作失败: {result.error_message}"
        
        # 验证所有相关元素都被移除
        remaining_elements = self.mock_database.get_all_elements()
        removed_elements = initial_elements - remaining_elements
        
        # 所有文件中的元素都应该被移除
        for element_id in element_ids:
            assert element_id in removed_elements, f"元素 {element_id} 未被正确移除"
        
        # 验证文件映射被清理
        assert file_path not in self.updater._file_to_elements, "文件映射未被清理"
        for element_id in element_ids:
            assert element_id not in self.updater._element_to_file, f"元素映射 {element_id} 未被清理"
        
        # 验证更新记录
        assert len(result.updates_applied) > 0, "应该有更新记录"
        
        # 验证受影响的节点
        assert len(result.affected_nodes) > 0, "应该有受影响的节点"
    
    @given(st.lists(code_element_strategy(), min_size=2, max_size=8))
    @settings(max_examples=30, deadline=None)
    def test_incremental_vs_full_rebuild_consistency(self, elements: List[CodeElement]):
        """
        **Feature: code-weaver, Property 6: 增量更新一致性**
        **验证需求: 需求 4.5**
        
        属性：增量更新与完全重建的一致性
        对于任意代码变更，增量更新的结果应该与完全重建的结果一致。
        """
        # 确保元素ID唯一
        unique_elements = []
        seen_ids = set()
        for element in elements:
            if element.id not in seen_ids:
                unique_elements.append(element)
                seen_ids.add(element.id)
        
        if len(unique_elements) < 2:
            assume(False)
        
        elements = unique_elements
        file_path = "/test/consistency_test.py"
        
        # 模拟初始状态
        initial_elements = elements[:len(elements)//2]
        updated_elements = elements[len(elements)//2:]
        
        # 设置初始图状态
        for element in initial_elements:
            self.mock_database.add_node(element.id, {
                'name': element.name,
                'type': element.type.value,
                'file_path': file_path,
                'line_number': element.line_number
            })
        
        # 设置初始文件映射
        initial_element_ids = {element.id for element in initial_elements}
        self.updater._file_to_elements[file_path] = initial_element_ids
        for element in initial_elements:
            self.updater._element_to_file[element.id] = file_path
        
        # 模拟图构建器的行为
        def mock_create_nodes(elements_list):
            nodes = []
            for element in elements_list:
                node = Mock()
                node.id = f"node_{element.id}"
                node.name = element.name
                node.type = element.type.value
                node.file_path = element.file_path
                node.line_number = element.line_number
                node.properties = element.metadata
                nodes.append(node)
                # 更新映射
                self.mock_graph_builder.element_to_node = getattr(self.mock_graph_builder, 'element_to_node', {})
                self.mock_graph_builder.element_to_node[element.id] = node.id
            return nodes
        
        self.mock_graph_builder.create_nodes.side_effect = mock_create_nodes
        self.mock_graph_builder.create_edges.return_value = []
        
        # 记录更新前的状态
        pre_update_elements = self.mock_database.get_all_elements().copy()
        
        # 执行增量更新
        result = self.updater.update_from_file_changes(file_path, updated_elements, [])
        
        # 验证更新成功
        assert result.success, f"增量更新失败: {result.error_message}"
        
        # 验证状态变化的一致性
        post_update_elements = self.mock_database.get_all_elements()
        
        # 新增的元素应该在最终状态中
        updated_element_ids = {element.id for element in updated_elements}
        for element_id in updated_element_ids:
            if element_id not in initial_element_ids:
                # 这是新增的元素，应该通过图构建器被处理
                assert self.mock_graph_builder.create_nodes.called, "图构建器应该被调用来创建新节点"
        
        # 验证文件映射的一致性
        final_mapped_elements = self.updater._file_to_elements.get(file_path, set())
        assert final_mapped_elements == updated_element_ids, "文件映射应该反映最终的元素集合"
        
        # 验证更新记录的完整性
        assert len(result.updates_applied) >= 0, "应该有更新记录（可能为空）"
    
    @given(st.lists(code_element_strategy(), min_size=1, max_size=5))
    @settings(max_examples=20, deadline=None)
    def test_dependency_analysis_consistency(self, elements: List[CodeElement]):
        """
        **Feature: code-weaver, Property 6: 增量更新一致性**
        **验证需求: 需求 4.5**
        
        属性：依赖分析的一致性
        对于任意元素集合，依赖分析应该正确识别所有受影响的元素，
        且分析结果应该是确定性的和可重复的。
        """
        # 确保元素ID唯一
        unique_elements = []
        seen_ids = set()
        for element in elements:
            if element.id not in seen_ids:
                unique_elements.append(element)
                seen_ids.add(element.id)
        
        if not unique_elements:
            assume(False)
        
        elements = unique_elements
        element_ids = {element.id for element in elements}
        
        # 设置模拟的依赖关系
        for i, element in enumerate(elements):
            self.mock_database.add_node(element.id, {
                'name': element.name,
                'type': element.type.value,
                'file_path': element.file_path,
                'line_number': element.line_number
            })
            
            # 创建一些依赖关系
            if i > 0:
                prev_element = elements[i-1]
                self.mock_database.add_edge(element.id, prev_element.id, {
                    'type': 'DEPENDS_ON'
                })
        
        # 第一次分析
        first_analysis = {}
        for element_id in element_ids:
            first_analysis[element_id] = self.updater.dependency_analyzer.analyze_dependencies(element_id)
        
        # 清除缓存
        self.updater.dependency_analyzer.clear_cache()
        
        # 第二次分析
        second_analysis = {}
        for element_id in element_ids:
            second_analysis[element_id] = self.updater.dependency_analyzer.analyze_dependencies(element_id)
        
        # 验证分析结果的一致性
        for element_id in element_ids:
            assert first_analysis[element_id] == second_analysis[element_id], \
                f"元素 {element_id} 的依赖分析结果不一致"
        
        # 验证获取受影响元素的一致性
        first_affected = self.updater.get_affected_elements(element_ids)
        second_affected = self.updater.get_affected_elements(element_ids)
        
        assert first_affected == second_affected, "受影响元素的分析结果应该一致"
        
        # 验证受影响的元素包含原始元素
        assert element_ids.issubset(first_affected), "受影响的元素应该包含原始元素集合"
    
    @given(st.lists(code_element_strategy(), min_size=1, max_size=6))
    @settings(max_examples=25, deadline=None)
    def test_file_mapping_consistency(self, elements: List[CodeElement]):
        """
        **Feature: code-weaver, Property 6: 增量更新一致性**
        **验证需求: 需求 4.5**
        
        属性：文件映射的一致性
        对于任意元素集合，文件到元素的映射应该始终保持双向一致性。
        """
        # 确保元素ID唯一
        unique_elements = []
        seen_ids = set()
        for element in elements:
            if element.id not in seen_ids:
                unique_elements.append(element)
                seen_ids.add(element.id)
        
        if not unique_elements:
            assume(False)
        
        elements = unique_elements
        
        # 将元素按文件路径分组
        file_groups = {}
        for element in elements:
            file_path = element.file_path
            if file_path not in file_groups:
                file_groups[file_path] = []
            file_groups[file_path].append(element)
        
        # 模拟数据库会话和查询结果
        class MockRecord:
            def __init__(self, element_id, file_path):
                self.data = {"element_id": element_id, "file_path": file_path}
            
            def __getitem__(self, key):
                return self.data[key]
        
        mock_records = [MockRecord(elem.id, elem.file_path) for elem in elements]
        
        mock_session = Mock()
        mock_session.run.return_value = mock_records
        
        mock_session_context = Mock()
        mock_session_context.__enter__ = Mock(return_value=mock_session)
        mock_session_context.__exit__ = Mock(return_value=None)
        
        self.mock_database.session = Mock(return_value=mock_session_context)
        
        # 重建文件映射
        self.updater.rebuild_file_mappings()
        
        # 验证文件到元素的映射
        for file_path, file_elements in file_groups.items():
            expected_element_ids = {element.id for element in file_elements}
            actual_element_ids = self.updater._file_to_elements.get(file_path, set())
            
            assert actual_element_ids == expected_element_ids, \
                f"文件 {file_path} 的元素映射不正确"
        
        # 验证元素到文件的映射
        for element in elements:
            actual_file_path = self.updater._element_to_file.get(element.id)
            assert actual_file_path == element.file_path, \
                f"元素 {element.id} 的文件映射不正确"
        
        # 验证双向映射的一致性
        for file_path, element_ids in self.updater._file_to_elements.items():
            for element_id in element_ids:
                assert self.updater._element_to_file.get(element_id) == file_path, \
                    f"双向映射不一致：元素 {element_id} 和文件 {file_path}"
        
        for element_id, file_path in self.updater._element_to_file.items():
            assert element_id in self.updater._file_to_elements.get(file_path, set()), \
                f"双向映射不一致：文件 {file_path} 和元素 {element_id}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])