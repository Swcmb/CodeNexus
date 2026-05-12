"""
增量图更新服务单元测试
"""

import time
from unittest.mock import Mock, MagicMock, patch
import pytest

from src.codenexus.services.incremental_updater import (
    IncrementalGraphUpdater, DependencyAnalyzer, GraphUpdate, UpdateResult,
    UpdateType, create_incremental_updater
)
from src.codenexus.models.core import (
    CodeElement, Relationship, GraphNode, GraphEdge, 
    ElementType, RelationType
)


class TestUpdateType:
    """测试更新类型枚举"""
    
    def test_update_types(self):
        """测试更新类型值"""
        assert UpdateType.ADD_NODE.value == "add_node"
        assert UpdateType.UPDATE_NODE.value == "update_node"
        assert UpdateType.REMOVE_NODE.value == "remove_node"
        assert UpdateType.ADD_EDGE.value == "add_edge"
        assert UpdateType.UPDATE_EDGE.value == "update_edge"
        assert UpdateType.REMOVE_EDGE.value == "remove_edge"


class TestGraphUpdate:
    """测试图更新操作"""
    
    def test_graph_update_creation(self):
        """测试图更新操作创建"""
        update = GraphUpdate(
            update_type=UpdateType.ADD_NODE,
            node_id="node_123",
            data={"element_id": "elem_456"}
        )
        
        assert update.update_type == UpdateType.ADD_NODE
        assert update.node_id == "node_123"
        assert update.edge_id is None
        assert update.data["element_id"] == "elem_456"
        assert update.timestamp is not None
    
    def test_graph_update_with_timestamp(self):
        """测试带时间戳的图更新操作"""
        timestamp = time.time()
        update = GraphUpdate(
            update_type=UpdateType.REMOVE_EDGE,
            edge_id="edge_789",
            timestamp=timestamp
        )
        
        assert update.update_type == UpdateType.REMOVE_EDGE
        assert update.edge_id == "edge_789"
        assert update.timestamp == timestamp


class TestUpdateResult:
    """测试更新结果"""
    
    def test_successful_update_result(self):
        """测试成功的更新结果"""
        updates = [
            GraphUpdate(UpdateType.ADD_NODE, node_id="node_1"),
            GraphUpdate(UpdateType.ADD_EDGE, edge_id="edge_1")
        ]
        
        result = UpdateResult(
            success=True,
            updates_applied=updates,
            affected_nodes={"node_1", "node_2"},
            affected_edges={"edge_1"}
        )
        
        assert result.success is True
        assert len(result.updates_applied) == 2
        assert len(result.affected_nodes) == 2
        assert len(result.affected_edges) == 1
        assert result.error_message is None
    
    def test_failed_update_result(self):
        """测试失败的更新结果"""
        result = UpdateResult(
            success=False,
            updates_applied=[],
            affected_nodes=set(),
            affected_edges=set(),
            error_message="Database connection failed"
        )
        
        assert result.success is False
        assert len(result.updates_applied) == 0
        assert len(result.affected_nodes) == 0
        assert len(result.affected_edges) == 0
        assert result.error_message == "Database connection failed"


class TestDependencyAnalyzer:
    """测试依赖分析器"""
    
    def setup_method(self):
        """测试设置"""
        self.mock_database = Mock()
        self.analyzer = DependencyAnalyzer(self.mock_database)
    
    def test_analyze_dependencies_with_cache(self):
        """测试带缓存的依赖分析"""
        # 设置缓存
        element_id = "test_element"
        cached_deps = {"dep1", "dep2"}
        self.analyzer._dependency_cache[element_id] = cached_deps
        
        # 调用分析
        result = self.analyzer.analyze_dependencies(element_id)
        
        # 验证返回缓存结果
        assert result == cached_deps
        # 验证没有调用数据库
        self.mock_database.session.assert_not_called()
    
    def test_analyze_dependencies_without_cache(self):
        """测试无缓存的依赖分析"""
        element_id = "test_element"
        
        # 模拟数据库会话
        mock_session = Mock()
        mock_context_manager = Mock()
        mock_context_manager.__enter__ = Mock(return_value=mock_session)
        mock_context_manager.__exit__ = Mock(return_value=None)
        self.mock_database.session.return_value = mock_context_manager
        
        # 模拟查询结果
        mock_session.run.side_effect = [
            [{"dep_id": "direct_dep1"}, {"dep_id": "direct_dep2"}],  # 直接依赖
            [{"dep_id": "indirect_dep1"}, {"dep_id": "direct_dep1"}]  # 间接依赖
        ]
        
        # 调用分析
        result = self.analyzer.analyze_dependencies(element_id)
        
        # 验证结果（去重后）
        expected = {"direct_dep1", "direct_dep2", "indirect_dep1"}
        assert result == expected
        
        # 验证缓存被更新
        assert self.analyzer._dependency_cache[element_id] == expected
        
        # 验证数据库被调用
        assert mock_session.run.call_count == 2
    
    def test_analyze_dependencies_database_error(self):
        """测试数据库错误时的依赖分析"""
        element_id = "test_element"
        
        # 模拟数据库错误
        self.mock_database.session.side_effect = Exception("Database error")
        
        # 调用分析
        result = self.analyzer.analyze_dependencies(element_id)
        
        # 验证返回空集合
        assert result == set()
        
        # 验证缓存被设置为空集合
        assert self.analyzer._dependency_cache[element_id] == set()
    
    def test_clear_cache_all(self):
        """测试清除所有缓存"""
        # 设置缓存
        self.analyzer._dependency_cache = {
            "elem1": {"dep1"},
            "elem2": {"dep2"}
        }
        
        # 清除所有缓存
        self.analyzer.clear_cache()
        
        # 验证缓存被清空
        assert len(self.analyzer._dependency_cache) == 0
    
    def test_clear_cache_specific(self):
        """测试清除特定缓存"""
        # 设置缓存
        self.analyzer._dependency_cache = {
            "elem1": {"dep1"},
            "elem2": {"dep2"},
            "elem3": {"dep3"}
        }
        
        # 清除特定缓存
        self.analyzer.clear_cache({"elem1", "elem3"})
        
        # 验证特定缓存被清除
        assert "elem1" not in self.analyzer._dependency_cache
        assert "elem3" not in self.analyzer._dependency_cache
        assert "elem2" in self.analyzer._dependency_cache


class TestIncrementalGraphUpdater:
    """测试增量图更新器"""
    
    def setup_method(self):
        """测试设置"""
        self.mock_graph_builder = Mock()
        self.mock_database = Mock()
        self.updater = IncrementalGraphUpdater(self.mock_graph_builder, self.mock_database)
    
    def test_initialization(self):
        """测试初始化"""
        assert self.updater.graph_builder == self.mock_graph_builder
        assert self.updater.graph_database == self.mock_database
        assert isinstance(self.updater.dependency_analyzer, DependencyAnalyzer)
        assert len(self.updater._file_to_elements) == 0
        assert len(self.updater._element_to_file) == 0
    
    def test_update_from_file_changes_empty_elements(self):
        """测试处理文件删除（空元素列表）"""
        file_path = "/test/deleted_file.py"
        
        # 模拟文件删除处理
        with patch.object(self.updater, '_handle_file_deletion') as mock_handle:
            mock_result = UpdateResult(
                success=True,
                updates_applied=[],
                affected_nodes=set(),
                affected_edges=set()
            )
            mock_handle.return_value = mock_result
            
            result = self.updater.update_from_file_changes(file_path, [], [])
            
            # 验证调用了文件删除处理
            mock_handle.assert_called_once_with(file_path)
            assert result == mock_result
    
    def test_update_from_file_changes_with_elements(self):
        """测试处理文件更新（有元素）"""
        file_path = "/test/updated_file.py"
        elements = [
            CodeElement(
                id="elem1",
                name="TestClass",
                type=ElementType.CLASS,
                file_path=file_path,
                line_number=1
            )
        ]
        relationships = [
            Relationship(
                source_id="elem1",
                target_id="elem2",
                type=RelationType.CALLS
            )
        ]
        
        # 模拟文件更新处理
        with patch.object(self.updater, '_handle_file_update') as mock_handle:
            mock_result = UpdateResult(
                success=True,
                updates_applied=[GraphUpdate(UpdateType.ADD_NODE, node_id="node1")],
                affected_nodes={"node1"},
                affected_edges=set()
            )
            mock_handle.return_value = mock_result
            
            result = self.updater.update_from_file_changes(file_path, elements, relationships)
            
            # 验证调用了文件更新处理
            mock_handle.assert_called_once_with(file_path, elements, relationships)
            assert result == mock_result
    
    def test_update_from_file_changes_exception(self):
        """测试处理异常情况"""
        file_path = "/test/error_file.py"
        
        # 模拟异常
        with patch.object(self.updater, '_handle_file_deletion') as mock_handle:
            mock_handle.side_effect = Exception("Test error")
            
            result = self.updater.update_from_file_changes(file_path, [], [])
            
            # 验证返回失败结果
            assert result.success is False
            assert result.error_message == "Test error"
            assert len(result.updates_applied) == 0
    
    def test_handle_file_deletion_no_elements(self):
        """测试处理没有元素的文件删除"""
        file_path = "/test/empty_file.py"
        
        # 文件映射中没有元素
        result = self.updater._handle_file_deletion(file_path)
        
        # 验证返回成功但无操作
        assert result.success is True
        assert len(result.updates_applied) == 0
        assert len(result.affected_nodes) == 0
    
    def test_handle_file_deletion_with_elements(self):
        """测试处理有元素的文件删除"""
        file_path = "/test/file_with_elements.py"
        element_ids = {"elem1", "elem2"}
        
        # 设置文件映射
        self.updater._file_to_elements[file_path] = element_ids
        for elem_id in element_ids:
            self.updater._element_to_file[elem_id] = file_path
        
        # 模拟依赖分析
        self.updater.dependency_analyzer.analyze_dependencies = Mock(return_value={"dep1"})
        
        # 模拟数据库操作
        mock_session = Mock()
        mock_tx = Mock()
        
        # 设置会话上下文管理器
        mock_session_context = Mock()
        mock_session_context.__enter__ = Mock(return_value=mock_session)
        mock_session_context.__exit__ = Mock(return_value=None)
        self.mock_database.session.return_value = mock_session_context
        
        # 设置事务上下文管理器
        mock_tx_context = Mock()
        mock_tx_context.__enter__ = Mock(return_value=mock_tx)
        mock_tx_context.__exit__ = Mock(return_value=None)
        mock_session.begin_transaction.return_value = mock_tx_context
        
        # 模拟查询结果 - 创建正确的记录对象
        class MockRecord:
            def __init__(self, data):
                self.data = data
            
            def get(self, key, default=None):
                return self.data.get(key, default)
            
            def __getitem__(self, key):
                return self.data[key]
        
        mock_tx.run.side_effect = [
            [MockRecord({"deleted_edges": 2})],  # 删除边的结果
            [MockRecord({"node_id": "node1"})],  # 删除节点的结果
            [MockRecord({"deleted_edges": 1})],  # 第二个元素删除边的结果
            [MockRecord({"node_id": "node2"})]   # 第二个元素删除节点的结果
        ]
        
        # 调用删除处理
        result = self.updater._handle_file_deletion(file_path)
        
        # 验证结果
        assert result.success is True
        assert len(result.updates_applied) > 0
        
        # 验证映射被清理
        assert file_path not in self.updater._file_to_elements
        for elem_id in element_ids:
            assert elem_id not in self.updater._element_to_file
    
    def test_get_affected_elements(self):
        """测试获取受影响的元素"""
        element_ids = {"elem1", "elem2"}
        
        # 模拟依赖分析
        def mock_analyze(elem_id):
            if elem_id == "elem1":
                return {"dep1", "dep2"}
            elif elem_id == "elem2":
                return {"dep3"}
            return set()
        
        self.updater.dependency_analyzer.analyze_dependencies = mock_analyze
        
        # 获取受影响的元素
        affected = self.updater.get_affected_elements(element_ids)
        
        # 验证结果包含原始元素和依赖
        expected = {"elem1", "elem2", "dep1", "dep2", "dep3"}
        assert affected == expected
    
    def test_rebuild_file_mappings(self):
        """测试重建文件映射"""
        # 模拟数据库查询结果
        mock_session = Mock()
        mock_context_manager = Mock()
        mock_context_manager.__enter__ = Mock(return_value=mock_session)
        mock_context_manager.__exit__ = Mock(return_value=None)
        self.mock_database.session.return_value = mock_context_manager
        
        # 模拟查询结果
        mock_session.run.return_value = [
            {"element_id": "elem1", "file_path": "/test/file1.py"},
            {"element_id": "elem2", "file_path": "/test/file1.py"},
            {"element_id": "elem3", "file_path": "/test/file2.py"}
        ]
        
        # 调用重建
        self.updater.rebuild_file_mappings()
        
        # 验证映射被正确构建
        assert len(self.updater._file_to_elements) == 2
        assert self.updater._file_to_elements["/test/file1.py"] == {"elem1", "elem2"}
        assert self.updater._file_to_elements["/test/file2.py"] == {"elem3"}
        
        assert len(self.updater._element_to_file) == 3
        assert self.updater._element_to_file["elem1"] == "/test/file1.py"
        assert self.updater._element_to_file["elem2"] == "/test/file1.py"
        assert self.updater._element_to_file["elem3"] == "/test/file2.py"
    
    def test_rebuild_file_mappings_database_error(self):
        """测试重建文件映射时的数据库错误"""
        # 模拟数据库错误
        self.mock_database.session.side_effect = Exception("Database error")
        
        # 调用重建（不应该抛出异常）
        self.updater.rebuild_file_mappings()
        
        # 验证映射被清空
        assert len(self.updater._file_to_elements) == 0
        assert len(self.updater._element_to_file) == 0


class TestConvenienceFunctions:
    """测试便捷函数"""
    
    def test_create_incremental_updater(self):
        """测试创建增量更新器"""
        mock_builder = Mock()
        mock_database = Mock()
        
        updater = create_incremental_updater(mock_builder, mock_database)
        
        assert isinstance(updater, IncrementalGraphUpdater)
        assert updater.graph_builder == mock_builder
        assert updater.graph_database == mock_database


if __name__ == "__main__":
    pytest.main([__file__])