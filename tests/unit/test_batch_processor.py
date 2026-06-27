"""
批处理器测试
"""

import asyncio
import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import pytest

from src.codenexus.services.batch_processor import (
    BatchProcessor, BatchConfig, MemoryMonitor, 
    ProcessingStats, ProgressTracker
)


class TestBatchProcessor:
    """批处理器测试类"""
    
    def test_batch_config_defaults(self):
        """测试批处理配置默认值"""
        config = BatchConfig()
        
        assert config.batch_size == 50
        assert config.memory_limit_mb == 2048
        assert config.timeout_seconds == 300
        assert config.enable_gc is True
        assert config.chunk_size == 10
    
    def test_batch_processor_initialization(self):
        """测试批处理器初始化"""
        config = BatchConfig(batch_size=100, max_workers=4)
        processor = BatchProcessor(config)
        
        assert processor.config.batch_size == 100
        assert processor.config.max_workers == 4
        assert isinstance(processor.stats, ProcessingStats)
    
    def test_find_source_files(self):
        """测试查找源代码文件"""
        processor = BatchProcessor()
        
        # 创建临时目录和文件
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # 创建测试文件
            (temp_path / "test.py").write_text("print('hello')")
            (temp_path / "test.java").write_text("public class Test {}")
            (temp_path / "test.js").write_text("console.log('hello');")
            (temp_path / "test.txt").write_text("not a source file")
            
            # 创建排除目录
            node_modules = temp_path / "node_modules"
            node_modules.mkdir()
            (node_modules / "package.js").write_text("// should be excluded")
            
            source_files = processor._find_source_files(str(temp_path))
            
            # 验证结果
            assert len(source_files) == 3  # 只有源代码文件
            file_names = [Path(f).name for f in source_files]
            assert "test.py" in file_names
            assert "test.java" in file_names
            assert "test.js" in file_names
            assert "test.txt" not in file_names
            assert "package.js" not in file_names  # 应该被排除
    
    def test_create_batches(self):
        """测试创建批次"""
        processor = BatchProcessor(BatchConfig(batch_size=3))
        
        files = ["file1.py", "file2.py", "file3.py", "file4.py", "file5.py"]
        batches = processor._create_batches(files)
        
        assert len(batches) == 2
        assert len(batches[0]) == 3
        assert len(batches[1]) == 2
        assert batches[0] == ["file1.py", "file2.py", "file3.py"]
        assert batches[1] == ["file4.py", "file5.py"]
    
    def test_create_chunks(self):
        """测试创建文件块"""
        processor = BatchProcessor()
        
        files = ["file1.py", "file2.py", "file3.py", "file4.py", "file5.py"]
        chunks = processor._create_chunks(files, chunk_size=2)
        
        assert len(chunks) == 3
        assert chunks[0] == ["file1.py", "file2.py"]
        assert chunks[1] == ["file3.py", "file4.py"]
        assert chunks[2] == ["file5.py"]
    
    @patch('psutil.Process')
    def test_get_processing_stats(self, mock_process):
        """测试获取处理统计信息"""
        # 模拟psutil.Process
        mock_process_instance = Mock()
        mock_process_instance.memory_info.return_value.rss = 1024 * 1024 * 100  # 100MB
        mock_process_instance.cpu_percent.return_value = 50.0
        mock_process.return_value = mock_process_instance
        
        processor = BatchProcessor()
        processor.stats.total_files = 100
        processor.stats.processed_files = 80
        processor.stats.failed_files = 5
        
        stats = processor.get_processing_stats()
        
        assert stats.total_files == 100
        assert stats.processed_files == 80
        assert stats.failed_files == 5
        assert stats.memory_usage_mb == 100.0
        assert stats.cpu_usage_percent == 50.0


class TestMemoryMonitor:
    """内存监控器测试类"""
    
    @patch('psutil.Process')
    def test_memory_monitor_thresholds(self, mock_process):
        """测试内存监控阈值"""
        # 模拟psutil.Process
        mock_process_instance = Mock()
        mock_process.return_value = mock_process_instance
        
        monitor = MemoryMonitor(memory_limit_mb=1000)
        
        # 测试正常内存使用
        mock_process_instance.memory_info.return_value.rss = 500 * 1024 * 1024  # 500MB
        assert not monitor.should_trigger_gc()
        assert not monitor.is_memory_critical()
        
        # 测试警告阈值
        mock_process_instance.memory_info.return_value.rss = 850 * 1024 * 1024  # 850MB
        assert monitor.should_trigger_gc()
        assert not monitor.is_memory_critical()
        
        # 测试临界阈值
        mock_process_instance.memory_info.return_value.rss = 950 * 1024 * 1024  # 950MB
        assert monitor.should_trigger_gc()
        assert monitor.is_memory_critical()
    
    @patch('psutil.Process')
    def test_get_memory_usage_percent(self, mock_process):
        """测试获取内存使用百分比"""
        mock_process_instance = Mock()
        mock_process_instance.memory_info.return_value.rss = 500 * 1024 * 1024  # 500MB
        mock_process.return_value = mock_process_instance
        
        monitor = MemoryMonitor(memory_limit_mb=1000)
        usage_percent = monitor.get_memory_usage_percent()
        
        assert usage_percent == 50.0


class TestProgressTracker:
    """进度跟踪器测试类"""
    
    def test_progress_tracker_initialization(self):
        """测试进度跟踪器初始化"""
        tracker = ProgressTracker(total_items=100)
        
        assert tracker.total_items == 100
        assert tracker.processed_items == 0
        assert tracker.start_time is not None
    
    def test_progress_update(self):
        """测试进度更新"""
        tracker = ProgressTracker(total_items=100)
        
        # 更新进度
        tracker.update(50)
        assert tracker.processed_items == 50
        
        # 再次更新
        tracker.update(80)
        assert tracker.processed_items == 80
    
    @patch('src.codeweaver.services.batch_processor.logger')
    @patch('src.codeweaver.services.batch_processor.time')
    def test_progress_logging(self, mock_time, mock_logger):
        """测试进度日志记录"""
        # 设置时间模拟
        mock_time.time.side_effect = [0, 0, 2]  # 初始化时间，last_update_time，当前时间
        
        tracker = ProgressTracker(total_items=100)
        
        # 手动设置时间以确保触发日志
        tracker.start_time = 0
        tracker.last_update_time = 0
        
        tracker.update(50)
        
        # 验证日志被调用
        mock_logger.info.assert_called()
        call_args = mock_logger.info.call_args[0][0]
        assert "50/100" in call_args
        assert "50.0%" in call_args


@pytest.mark.asyncio
class TestAsyncBatchProcessor:
    """异步批处理器测试类"""
    
    async def test_process_project_parallel_empty_directory(self):
        """测试处理空目录"""
        processor = BatchProcessor()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            results = await processor.process_project_parallel(temp_dir)
            assert results == []
            assert processor.stats.total_files == 0
    
    @patch('src.codeweaver.services.batch_processor.process_file_chunk')
    async def test_process_project_parallel_with_files(self, mock_process_chunk):
        """测试并行处理项目文件"""
        # 创建一个真实的解析结果而不是mock
        from src.codenexus.models.core import CodeElement, Relationship
        
        real_parse_result = {
            'elements': [CodeElement(
                id="test_1",
                name="test_function",
                type="function",
                file_path="test.py",
                line_number=1,
                complexity=1
            )],
            'relationships': []
        }
        
        # 使用真实的函数而不是mock
        def real_process_chunk(file_paths, parser_factory):
            return [real_parse_result]
        
        mock_process_chunk.side_effect = real_process_chunk
        
        processor = BatchProcessor(BatchConfig(batch_size=2, max_workers=1))
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # 创建测试文件
            (temp_path / "test1.py").write_text("print('test1')")
            (temp_path / "test2.py").write_text("print('test2')")
            (temp_path / "test3.py").write_text("print('test3')")
            
            results = await processor.process_project_parallel(temp_dir)
            
            # 验证结果
            assert len(results) >= 1  # 至少有一些结果
            assert processor.stats.total_files == 3
    
    async def test_progress_callback(self):
        """测试进度回调"""
        progress_calls = []
        
        def progress_callback(processed, total):
            progress_calls.append((processed, total))
        
        processor = BatchProcessor(BatchConfig(batch_size=1))
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            (temp_path / "test.py").write_text("print('test')")
            
            with patch('src.codeweaver.services.batch_processor.process_file_chunk') as mock_process:
                mock_process.return_value = []
                
                await processor.process_project_parallel(
                    temp_dir, 
                    progress_callback=progress_callback
                )
                
                # 验证进度回调被调用
                assert len(progress_calls) > 0
                final_call = progress_calls[-1]
                assert final_call[0] == final_call[1]  # 最终进度应该是100%


if __name__ == "__main__":
    pytest.main([__file__])