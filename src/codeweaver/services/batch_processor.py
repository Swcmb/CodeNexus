"""
批处理器

实现分批处理和并行解析，优化大型项目的处理性能。
"""

import asyncio
import gc
import logging
import multiprocessing
import os
import time
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Callable
from dataclasses import dataclass
import psutil

from ..models.core import ParseResult, FileParseResult
from ..parser.tree_sitter_parser import TreeSitterParser
from ..exceptions import ParseError


logger = logging.getLogger(__name__)


@dataclass
class BatchConfig:
    """批处理配置"""
    batch_size: int = 50  # 每批处理的文件数量
    max_workers: int = None  # 最大工作进程数，None表示自动检测
    memory_limit_mb: int = 2048  # 内存限制（MB）
    timeout_seconds: int = 300  # 单个文件处理超时时间
    enable_gc: bool = True  # 是否启用垃圾回收优化
    chunk_size: int = 10  # 每个工作进程处理的文件块大小


@dataclass
class ProcessingStats:
    """处理统计信息"""
    total_files: int = 0
    processed_files: int = 0
    failed_files: int = 0
    total_time: float = 0.0
    avg_time_per_file: float = 0.0
    memory_usage_mb: float = 0.0
    cpu_usage_percent: float = 0.0


class BatchProcessor:
    """批处理器类
    
    提供分批处理和并行解析功能，优化大型项目处理。
    """
    
    def __init__(self, config: Optional[BatchConfig] = None):
        """初始化批处理器
        
        Args:
            config: 批处理配置
        """
        self.config = config or BatchConfig()
        
        # 自动检测最大工作进程数
        if self.config.max_workers is None:
            self.config.max_workers = min(
                multiprocessing.cpu_count(),
                max(1, multiprocessing.cpu_count() - 1)  # 保留一个CPU核心
            )
        
        self.stats = ProcessingStats()
        self._memory_monitor = MemoryMonitor(self.config.memory_limit_mb)
        
        logger.info(f"批处理器初始化完成，配置: {self.config}")
    
    async def process_project_parallel(
        self, 
        project_path: str,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> List[ParseResult]:
        """并行处理整个项目
        
        Args:
            project_path: 项目路径
            progress_callback: 进度回调函数 (processed, total)
            
        Returns:
            解析结果列表
        """
        start_time = time.time()
        
        try:
            # 查找所有源代码文件
            source_files = self._find_source_files(project_path)
            self.stats.total_files = len(source_files)
            
            logger.info(f"开始并行处理项目: {project_path}, 文件数: {len(source_files)}")
            
            if not source_files:
                logger.warning("未找到源代码文件")
                return []
            
            # 分批处理文件
            all_results = []
            batches = self._create_batches(source_files)
            
            for batch_idx, batch_files in enumerate(batches):
                logger.info(f"处理批次 {batch_idx + 1}/{len(batches)}, 文件数: {len(batch_files)}")
                
                # 检查内存使用情况
                if self._memory_monitor.should_trigger_gc():
                    logger.info("触发垃圾回收以释放内存")
                    gc.collect()
                
                # 并行处理当前批次
                batch_results = await self._process_batch_parallel(batch_files)
                all_results.extend(batch_results)
                
                # 更新统计信息
                self.stats.processed_files += len(batch_files)
                
                # 调用进度回调
                if progress_callback:
                    progress_callback(self.stats.processed_files, self.stats.total_files)
                
                # 检查是否需要暂停以避免内存溢出
                if self._memory_monitor.is_memory_critical():
                    logger.warning("内存使用过高，暂停处理")
                    await asyncio.sleep(1)
                    gc.collect()
            
            # 更新最终统计信息
            self.stats.total_time = time.time() - start_time
            if self.stats.processed_files > 0:
                self.stats.avg_time_per_file = self.stats.total_time / self.stats.processed_files
            
            logger.info(f"项目处理完成，统计信息: {self.stats}")
            return all_results
            
        except Exception as e:
            logger.error(f"并行处理项目失败: {e}")
            raise ParseError(f"Failed to process project in parallel: {e}")
    
    async def _process_batch_parallel(self, file_paths: List[str]) -> List[ParseResult]:
        """并行处理一批文件
        
        Args:
            file_paths: 文件路径列表
            
        Returns:
            解析结果列表
        """
        results = []
        
        # 创建文件块
        chunks = self._create_chunks(file_paths, self.config.chunk_size)
        
        # 使用进程池并行处理
        with ProcessPoolExecutor(max_workers=self.config.max_workers) as executor:
            # 提交所有任务
            future_to_chunk = {
                executor.submit(process_file_chunk, chunk): chunk 
                for chunk in chunks
            }
            
            # 收集结果
            for future in as_completed(future_to_chunk):
                chunk = future_to_chunk[future]
                try:
                    chunk_results = future.result(timeout=self.config.timeout_seconds)
                    results.extend(chunk_results)
                except Exception as e:
                    logger.error(f"处理文件块失败: {chunk}, 错误: {e}")
                    self.stats.failed_files += len(chunk)
        
        return results
    
    def _find_source_files(self, project_path: str) -> List[str]:
        """查找项目中的所有源代码文件
        
        Args:
            project_path: 项目路径
            
        Returns:
            源代码文件路径列表
        """
        project_dir = Path(project_path)
        if not project_dir.exists():
            raise ParseError(f"项目路径不存在: {project_path}")
        
        # 支持的文件扩展名
        extensions = {".py", ".java", ".js", ".jsx", ".ts", ".tsx", ".cs"}
        
        # 需要排除的目录
        exclude_dirs = {
            "node_modules", ".git", "__pycache__", ".pytest_cache",
            "build", "dist", "target", "bin", "obj", ".vscode", ".idea"
        }
        
        source_files = []
        
        for root, dirs, files in os.walk(project_dir):
            # 过滤掉排除的目录
            dirs[:] = [d for d in dirs if d not in exclude_dirs]
            
            for file in files:
                if Path(file).suffix.lower() in extensions:
                    file_path = os.path.join(root, file)
                    # 检查文件大小，跳过过大的文件（可能是生成的文件）
                    try:
                        if os.path.getsize(file_path) < 10 * 1024 * 1024:  # 10MB限制
                            source_files.append(file_path)
                    except OSError:
                        continue
        
        logger.info(f"找到 {len(source_files)} 个源代码文件")
        return source_files
    
    def _create_batches(self, file_paths: List[str]) -> List[List[str]]:
        """将文件列表分成批次
        
        Args:
            file_paths: 文件路径列表
            
        Returns:
            批次列表
        """
        batches = []
        for i in range(0, len(file_paths), self.config.batch_size):
            batch = file_paths[i:i + self.config.batch_size]
            batches.append(batch)
        
        return batches
    
    def _create_chunks(self, file_paths: List[str], chunk_size: int) -> List[List[str]]:
        """将文件列表分成块
        
        Args:
            file_paths: 文件路径列表
            chunk_size: 块大小
            
        Returns:
            文件块列表
        """
        chunks = []
        for i in range(0, len(file_paths), chunk_size):
            chunk = file_paths[i:i + chunk_size]
            chunks.append(chunk)
        
        return chunks
    
    def get_processing_stats(self) -> ProcessingStats:
        """获取处理统计信息
        
        Returns:
            处理统计信息
        """
        # 更新当前内存和CPU使用情况
        process = psutil.Process()
        self.stats.memory_usage_mb = process.memory_info().rss / 1024 / 1024
        self.stats.cpu_usage_percent = process.cpu_percent()
        
        return self.stats
    
    def reset_stats(self):
        """重置统计信息"""
        self.stats = ProcessingStats()


class MemoryMonitor:
    """内存监控器"""
    
    def __init__(self, memory_limit_mb: int):
        """初始化内存监控器
        
        Args:
            memory_limit_mb: 内存限制（MB）
        """
        self.memory_limit_mb = memory_limit_mb
        self.warning_threshold = memory_limit_mb * 0.8  # 80%警告阈值
        self.critical_threshold = memory_limit_mb * 0.9  # 90%临界阈值
    
    def get_current_memory_mb(self) -> float:
        """获取当前内存使用量（MB）
        
        Returns:
            内存使用量（MB）
        """
        process = psutil.Process()
        return process.memory_info().rss / 1024 / 1024
    
    def should_trigger_gc(self) -> bool:
        """是否应该触发垃圾回收
        
        Returns:
            是否应该触发垃圾回收
        """
        current_memory = self.get_current_memory_mb()
        return current_memory > self.warning_threshold
    
    def is_memory_critical(self) -> bool:
        """内存使用是否达到临界状态
        
        Returns:
            是否达到临界状态
        """
        current_memory = self.get_current_memory_mb()
        return current_memory > self.critical_threshold
    
    def get_memory_usage_percent(self) -> float:
        """获取内存使用百分比
        
        Returns:
            内存使用百分比
        """
        current_memory = self.get_current_memory_mb()
        return (current_memory / self.memory_limit_mb) * 100


def process_file_chunk(file_paths: List[str]) -> List[ParseResult]:
    """处理文件块（在独立进程中运行）
    
    Args:
        file_paths: 文件路径列表
        
    Returns:
        解析结果列表
    """
    results = []
    parser = TreeSitterParser()
    
    for file_path in file_paths:
        try:
            file_result = parser.parse_file(file_path)
            if file_result.success and file_result.parse_result:
                results.append(file_result.parse_result)
        except Exception as e:
            logger.warning(f"处理文件失败: {file_path}, 错误: {e}")
            continue
    
    return results


class StreamingProcessor:
    """流式处理器
    
    用于处理超大型项目，采用流式处理避免内存溢出。
    """
    
    def __init__(self, batch_size: int = 10):
        """初始化流式处理器
        
        Args:
            batch_size: 批处理大小
        """
        self.batch_size = batch_size
        self.parser = TreeSitterParser()
    
    async def process_project_streaming(
        self,
        project_path: str,
        result_handler: Callable[[ParseResult], None],
        progress_callback: Optional[Callable[[int, int], None]] = None
    ):
        """流式处理项目
        
        Args:
            project_path: 项目路径
            result_handler: 结果处理函数
            progress_callback: 进度回调函数
        """
        source_files = self._find_source_files(project_path)
        total_files = len(source_files)
        processed_files = 0
        
        logger.info(f"开始流式处理项目: {project_path}, 文件数: {total_files}")
        
        # 分批处理文件
        for i in range(0, len(source_files), self.batch_size):
            batch_files = source_files[i:i + self.batch_size]
            
            # 处理当前批次
            for file_path in batch_files:
                try:
                    file_result = self.parser.parse_file(file_path)
                    if file_result.success and file_result.parse_result:
                        # 立即处理结果，不在内存中累积
                        result_handler(file_result.parse_result)
                    
                    processed_files += 1
                    
                    # 调用进度回调
                    if progress_callback:
                        progress_callback(processed_files, total_files)
                        
                except Exception as e:
                    logger.warning(f"流式处理文件失败: {file_path}, 错误: {e}")
                    continue
            
            # 批次处理完成后进行垃圾回收
            gc.collect()
            
            # 让出控制权，避免阻塞
            await asyncio.sleep(0.01)
        
        logger.info(f"流式处理完成，处理文件数: {processed_files}")
    
    def _find_source_files(self, project_path: str) -> List[str]:
        """查找源代码文件（复用BatchProcessor的实现）"""
        processor = BatchProcessor()
        return processor._find_source_files(project_path)


class ProgressTracker:
    """进度跟踪器"""
    
    def __init__(self, total_items: int):
        """初始化进度跟踪器
        
        Args:
            total_items: 总项目数
        """
        self.total_items = total_items
        self.processed_items = 0
        self.start_time = time.time()
        self.last_update_time = self.start_time
    
    def update(self, processed_items: int):
        """更新进度
        
        Args:
            processed_items: 已处理项目数
        """
        self.processed_items = processed_items
        current_time = time.time()
        
        # 每秒最多更新一次日志
        if current_time - self.last_update_time >= 1.0:
            self._log_progress()
            self.last_update_time = current_time
    
    def _log_progress(self):
        """记录进度日志"""
        if self.total_items == 0:
            return
        
        progress_percent = (self.processed_items / self.total_items) * 100
        elapsed_time = time.time() - self.start_time
        
        if self.processed_items > 0:
            avg_time_per_item = elapsed_time / self.processed_items
            remaining_items = self.total_items - self.processed_items
            estimated_remaining_time = remaining_items * avg_time_per_item
            
            logger.info(
                f"进度: {self.processed_items}/{self.total_items} "
                f"({progress_percent:.1f}%), "
                f"预计剩余时间: {estimated_remaining_time:.1f}秒"
            )
        else:
            logger.info(f"进度: {self.processed_items}/{self.total_items} ({progress_percent:.1f}%)")
    
    def complete(self):
        """标记完成"""
        total_time = time.time() - self.start_time
        logger.info(f"处理完成，总耗时: {total_time:.2f}秒，平均每项: {total_time/max(1, self.processed_items):.3f}秒")