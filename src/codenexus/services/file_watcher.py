"""
文件变更监控服务

实现文件系统监控和变更检测，支持增量解析触发机制。
"""

import asyncio
import os
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set, Callable, Any
from threading import Thread, Event
import hashlib

from ..utils.logger import setup_logger
from ..interfaces import CodeParserInterface
from ..models.core import CodeElement, Relationship


logger = setup_logger(__name__)


class ChangeType(Enum):
    """文件变更类型"""
    CREATED = "created"
    MODIFIED = "modified"
    DELETED = "deleted"
    MOVED = "moved"


@dataclass
class FileChange:
    """文件变更事件"""
    path: str
    change_type: ChangeType
    timestamp: float
    old_path: Optional[str] = None  # 用于移动事件
    file_hash: Optional[str] = None  # 文件内容哈希


@dataclass
class WatchConfig:
    """监控配置"""
    watch_paths: List[str]
    ignore_patterns: List[str] = None
    supported_extensions: List[str] = None
    poll_interval: float = 1.0  # 轮询间隔（秒）
    debounce_delay: float = 0.5  # 防抖延迟（秒）
    
    def __post_init__(self):
        if self.ignore_patterns is None:
            self.ignore_patterns = [
                "*.pyc", "*.pyo", "__pycache__", ".git", ".svn", 
                "node_modules", ".pytest_cache", ".hypothesis",
                "*.log", "*.tmp", ".DS_Store"
            ]
        if self.supported_extensions is None:
            self.supported_extensions = [
                ".py", ".java", ".js", ".ts", ".cs", ".cpp", ".c", ".h"
            ]


class FileWatcher:
    """文件监控器
    
    使用轮询方式监控文件变更，支持跨平台。
    在生产环境中可以替换为更高效的平台特定实现。
    """
    
    def __init__(self, config: WatchConfig):
        self.config = config
        self._file_states: Dict[str, Dict[str, Any]] = {}  # 文件状态缓存
        self._is_running = False
        self._stop_event = Event()
        self._watch_thread: Optional[Thread] = None
        self._change_handlers: List[Callable[[List[FileChange]], None]] = []
        self._pending_changes: Dict[str, FileChange] = {}  # 防抖缓存
        self._last_scan_time = 0.0
        
    def add_change_handler(self, handler: Callable[[List[FileChange]], None]) -> None:
        """添加变更处理器"""
        self._change_handlers.append(handler)
        logger.info(f"添加文件变更处理器: {handler.__name__}")
    
    def remove_change_handler(self, handler: Callable[[List[FileChange]], None]) -> None:
        """移除变更处理器"""
        if handler in self._change_handlers:
            self._change_handlers.remove(handler)
            logger.info(f"移除文件变更处理器: {handler.__name__}")
    
    def start(self) -> None:
        """开始监控"""
        if self._is_running:
            logger.warning("文件监控器已在运行")
            return
        
        self._is_running = True
        self._stop_event.clear()
        
        # 初始化文件状态
        self._initialize_file_states()
        
        # 启动监控线程
        self._watch_thread = Thread(target=self._watch_loop, daemon=True)
        self._watch_thread.start()
        
        logger.info(f"文件监控器已启动，监控路径: {self.config.watch_paths}")
    
    def stop(self) -> None:
        """停止监控"""
        if not self._is_running:
            return
        
        self._is_running = False
        self._stop_event.set()
        
        if self._watch_thread and self._watch_thread.is_alive():
            self._watch_thread.join(timeout=5.0)
        
        logger.info("文件监控器已停止")
    
    def _initialize_file_states(self) -> None:
        """初始化文件状态缓存"""
        logger.info("初始化文件状态缓存...")
        
        for watch_path in self.config.watch_paths:
            if not os.path.exists(watch_path):
                logger.warning(f"监控路径不存在: {watch_path}")
                continue
            
            for file_path in self._scan_directory(watch_path):
                try:
                    stat = os.stat(file_path)
                    file_hash = self._calculate_file_hash(file_path)
                    
                    self._file_states[file_path] = {
                        'mtime': stat.st_mtime,
                        'size': stat.st_size,
                        'hash': file_hash
                    }
                except (OSError, IOError) as e:
                    logger.warning(f"无法获取文件状态 {file_path}: {e}")
        
        logger.info(f"初始化完成，监控 {len(self._file_states)} 个文件")
    
    def _scan_directory(self, directory: str) -> List[str]:
        """扫描目录，返回符合条件的文件列表"""
        files = []
        
        try:
            for root, dirs, filenames in os.walk(directory):
                # 过滤忽略的目录
                dirs[:] = [d for d in dirs if not self._should_ignore(d)]
                
                for filename in filenames:
                    file_path = os.path.join(root, filename)
                    
                    if self._should_monitor_file(file_path):
                        files.append(file_path)
        
        except (OSError, IOError) as e:
            logger.error(f"扫描目录失败 {directory}: {e}")
        
        return files
    
    def _should_monitor_file(self, file_path: str) -> bool:
        """判断是否应该监控该文件"""
        # 检查文件扩展名
        if self.config.supported_extensions:
            ext = Path(file_path).suffix.lower()
            if ext not in self.config.supported_extensions:
                return False
        
        # 检查忽略模式
        if self._should_ignore(file_path):
            return False
        
        return True
    
    def _should_ignore(self, path: str) -> bool:
        """检查路径是否应该被忽略"""
        import fnmatch
        
        path_name = os.path.basename(path)
        
        for pattern in self.config.ignore_patterns:
            if fnmatch.fnmatch(path_name, pattern) or fnmatch.fnmatch(path, pattern):
                return True
        
        return False
    
    def _calculate_file_hash(self, file_path: str) -> str:
        """计算文件内容哈希"""
        try:
            with open(file_path, 'rb') as f:
                content = f.read()
                return hashlib.md5(content).hexdigest()
        except (OSError, IOError):
            return ""
    
    def _watch_loop(self) -> None:
        """监控循环"""
        logger.info("文件监控循环已启动")
        
        while not self._stop_event.is_set():
            try:
                changes = self._detect_changes()
                
                if changes:
                    # 应用防抖机制
                    self._apply_debounce(changes)
                
                # 处理防抖后的变更
                self._process_debounced_changes()
                
            except Exception as e:
                logger.error(f"文件监控循环出错: {e}")
            
            # 等待下次扫描
            self._stop_event.wait(self.config.poll_interval)
        
        logger.info("文件监控循环已退出")
    
    def _detect_changes(self) -> List[FileChange]:
        """检测文件变更"""
        changes = []
        current_files = set()
        
        # 扫描所有监控路径
        for watch_path in self.config.watch_paths:
            if os.path.exists(watch_path):
                current_files.update(self._scan_directory(watch_path))
        
        # 检测新增和修改的文件
        for file_path in current_files:
            try:
                stat = os.stat(file_path)
                file_hash = self._calculate_file_hash(file_path)
                
                if file_path not in self._file_states:
                    # 新文件
                    changes.append(FileChange(
                        path=file_path,
                        change_type=ChangeType.CREATED,
                        timestamp=time.time(),
                        file_hash=file_hash
                    ))
                    
                    self._file_states[file_path] = {
                        'mtime': stat.st_mtime,
                        'size': stat.st_size,
                        'hash': file_hash
                    }
                
                else:
                    # 检查是否修改
                    old_state = self._file_states[file_path]
                    
                    if (stat.st_mtime != old_state['mtime'] or 
                        stat.st_size != old_state['size'] or
                        file_hash != old_state['hash']):
                        
                        changes.append(FileChange(
                            path=file_path,
                            change_type=ChangeType.MODIFIED,
                            timestamp=time.time(),
                            file_hash=file_hash
                        ))
                        
                        self._file_states[file_path] = {
                            'mtime': stat.st_mtime,
                            'size': stat.st_size,
                            'hash': file_hash
                        }
            
            except (OSError, IOError) as e:
                logger.warning(f"检测文件变更失败 {file_path}: {e}")
        
        # 检测删除的文件
        deleted_files = set(self._file_states.keys()) - current_files
        for file_path in deleted_files:
            changes.append(FileChange(
                path=file_path,
                change_type=ChangeType.DELETED,
                timestamp=time.time()
            ))
            del self._file_states[file_path]
        
        return changes
    
    def _apply_debounce(self, changes: List[FileChange]) -> None:
        """应用防抖机制"""
        current_time = time.time()
        
        for change in changes:
            # 更新或添加到防抖缓存
            self._pending_changes[change.path] = change
    
    def _process_debounced_changes(self) -> None:
        """处理防抖后的变更"""
        if not self._pending_changes:
            return
        
        current_time = time.time()
        ready_changes = []
        
        # 检查哪些变更已经超过防抖延迟
        for path, change in list(self._pending_changes.items()):
            if current_time - change.timestamp >= self.config.debounce_delay:
                ready_changes.append(change)
                del self._pending_changes[path]
        
        if ready_changes:
            self._notify_handlers(ready_changes)
    
    def _notify_handlers(self, changes: List[FileChange]) -> None:
        """通知变更处理器"""
        if not changes:
            return
        
        logger.info(f"检测到 {len(changes)} 个文件变更")
        
        for change in changes:
            logger.debug(f"文件变更: {change.change_type.value} - {change.path}")
        
        # 通知所有处理器
        for handler in self._change_handlers:
            try:
                handler(changes)
            except Exception as e:
                logger.error(f"文件变更处理器出错 {handler.__name__}: {e}")


class IncrementalParseManager:
    """增量解析管理器
    
    管理文件变更触发的增量解析流程。
    """
    
    def __init__(self, parser: CodeParserInterface, file_watcher: FileWatcher):
        self.parser = parser
        self.file_watcher = file_watcher
        self._parse_handlers: List[Callable[[str, List[CodeElement], List[Relationship]], None]] = []
        
        # 注册文件变更处理器
        self.file_watcher.add_change_handler(self._handle_file_changes)
        
        logger.info("增量解析管理器已初始化")
    
    def add_parse_handler(self, handler: Callable[[str, List[CodeElement], List[Relationship]], None]) -> None:
        """添加解析结果处理器"""
        self._parse_handlers.append(handler)
        logger.info(f"添加解析结果处理器: {handler.__name__}")
    
    def remove_parse_handler(self, handler: Callable[[str, List[CodeElement], List[Relationship]], None]) -> None:
        """移除解析结果处理器"""
        if handler in self._parse_handlers:
            self._parse_handlers.remove(handler)
            logger.info(f"移除解析结果处理器: {handler.__name__}")
    
    def start(self) -> None:
        """启动增量解析管理器"""
        self.file_watcher.start()
        logger.info("增量解析管理器已启动")
    
    def stop(self) -> None:
        """停止增量解析管理器"""
        self.file_watcher.stop()
        logger.info("增量解析管理器已停止")
    
    def _handle_file_changes(self, changes: List[FileChange]) -> None:
        """处理文件变更事件"""
        logger.info(f"处理 {len(changes)} 个文件变更")
        
        # 按变更类型分组处理
        for change in changes:
            try:
                if change.change_type in [ChangeType.CREATED, ChangeType.MODIFIED]:
                    self._parse_changed_file(change)
                elif change.change_type == ChangeType.DELETED:
                    self._handle_deleted_file(change)
                elif change.change_type == ChangeType.MOVED:
                    self._handle_moved_file(change)
            
            except Exception as e:
                logger.error(f"处理文件变更失败 {change.path}: {e}")
    
    def _parse_changed_file(self, change: FileChange) -> None:
        """解析变更的文件"""
        logger.debug(f"解析文件: {change.path}")
        
        try:
            # 使用解析器解析文件
            result = self.parser.parse_file(change.path)
            
            if result and result.elements:
                logger.info(f"解析完成: {change.path}, 发现 {len(result.elements)} 个元素")
                
                # 通知解析结果处理器
                for handler in self._parse_handlers:
                    try:
                        handler(change.path, result.elements, result.relationships)
                    except Exception as e:
                        logger.error(f"解析结果处理器出错 {handler.__name__}: {e}")
            else:
                logger.warning(f"解析结果为空: {change.path}")
        
        except Exception as e:
            logger.error(f"解析文件失败 {change.path}: {e}")
    
    def _handle_deleted_file(self, change: FileChange) -> None:
        """处理删除的文件"""
        logger.debug(f"处理删除文件: {change.path}")
        
        # 通知处理器文件已删除
        for handler in self._parse_handlers:
            try:
                handler(change.path, [], [])  # 空的元素和关系列表表示删除
            except Exception as e:
                logger.error(f"删除文件处理器出错 {handler.__name__}: {e}")
    
    def _handle_moved_file(self, change: FileChange) -> None:
        """处理移动的文件"""
        logger.debug(f"处理移动文件: {change.old_path} -> {change.path}")
        
        # 先处理旧文件删除
        if change.old_path:
            old_change = FileChange(
                path=change.old_path,
                change_type=ChangeType.DELETED,
                timestamp=change.timestamp
            )
            self._handle_deleted_file(old_change)
        
        # 再处理新文件创建
        new_change = FileChange(
            path=change.path,
            change_type=ChangeType.CREATED,
            timestamp=change.timestamp,
            file_hash=change.file_hash
        )
        self._parse_changed_file(new_change)


def create_file_watcher(watch_paths: List[str], **kwargs) -> FileWatcher:
    """创建文件监控器的便捷函数"""
    config = WatchConfig(watch_paths=watch_paths, **kwargs)
    return FileWatcher(config)


def create_incremental_parse_manager(
    parser: CodeParserInterface, 
    watch_paths: List[str], 
    **kwargs
) -> IncrementalParseManager:
    """创建增量解析管理器的便捷函数"""
    file_watcher = create_file_watcher(watch_paths, **kwargs)
    return IncrementalParseManager(parser, file_watcher)