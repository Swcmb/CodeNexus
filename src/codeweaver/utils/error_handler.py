"""
全局错误处理器

提供统一的错误处理、监控和恢复机制。
"""

import traceback
import sys
import functools
import asyncio
from typing import Any, Callable, Dict, List, Optional, Type, Union
from datetime import datetime
import logging
import json
from pathlib import Path

from ..exceptions import (
    codenexusError, ParseError, GraphBuildError, DatabaseError,
    AIServiceError, ConfigurationError, ValidationError,
    ServiceUnavailableError, DocumentationError, QAServiceError
)
from .logger import system_logger


class ErrorContext:
    """错误上下文信息"""
    
    def __init__(
        self,
        operation: str,
        component: str,
        user_id: Optional[str] = None,
        request_id: Optional[str] = None,
        additional_data: Optional[Dict[str, Any]] = None
    ):
        self.operation = operation
        self.component = component
        self.user_id = user_id
        self.request_id = request_id
        self.additional_data = additional_data or {}
        self.timestamp = datetime.utcnow()


class ErrorRecord:
    """错误记录"""
    
    def __init__(
        self,
        exception: Exception,
        context: ErrorContext,
        stack_trace: str,
        severity: str = "ERROR"
    ):
        self.exception = exception
        self.context = context
        self.stack_trace = stack_trace
        self.severity = severity
        self.timestamp = datetime.utcnow()
        self.error_id = f"{context.component}_{int(self.timestamp.timestamp())}"
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "error_id": self.error_id,
            "timestamp": self.timestamp.isoformat(),
            "severity": self.severity,
            "exception_type": type(self.exception).__name__,
            "exception_message": str(self.exception),
            "operation": self.context.operation,
            "component": self.context.component,
            "user_id": self.context.user_id,
            "request_id": self.context.request_id,
            "additional_data": self.context.additional_data,
            "stack_trace": self.stack_trace
        }


class ErrorMonitor:
    """错误监控器"""
    
    def __init__(self, log_file: Optional[str] = None):
        self.logger = system_logger
        self.error_records: List[ErrorRecord] = []
        self.error_counts: Dict[str, int] = {}
        self.log_file = log_file
        
        # 错误阈值配置
        self.error_thresholds = {
            "ParseError": 10,
            "DatabaseError": 5,
            "AIServiceError": 3,
            "ServiceUnavailableError": 2
        }
    
    def record_error(
        self,
        exception: Exception,
        context: ErrorContext,
        severity: str = "ERROR"
    ) -> str:
        """记录错误"""
        stack_trace = traceback.format_exc()
        error_record = ErrorRecord(exception, context, stack_trace, severity)
        
        # 添加到记录列表
        self.error_records.append(error_record)
        
        # 更新错误计数
        error_type = type(exception).__name__
        self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1
        
        # 记录日志
        self._log_error(error_record)
        
        # 写入文件
        if self.log_file:
            self._write_to_file(error_record)
        
        # 检查是否需要告警
        self._check_alert_threshold(error_type)
        
        return error_record.error_id
    
    def _log_error(self, error_record: ErrorRecord):
        """记录错误日志"""
        log_message = (
            f"错误ID: {error_record.error_id} | "
            f"组件: {error_record.context.component} | "
            f"操作: {error_record.context.operation} | "
            f"异常: {error_record.exception}"
        )
        
        if error_record.severity == "CRITICAL":
            self.logger.critical(log_message, exc_info=True)
        elif error_record.severity == "ERROR":
            self.logger.error(log_message, exc_info=True)
        elif error_record.severity == "WARNING":
            self.logger.warning(log_message)
        else:
            self.logger.info(log_message)
    
    def _write_to_file(self, error_record: ErrorRecord):
        """写入错误日志文件"""
        try:
            log_path = Path(self.log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(log_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps(error_record.to_dict(), ensure_ascii=False) + '\n')
        except Exception as e:
            self.logger.error(f"写入错误日志文件失败: {e}")
    
    def _check_alert_threshold(self, error_type: str):
        """检查告警阈值"""
        threshold = self.error_thresholds.get(error_type, 20)
        count = self.error_counts.get(error_type, 0)
        
        if count >= threshold:
            self.logger.critical(
                f"错误类型 {error_type} 达到告警阈值: {count}/{threshold}"
            )
            # 这里可以集成告警系统，如发送邮件、短信等
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """获取错误统计信息"""
        return {
            "total_errors": len(self.error_records),
            "error_counts": self.error_counts.copy(),
            "recent_errors": [
                record.to_dict() for record in self.error_records[-10:]
            ]
        }
    
    def clear_old_records(self, days: int = 7):
        """清理旧的错误记录"""
        cutoff_time = datetime.utcnow().timestamp() - (days * 24 * 3600)
        self.error_records = [
            record for record in self.error_records
            if record.timestamp.timestamp() > cutoff_time
        ]


# 全局错误监控器实例
error_monitor = ErrorMonitor(log_file="logs/errors.jsonl")


class GlobalErrorHandler:
    """全局错误处理器"""
    
    def __init__(self, monitor: ErrorMonitor = None):
        self.monitor = monitor or error_monitor
        self.recovery_strategies: Dict[Type[Exception], Callable] = {}
        self.fallback_handlers: Dict[str, Callable] = {}
    
    def register_recovery_strategy(
        self,
        exception_type: Type[Exception],
        strategy: Callable
    ):
        """注册错误恢复策略"""
        self.recovery_strategies[exception_type] = strategy
    
    def register_fallback_handler(
        self,
        component: str,
        handler: Callable
    ):
        """注册降级处理器"""
        self.fallback_handlers[component] = handler
    
    def handle_error(
        self,
        exception: Exception,
        context: ErrorContext,
        attempt_recovery: bool = True
    ) -> Any:
        """处理错误"""
        # 记录错误
        error_id = self.monitor.record_error(exception, context)
        
        # 尝试恢复
        if attempt_recovery:
            recovery_result = self._attempt_recovery(exception, context)
            if recovery_result is not None:
                self.monitor.logger.info(f"错误恢复成功: {error_id}")
                return recovery_result
        
        # 尝试降级处理
        fallback_result = self._attempt_fallback(context)
        if fallback_result is not None:
            self.monitor.logger.info(f"降级处理成功: {error_id}")
            return fallback_result
        
        # 重新抛出异常
        raise exception
    
    def _attempt_recovery(
        self,
        exception: Exception,
        context: ErrorContext
    ) -> Any:
        """尝试错误恢复"""
        exception_type = type(exception)
        
        # 查找匹配的恢复策略
        for exc_type, strategy in self.recovery_strategies.items():
            if issubclass(exception_type, exc_type):
                try:
                    return strategy(exception, context)
                except Exception as recovery_error:
                    self.monitor.logger.warning(
                        f"恢复策略执行失败: {recovery_error}"
                    )
        
        return None
    
    def _attempt_fallback(self, context: ErrorContext) -> Any:
        """尝试降级处理"""
        handler = self.fallback_handlers.get(context.component)
        if handler:
            try:
                return handler(context)
            except Exception as fallback_error:
                self.monitor.logger.warning(
                    f"降级处理失败: {fallback_error}"
                )
        
        return None


# 全局错误处理器实例
global_error_handler = GlobalErrorHandler()


def error_handler(
    component: str,
    operation: str = None,
    reraise: bool = True,
    fallback_value: Any = None
):
    """错误处理装饰器"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            context = ErrorContext(
                operation=operation or func.__name__,
                component=component
            )
            
            try:
                return func(*args, **kwargs)
            except Exception as e:
                try:
                    result = global_error_handler.handle_error(
                        e, context, attempt_recovery=True
                    )
                    return result
                except Exception:
                    if reraise:
                        raise
                    return fallback_value
        
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            context = ErrorContext(
                operation=operation or func.__name__,
                component=component
            )
            
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                try:
                    result = global_error_handler.handle_error(
                        e, context, attempt_recovery=True
                    )
                    return result
                except Exception:
                    if reraise:
                        raise
                    return fallback_value
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def setup_default_recovery_strategies():
    """设置默认的错误恢复策略"""
    
    def database_recovery(exception: DatabaseError, context: ErrorContext):
        """数据库错误恢复策略"""
        # 尝试重新连接数据库
        system_logger.info("尝试重新连接数据库...")
        # 这里应该实现具体的数据库重连逻辑
        return None
    
    def ai_service_recovery(exception: AIServiceError, context: ErrorContext):
        """AI服务错误恢复策略"""
        # 切换到备用AI服务或降级到规则引擎
        system_logger.info("AI服务不可用，切换到备用方案...")
        return None
    
    def parse_error_recovery(exception: ParseError, context: ErrorContext):
        """解析错误恢复策略"""
        # 尝试使用备用解析器或跳过有问题的文件
        system_logger.info("解析失败，尝试备用解析方案...")
        return None
    
    # 注册恢复策略
    global_error_handler.register_recovery_strategy(DatabaseError, database_recovery)
    global_error_handler.register_recovery_strategy(AIServiceError, ai_service_recovery)
    global_error_handler.register_recovery_strategy(ParseError, parse_error_recovery)


def setup_default_fallback_handlers():
    """设置默认的降级处理器"""
    
    def parser_fallback(context: ErrorContext):
        """解析器降级处理"""
        return {"status": "partial", "message": "部分解析失败，返回可用结果"}
    
    def ai_fallback(context: ErrorContext):
        """AI服务降级处理"""
        return {"status": "fallback", "message": "AI服务不可用，使用基础功能"}
    
    def documentation_fallback(context: ErrorContext):
        """文档生成降级处理"""
        return {"status": "basic", "content": "基础文档模板"}
    
    # 注册降级处理器
    global_error_handler.register_fallback_handler("parser", parser_fallback)
    global_error_handler.register_fallback_handler("ai", ai_fallback)
    global_error_handler.register_fallback_handler("documentation", documentation_fallback)


# 初始化默认策略
setup_default_recovery_strategies()
setup_default_fallback_handlers()


class CircuitBreaker:
    """熔断器"""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: Type[Exception] = Exception
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
    
    def __call__(self, func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if self.state == "OPEN":
                if self._should_attempt_reset():
                    self.state = "HALF_OPEN"
                else:
                    raise ServiceUnavailableError(
                        f"服务熔断中，请在 {self.recovery_timeout} 秒后重试"
                    )
            
            try:
                result = func(*args, **kwargs)
                self._on_success()
                return result
            except self.expected_exception as e:
                self._on_failure()
                raise e
        
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            if self.state == "OPEN":
                if self._should_attempt_reset():
                    self.state = "HALF_OPEN"
                else:
                    raise ServiceUnavailableError(
                        f"服务熔断中，请在 {self.recovery_timeout} 秒后重试"
                    )
            
            try:
                result = await func(*args, **kwargs)
                self._on_success()
                return result
            except self.expected_exception as e:
                self._on_failure()
                raise e
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return wrapper
    
    def _should_attempt_reset(self) -> bool:
        """检查是否应该尝试重置"""
        if self.last_failure_time is None:
            return True
        
        return (datetime.utcnow().timestamp() - self.last_failure_time) > self.recovery_timeout
    
    def _on_success(self):
        """成功时的处理"""
        self.failure_count = 0
        self.state = "CLOSED"
    
    def _on_failure(self):
        """失败时的处理"""
        self.failure_count += 1
        self.last_failure_time = datetime.utcnow().timestamp()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"


def with_circuit_breaker(
    failure_threshold: int = 5,
    recovery_timeout: int = 60,
    expected_exception: Type[Exception] = Exception
):
    """熔断器装饰器"""
    def decorator(func: Callable) -> Callable:
        circuit_breaker = CircuitBreaker(
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout,
            expected_exception=expected_exception
        )
        return circuit_breaker(func)
    
    return decorator