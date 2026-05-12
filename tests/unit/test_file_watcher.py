"""
文件监控服务单元测试
"""

import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from src.codenexus.services.file_watcher import (
    FileWatcher, IncrementalParseManager, FileChange, WatchConfig, 
    ChangeType, create_file_watcher, create_incremental_parse_manager
)
from src.codenexus.models.core import CodeElement, Relationship, ElementType, RelationType


class TestWatchConfig:
    """测试监控配置"""
    
    def test_default_config(self):
        """测试默认配置"""
        config = WatchConfig(watch_paths=["/test"])
        
        assert config.watch_paths == ["/test"]
        assert config.poll_interval == 1.0
        assert config.debounce_delay == 0.5
        assert "*.pyc" in config.ignore_patterns
        assert ".py" in config.supported_extensions
    
    def test_custom_config(self):
        """测试自定义配置"""
        config = WatchConfig(
            watch_paths=["/test1", "/test2"],
            ignore_patterns=["*.tmp"],
            supported_extensions=[".py", ".java"],
            poll_interval=2.0,
            debounce_delay=1.0
        )
        
        assert config.watch_paths == ["/test1", "/test2"]
        assert config.ignore_patterns == ["*.tmp"]
        assert config.supported_extensions == [".py", ".java"]
        assert config.poll_interval == 2.0
        assert config.debounce_delay == 1.0


class TestFileChange:
    """测试文件变更事件"""
    
    def test_file_change_creation(self):
        """测试文件变更事件创建"""
        change = FileChange(
            path="/test/file.py",
            change_type=ChangeType.CREATED,
            timestamp=time.time(),
            file_hash="abc123"
        )
        
        assert change.path == "/test/file.py"
        assert change.change_type == ChangeType.CREATED
        assert change.file_hash == "abc123"
        assert change.old_path is None
    
    def test_file_move_change(self):
        """测试文件移动变更"""
        change = FileChange(
            path="/test/new_file.py",
            change_type=ChangeType.MOVED,
            timestamp=time.time(),
            old_path="/test/old_file.py"
        )
        
        assert change.path == "/test/new_file.py"
        assert change.change_type == ChangeType.MOVED
        assert change.old_path == "/test/old_file.py"


class TestFileWatcher:
    """测试文件监控器"""
    
    def setup_method(self):
        """测试设置"""
        self.temp_dir = tempfile.mkdtemp()
        self.config = WatchConfig(
            watch_paths=[self.temp_dir],
            poll_interval=0.1,  # 快速轮询用于测试
            debounce_delay=0.1
        )
        self.watcher = FileWatcher(self.config)
        self.changes_received = []
        
        def change_handler(changes):
            self.changes_received.extend(changes)
        
        self.watcher.add_change_handler(change_handler)
    
    def teardown_method(self):
        """测试清理"""
        if self.watcher._is_running:
            self.watcher.stop()
        
        # 清理临时目录
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_should_monitor_file(self):
        """测试文件监控判断"""
        # 支持的文件
        assert self.watcher._should_monitor_file("/test/file.py")
        assert self.watcher._should_monitor_file("/test/file.java")
        
        # 不支持的文件
        assert not self.watcher._should_monitor_file("/test/file.txt")
        assert not self.watcher._should_monitor_file("/test/file.pyc")
    
    def test_should_ignore(self):
        """测试忽略模式"""
        assert self.watcher._should_ignore("__pycache__")
        assert self.watcher._should_ignore("file.pyc")
        assert self.watcher._should_ignore(".git")
        assert not self.watcher._should_ignore("file.py")
    
    def test_calculate_file_hash(self):
        """测试文件哈希计算"""
        test_file = os.path.join(self.temp_dir, "test.py")
        
        with open(test_file, 'w') as f:
            f.write("print('hello')")
        
        hash1 = self.watcher._calculate_file_hash(test_file)
        assert hash1
        
        # 相同内容应该有相同哈希
        hash2 = self.watcher._calculate_file_hash(test_file)
        assert hash1 == hash2
        
        # 修改内容后哈希应该不同
        with open(test_file, 'w') as f:
            f.write("print('world')")
        
        hash3 = self.watcher._calculate_file_hash(test_file)
        assert hash1 != hash3
    
    def test_scan_directory(self):
        """测试目录扫描"""
        # 创建测试文件
        test_files = [
            "test1.py",
            "test2.java",
            "test3.txt",  # 不支持的扩展名
            "test4.pyc"   # 忽略的文件
        ]
        
        for filename in test_files:
            with open(os.path.join(self.temp_dir, filename), 'w') as f:
                f.write("test content")
        
        # 创建子目录
        sub_dir = os.path.join(self.temp_dir, "subdir")
        os.makedirs(sub_dir)
        with open(os.path.join(sub_dir, "sub.py"), 'w') as f:
            f.write("sub content")
        
        files = self.watcher._scan_directory(self.temp_dir)
        
        # 应该只包含支持的文件
        file_names = [os.path.basename(f) for f in files]
        assert "test1.py" in file_names
        assert "test2.java" in file_names
        assert "sub.py" in file_names
        assert "test3.txt" not in file_names
        assert "test4.pyc" not in file_names
    
    def test_change_handler_management(self):
        """测试变更处理器管理"""
        handler1 = Mock()
        handler1.__name__ = "handler1"  # 添加__name__属性
        handler2 = Mock()
        handler2.__name__ = "handler2"  # 添加__name__属性
        
        # 添加处理器
        self.watcher.add_change_handler(handler1)
        self.watcher.add_change_handler(handler2)
        assert len(self.watcher._change_handlers) == 3  # 包括setup中的处理器
        
        # 移除处理器
        self.watcher.remove_change_handler(handler1)
        assert len(self.watcher._change_handlers) == 2
        assert handler1 not in self.watcher._change_handlers
        assert handler2 in self.watcher._change_handlers
    
    def test_file_creation_detection(self):
        """测试文件创建检测"""
        # 启动监控
        self.watcher.start()
        
        # 创建新文件
        test_file = os.path.join(self.temp_dir, "new_file.py")
        with open(test_file, 'w') as f:
            f.write("print('new file')")
        
        # 等待检测
        time.sleep(0.3)
        
        # 停止监控
        self.watcher.stop()
        
        # 验证检测到创建事件
        assert len(self.changes_received) > 0
        create_changes = [c for c in self.changes_received if c.change_type == ChangeType.CREATED]
        assert len(create_changes) > 0
        assert any(c.path == test_file for c in create_changes)
    
    def test_file_modification_detection(self):
        """测试文件修改检测"""
        # 先创建文件
        test_file = os.path.join(self.temp_dir, "modify_test.py")
        with open(test_file, 'w') as f:
            f.write("original content")
        
        # 启动监控（会初始化文件状态）
        self.watcher.start()
        time.sleep(0.2)  # 等待初始化完成
        
        # 清空之前的变更记录
        self.changes_received.clear()
        
        # 修改文件
        with open(test_file, 'w') as f:
            f.write("modified content")
        
        # 等待检测
        time.sleep(0.3)
        
        # 停止监控
        self.watcher.stop()
        
        # 验证检测到修改事件
        modify_changes = [c for c in self.changes_received if c.change_type == ChangeType.MODIFIED]
        assert len(modify_changes) > 0
        assert any(c.path == test_file for c in modify_changes)
    
    def test_file_deletion_detection(self):
        """测试文件删除检测"""
        # 先创建文件
        test_file = os.path.join(self.temp_dir, "delete_test.py")
        with open(test_file, 'w') as f:
            f.write("to be deleted")
        
        # 启动监控
        self.watcher.start()
        time.sleep(0.2)  # 等待初始化完成
        
        # 清空之前的变更记录
        self.changes_received.clear()
        
        # 删除文件
        os.remove(test_file)
        
        # 等待检测
        time.sleep(0.3)
        
        # 停止监控
        self.watcher.stop()
        
        # 验证检测到删除事件
        delete_changes = [c for c in self.changes_received if c.change_type == ChangeType.DELETED]
        assert len(delete_changes) > 0
        assert any(c.path == test_file for c in delete_changes)


class TestIncrementalParseManager:
    """测试增量解析管理器"""
    
    def setup_method(self):
        """测试设置"""
        self.temp_dir = tempfile.mkdtemp()
        self.mock_parser = Mock()
        self.file_watcher = create_file_watcher([self.temp_dir], poll_interval=0.1)
        self.manager = IncrementalParseManager(self.mock_parser, self.file_watcher)
        self.parse_results = []
        
        def parse_handler(file_path, elements, relationships):
            self.parse_results.append((file_path, elements, relationships))
        
        self.manager.add_parse_handler(parse_handler)
    
    def teardown_method(self):
        """测试清理"""
        if self.manager.file_watcher._is_running:
            self.manager.stop()
        
        # 清理临时目录
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_parse_handler_management(self):
        """测试解析处理器管理"""
        handler1 = Mock()
        handler1.__name__ = "handler1"  # 添加__name__属性
        handler2 = Mock()
        handler2.__name__ = "handler2"  # 添加__name__属性
        
        # 添加处理器
        self.manager.add_parse_handler(handler1)
        self.manager.add_parse_handler(handler2)
        assert len(self.manager._parse_handlers) == 3  # 包括setup中的处理器
        
        # 移除处理器
        self.manager.remove_parse_handler(handler1)
        assert len(self.manager._parse_handlers) == 2
        assert handler1 not in self.manager._parse_handlers
        assert handler2 in self.manager._parse_handlers
    
    def test_handle_file_creation(self):
        """测试处理文件创建"""
        # 模拟解析结果
        mock_result = Mock()
        mock_result.elements = [
            CodeElement(
                id="test_func",
                name="test_function",
                type=ElementType.FUNCTION,
                file_path="/test/file.py",
                line_number=1
            )
        ]
        mock_result.relationships = [
            Relationship(
                source_id="test_func",
                target_id="other_func",
                type=RelationType.CALLS
            )
        ]
        self.mock_parser.parse_file.return_value = mock_result
        
        # 创建文件变更事件
        change = FileChange(
            path=os.path.join(self.temp_dir, "test.py"),
            change_type=ChangeType.CREATED,
            timestamp=time.time()
        )
        
        # 处理变更
        self.manager._handle_file_changes([change])
        
        # 验证解析器被调用
        self.mock_parser.parse_file.assert_called_once_with(change.path)
        
        # 验证解析结果被处理
        assert len(self.parse_results) == 1
        file_path, elements, relationships = self.parse_results[0]
        assert file_path == change.path
        assert len(elements) == 1
        assert elements[0].name == "test_function"
        assert len(relationships) == 1
    
    def test_handle_file_deletion(self):
        """测试处理文件删除"""
        # 创建删除事件
        change = FileChange(
            path="/test/deleted.py",
            change_type=ChangeType.DELETED,
            timestamp=time.time()
        )
        
        # 处理变更
        self.manager._handle_file_changes([change])
        
        # 验证解析器没有被调用（删除的文件不需要解析）
        self.mock_parser.parse_file.assert_not_called()
        
        # 验证删除事件被处理（空的元素和关系列表）
        assert len(self.parse_results) == 1
        file_path, elements, relationships = self.parse_results[0]
        assert file_path == change.path
        assert len(elements) == 0
        assert len(relationships) == 0
    
    def test_handle_file_move(self):
        """测试处理文件移动"""
        # 模拟解析结果
        mock_result = Mock()
        mock_result.elements = [CodeElement(
            id="moved_func",
            name="moved_function", 
            type=ElementType.FUNCTION,
            file_path="/test/new_file.py",
            line_number=1
        )]
        mock_result.relationships = []
        self.mock_parser.parse_file.return_value = mock_result
        
        # 创建移动事件
        change = FileChange(
            path="/test/new_file.py",
            change_type=ChangeType.MOVED,
            timestamp=time.time(),
            old_path="/test/old_file.py"
        )
        
        # 处理变更
        self.manager._handle_file_changes([change])
        
        # 验证解析器被调用（解析新位置的文件）
        self.mock_parser.parse_file.assert_called_once_with(change.path)
        
        # 验证两个事件被处理：删除旧文件 + 创建新文件
        assert len(self.parse_results) == 2
        
        # 第一个应该是删除事件
        old_file_path, old_elements, old_relationships = self.parse_results[0]
        assert old_file_path == change.old_path
        assert len(old_elements) == 0
        assert len(old_relationships) == 0
        
        # 第二个应该是创建事件
        new_file_path, new_elements, new_relationships = self.parse_results[1]
        assert new_file_path == change.path
        assert len(new_elements) == 1
        assert new_elements[0].name == "moved_function"


class TestConvenienceFunctions:
    """测试便捷函数"""
    
    def test_create_file_watcher(self):
        """测试创建文件监控器"""
        watcher = create_file_watcher(
            watch_paths=["/test"],
            poll_interval=2.0,
            debounce_delay=1.0
        )
        
        assert isinstance(watcher, FileWatcher)
        assert watcher.config.watch_paths == ["/test"]
        assert watcher.config.poll_interval == 2.0
        assert watcher.config.debounce_delay == 1.0
    
    def test_create_incremental_parse_manager(self):
        """测试创建增量解析管理器"""
        mock_parser = Mock()
        manager = create_incremental_parse_manager(
            parser=mock_parser,
            watch_paths=["/test"],
            poll_interval=2.0
        )
        
        assert isinstance(manager, IncrementalParseManager)
        assert manager.parser == mock_parser
        assert isinstance(manager.file_watcher, FileWatcher)
        assert manager.file_watcher.config.watch_paths == ["/test"]
        assert manager.file_watcher.config.poll_interval == 2.0


if __name__ == "__main__":
    pytest.main([__file__])