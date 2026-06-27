"""
性能管理器

监控系统性能，提供优化建议和自动调优功能。
"""

import asyncio
import gc
import logging
import time
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import psutil
import threading

from ..exceptions import PerformanceError


logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """性能指标"""
    timestamp: datetime = field(default_factory=datetime.now)
    cpu_percent: float = 0.0
    memory_mb: float = 0.0
    memory_percent: float = 0.0
    disk_io_read_mb: float = 0.0
    disk_io_write_mb: float = 0.0
    network_sent_mb: float = 0.0
    network_recv_mb: float = 0.0
    active_threads: int = 0
    gc_collections: Dict[int, int] = field(default_factory=dict)


@dataclass
class PerformanceThresholds:
    """性能阈值配置"""
    cpu_warning: float = 80.0  # CPU使用率警告阈值
    cpu_critical: float = 95.0  # CPU使用率临界阈值
    memory_warning: float = 80.0  # 内存使用率警告阈值
    memory_critical: float = 95.0  # 内存使用率临界阈值
    response_time_warning: float = 5.0  # 响应时间警告阈值（秒）
    response_time_critical: float = 10.0  # 响应时间临界阈值（秒）


@dataclass
class OptimizationSuggestion:
    """优化建议"""
    category: str  # 类别：memory, cpu, io, cache等
    priority: str  # 优先级：low, medium, high, critical
    title: str  # 建议标题
    description: str  # 详细描述
    action: Optional[Callable] = None  # 可执行的优化动作


class PerformanceManager:
    """性能管理器
    
    监控系统性能，提供优化建议和自动调优功能。
    """
    
    def __init__(self, 
                 thresholds: Optional[PerformanceThresholds] = None,
                 monitoring_interval: float = 5.0):
        """初始化性能管理器
        
        Args:
            thresholds: 性能阈值配置
            monitoring_interval: 监控间隔（秒）
        """
        self.thresholds = thresholds or PerformanceThresholds()
        self.monitoring_interval = monitoring_interval
        
        self._metrics_history: List[PerformanceMetrics] = []
        self._max_history_size = 1000  # 最大历史记录数
        self._monitoring_active = False
        self._monitoring_thread: Optional[threading.Thread] = None
        
        self._performance_callbacks: List[Callable[[PerformanceMetrics], None]] = []
        self._alert_callbacks: List[Callable[[str, PerformanceMetrics], None]] = []
        
        # 性能统计
        self._stats = {
            "total_alerts": 0,
            "cpu_alerts": 0,
            "memory_alerts": 0,
            "response_time_alerts": 0,
            "optimizations_applied": 0
        }
        
        logger.info("性能管理器初始化完成")
    
    def start_monitoring(self):
        """开始性能监控"""
        if self._monitoring_active:
            logger.warning("性能监控已在运行")
            return
        
        self._monitoring_active = True
        self._monitoring_thread = threading.Thread(
            target=self._monitoring_loop,
            daemon=True
        )
        self._monitoring_thread.start()
        
        logger.info("性能监控已启动")
    
    def stop_monitoring(self):
        """停止性能监控"""
        if not self._monitoring_active:
            return
        
        self._monitoring_active = False
        if self._monitoring_thread:
            self._monitoring_thread.join(timeout=5.0)
        
        logger.info("性能监控已停止")
    
    def _monitoring_loop(self):
        """监控循环"""
        while self._monitoring_active:
            try:
                # 收集性能指标
                metrics = self._collect_metrics()
                
                # 添加到历史记录
                self._add_metrics_to_history(metrics)
                
                # 检查阈值并发送警报
                self._check_thresholds(metrics)
                
                # 调用性能回调
                for callback in self._performance_callbacks:
                    try:
                        callback(metrics)
                    except Exception as e:
                        logger.error(f"性能回调执行失败: {e}")
                
                time.sleep(self.monitoring_interval)
                
            except Exception as e:
                logger.error(f"性能监控循环出错: {e}")
                time.sleep(self.monitoring_interval)
    
    def _collect_metrics(self) -> PerformanceMetrics:
        """收集性能指标"""
        process = psutil.Process()
        
        # CPU和内存指标
        cpu_percent = process.cpu_percent()
        memory_info = process.memory_info()
        memory_mb = memory_info.rss / 1024 / 1024
        memory_percent = process.memory_percent()
        
        # IO指标
        try:
            io_counters = process.io_counters()
            disk_io_read_mb = io_counters.read_bytes / 1024 / 1024
            disk_io_write_mb = io_counters.write_bytes / 1024 / 1024
        except (AttributeError, psutil.AccessDenied):
            disk_io_read_mb = 0.0
            disk_io_write_mb = 0.0
        
        # 网络指标（系统级别）
        try:
            net_io = psutil.net_io_counters()
            network_sent_mb = net_io.bytes_sent / 1024 / 1024
            network_recv_mb = net_io.bytes_recv / 1024 / 1024
        except (AttributeError, psutil.AccessDenied):
            network_sent_mb = 0.0
            network_recv_mb = 0.0
        
        # 线程数
        active_threads = process.num_threads()
        
        # 垃圾回收统计
        gc_collections = {i: gc.get_count()[i] for i in range(3)}
        
        return PerformanceMetrics(
            cpu_percent=cpu_percent,
            memory_mb=memory_mb,
            memory_percent=memory_percent,
            disk_io_read_mb=disk_io_read_mb,
            disk_io_write_mb=disk_io_write_mb,
            network_sent_mb=network_sent_mb,
            network_recv_mb=network_recv_mb,
            active_threads=active_threads,
            gc_collections=gc_collections
        )
    
    def _add_metrics_to_history(self, metrics: PerformanceMetrics):
        """添加指标到历史记录"""
        self._metrics_history.append(metrics)
        
        # 限制历史记录大小
        if len(self._metrics_history) > self._max_history_size:
            self._metrics_history = self._metrics_history[-self._max_history_size:]
    
    def _check_thresholds(self, metrics: PerformanceMetrics):
        """检查性能阈值"""
        alerts = []
        
        # CPU阈值检查
        if metrics.cpu_percent >= self.thresholds.cpu_critical:
            alerts.append(("CPU_CRITICAL", f"CPU使用率达到临界值: {metrics.cpu_percent:.1f}%"))
            self._stats["cpu_alerts"] += 1
        elif metrics.cpu_percent >= self.thresholds.cpu_warning:
            alerts.append(("CPU_WARNING", f"CPU使用率较高: {metrics.cpu_percent:.1f}%"))
            self._stats["cpu_alerts"] += 1
        
        # 内存阈值检查
        if metrics.memory_percent >= self.thresholds.memory_critical:
            alerts.append(("MEMORY_CRITICAL", f"内存使用率达到临界值: {metrics.memory_percent:.1f}%"))
            self._stats["memory_alerts"] += 1
        elif metrics.memory_percent >= self.thresholds.memory_warning:
            alerts.append(("MEMORY_WARNING", f"内存使用率较高: {metrics.memory_percent:.1f}%"))
            self._stats["memory_alerts"] += 1
        
        # 发送警报
        for alert_type, message in alerts:
            self._stats["total_alerts"] += 1
            logger.warning(f"性能警报 [{alert_type}]: {message}")
            
            for callback in self._alert_callbacks:
                try:
                    callback(alert_type, metrics)
                except Exception as e:
                    logger.error(f"警报回调执行失败: {e}")
    
    def get_current_metrics(self) -> Optional[PerformanceMetrics]:
        """获取当前性能指标
        
        Returns:
            当前性能指标，如果监控未启动则返回None
        """
        if not self._monitoring_active:
            return self._collect_metrics()
        
        if self._metrics_history:
            return self._metrics_history[-1]
        
        return None
    
    def get_metrics_history(self, 
                           duration_minutes: Optional[int] = None) -> List[PerformanceMetrics]:
        """获取性能指标历史
        
        Args:
            duration_minutes: 获取最近多少分钟的数据，None表示全部
            
        Returns:
            性能指标历史列表
        """
        if duration_minutes is None:
            return self._metrics_history.copy()
        
        cutoff_time = datetime.now() - timedelta(minutes=duration_minutes)
        return [
            metrics for metrics in self._metrics_history
            if metrics.timestamp >= cutoff_time
        ]
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """获取性能摘要
        
        Returns:
            性能摘要信息
        """
        if not self._metrics_history:
            return {"status": "no_data", "message": "暂无性能数据"}
        
        recent_metrics = self.get_metrics_history(duration_minutes=10)
        if not recent_metrics:
            return {"status": "no_recent_data", "message": "暂无最近的性能数据"}
        
        # 计算平均值
        avg_cpu = sum(m.cpu_percent for m in recent_metrics) / len(recent_metrics)
        avg_memory = sum(m.memory_mb for m in recent_metrics) / len(recent_metrics)
        avg_memory_percent = sum(m.memory_percent for m in recent_metrics) / len(recent_metrics)
        
        # 计算最大值
        max_cpu = max(m.cpu_percent for m in recent_metrics)
        max_memory = max(m.memory_mb for m in recent_metrics)
        max_memory_percent = max(m.memory_percent for m in recent_metrics)
        
        # 判断整体状态
        status = "good"
        if (max_cpu >= self.thresholds.cpu_critical or 
            max_memory_percent >= self.thresholds.memory_critical):
            status = "critical"
        elif (max_cpu >= self.thresholds.cpu_warning or 
              max_memory_percent >= self.thresholds.memory_warning):
            status = "warning"
        
        return {
            "status": status,
            "summary": {
                "avg_cpu_percent": round(avg_cpu, 1),
                "max_cpu_percent": round(max_cpu, 1),
                "avg_memory_mb": round(avg_memory, 1),
                "max_memory_mb": round(max_memory, 1),
                "avg_memory_percent": round(avg_memory_percent, 1),
                "max_memory_percent": round(max_memory_percent, 1),
                "sample_count": len(recent_metrics),
                "time_range_minutes": 10
            },
            "stats": self._stats.copy()
        }
    
    def get_optimization_suggestions(self) -> List[OptimizationSuggestion]:
        """获取优化建议
        
        Returns:
            优化建议列表
        """
        suggestions = []
        
        if not self._metrics_history:
            return suggestions
        
        recent_metrics = self.get_metrics_history(duration_minutes=5)
        if not recent_metrics:
            return suggestions
        
        # 分析CPU使用情况
        avg_cpu = sum(m.cpu_percent for m in recent_metrics) / len(recent_metrics)
        max_cpu = max(m.cpu_percent for m in recent_metrics)
        
        if max_cpu >= self.thresholds.cpu_critical:
            suggestions.append(OptimizationSuggestion(
                category="cpu",
                priority="critical",
                title="CPU使用率过高",
                description=f"CPU使用率达到 {max_cpu:.1f}%，建议减少并发处理数量或优化算法复杂度",
                action=self._optimize_cpu_usage
            ))
        elif avg_cpu >= self.thresholds.cpu_warning:
            suggestions.append(OptimizationSuggestion(
                category="cpu",
                priority="medium",
                title="CPU使用率较高",
                description=f"平均CPU使用率为 {avg_cpu:.1f}%，建议优化计算密集型操作",
                action=self._optimize_cpu_usage
            ))
        
        # 分析内存使用情况
        avg_memory_percent = sum(m.memory_percent for m in recent_metrics) / len(recent_metrics)
        max_memory_percent = max(m.memory_percent for m in recent_metrics)
        
        if max_memory_percent >= self.thresholds.memory_critical:
            suggestions.append(OptimizationSuggestion(
                category="memory",
                priority="critical",
                title="内存使用率过高",
                description=f"内存使用率达到 {max_memory_percent:.1f}%，建议立即释放内存或增加内存限制",
                action=self._optimize_memory_usage
            ))
        elif avg_memory_percent >= self.thresholds.memory_warning:
            suggestions.append(OptimizationSuggestion(
                category="memory",
                priority="medium",
                title="内存使用率较高",
                description=f"平均内存使用率为 {avg_memory_percent:.1f}%，建议优化内存使用",
                action=self._optimize_memory_usage
            ))
        
        # 分析垃圾回收情况
        if recent_metrics:
            latest_gc = recent_metrics[-1].gc_collections
            if len(self._metrics_history) > 1:
                prev_gc = self._metrics_history[-2].gc_collections
                gc_diff = sum(latest_gc.values()) - sum(prev_gc.values())
                
                if gc_diff > 10:  # 垃圾回收过于频繁
                    suggestions.append(OptimizationSuggestion(
                        category="memory",
                        priority="medium",
                        title="垃圾回收过于频繁",
                        description=f"检测到频繁的垃圾回收活动，建议优化对象创建和内存管理",
                        action=self._optimize_gc
                    ))
        
        return suggestions
    
    def apply_optimization(self, suggestion: OptimizationSuggestion) -> bool:
        """应用优化建议
        
        Args:
            suggestion: 优化建议
            
        Returns:
            是否成功应用
        """
        if not suggestion.action:
            logger.warning(f"优化建议 '{suggestion.title}' 没有可执行的动作")
            return False
        
        try:
            logger.info(f"应用优化: {suggestion.title}")
            suggestion.action()
            self._stats["optimizations_applied"] += 1
            return True
        except Exception as e:
            logger.error(f"应用优化失败: {e}")
            return False
    
    def _optimize_cpu_usage(self):
        """优化CPU使用"""
        # 这里可以实现具体的CPU优化策略
        # 例如：减少并发数量、优化算法等
        logger.info("执行CPU使用优化")
        
        # 示例：触发垃圾回收以释放CPU资源
        gc.collect()
    
    def _optimize_memory_usage(self):
        """优化内存使用"""
        logger.info("执行内存使用优化")
        
        # 强制垃圾回收
        gc.collect()
        
        # 可以在这里添加更多内存优化策略
        # 例如：清理缓存、释放不必要的对象等
    
    def _optimize_gc(self):
        """优化垃圾回收"""
        logger.info("执行垃圾回收优化")
        
        # 调整垃圾回收阈值
        gc.set_threshold(700, 10, 10)  # 减少垃圾回收频率
        
        # 手动触发一次完整的垃圾回收
        gc.collect()
    
    def add_performance_callback(self, callback: Callable[[PerformanceMetrics], None]):
        """添加性能监控回调
        
        Args:
            callback: 回调函数，接收性能指标参数
        """
        self._performance_callbacks.append(callback)
    
    def add_alert_callback(self, callback: Callable[[str, PerformanceMetrics], None]):
        """添加警报回调
        
        Args:
            callback: 回调函数，接收警报类型和性能指标参数
        """
        self._alert_callbacks.append(callback)
    
    def measure_execution_time(self, operation_name: str):
        """测量执行时间的装饰器工厂
        
        Args:
            operation_name: 操作名称
            
        Returns:
            装饰器函数
        """
        def decorator(func):
            def wrapper(*args, **kwargs):
                start_time = time.time()
                try:
                    result = func(*args, **kwargs)
                    execution_time = time.time() - start_time
                    
                    # 检查响应时间阈值
                    if execution_time >= self.thresholds.response_time_critical:
                        logger.warning(f"操作 '{operation_name}' 执行时间过长: {execution_time:.2f}秒")
                        self._stats["response_time_alerts"] += 1
                    elif execution_time >= self.thresholds.response_time_warning:
                        logger.info(f"操作 '{operation_name}' 执行时间较长: {execution_time:.2f}秒")
                        self._stats["response_time_alerts"] += 1
                    
                    return result
                except Exception as e:
                    execution_time = time.time() - start_time
                    logger.error(f"操作 '{operation_name}' 执行失败，耗时: {execution_time:.2f}秒")
                    raise
            
            return wrapper
        return decorator
    
    def get_stats(self) -> Dict[str, int]:
        """获取统计信息
        
        Returns:
            统计信息字典
        """
        return self._stats.copy()
    
    def reset_stats(self):
        """重置统计信息"""
        self._stats = {
            "total_alerts": 0,
            "cpu_alerts": 0,
            "memory_alerts": 0,
            "response_time_alerts": 0,
            "optimizations_applied": 0
        }
        logger.info("性能统计信息已重置")


class AsyncPerformanceManager:
    """异步性能管理器
    
    提供异步的性能监控和优化功能。
    """
    
    def __init__(self, performance_manager: PerformanceManager):
        """初始化异步性能管理器
        
        Args:
            performance_manager: 性能管理器实例
        """
        self.performance_manager = performance_manager
    
    async def monitor_async_operation(self, 
                                    operation_name: str,
                                    operation_coro):
        """监控异步操作的性能
        
        Args:
            operation_name: 操作名称
            operation_coro: 异步操作协程
            
        Returns:
            操作结果
        """
        start_time = time.time()
        start_metrics = self.performance_manager._collect_metrics()
        
        try:
            result = await operation_coro
            
            end_time = time.time()
            end_metrics = self.performance_manager._collect_metrics()
            execution_time = end_time - start_time
            
            # 记录性能信息
            logger.info(f"异步操作 '{operation_name}' 完成，耗时: {execution_time:.2f}秒")
            
            # 分析资源使用变化
            memory_delta = end_metrics.memory_mb - start_metrics.memory_mb
            if memory_delta > 100:  # 内存增长超过100MB
                logger.warning(f"操作 '{operation_name}' 导致内存增长: {memory_delta:.1f}MB")
            
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"异步操作 '{operation_name}' 失败，耗时: {execution_time:.2f}秒")
            raise
    
    async def auto_optimize_periodically(self, interval_minutes: int = 30):
        """定期自动优化
        
        Args:
            interval_minutes: 优化间隔（分钟）
        """
        while True:
            try:
                await asyncio.sleep(interval_minutes * 60)
                
                suggestions = self.performance_manager.get_optimization_suggestions()
                high_priority_suggestions = [
                    s for s in suggestions 
                    if s.priority in ["high", "critical"]
                ]
                
                if high_priority_suggestions:
                    logger.info(f"发现 {len(high_priority_suggestions)} 个高优先级优化建议")
                    
                    for suggestion in high_priority_suggestions:
                        if suggestion.priority == "critical":
                            # 自动应用临界优化
                            self.performance_manager.apply_optimization(suggestion)
                        else:
                            # 记录高优先级建议
                            logger.info(f"高优先级优化建议: {suggestion.title}")
                
            except Exception as e:
                logger.error(f"自动优化过程出错: {e}")
                await asyncio.sleep(60)  # 出错后等待1分钟再继续