"""
错误处理器测试

测试全局错误处理、监控和恢复机制。
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

from src.codenexus.utils.error_handler import (
    ErrorContext, ErrorRecord, ErrorMonitor, GlobalErrorHandler,
    error_handler, CircuitBreaker
)
from src.codenexus.exceptions import ParseError, DatabaseError


class TestErrorContext:
    """错误上下文测试"""
    
    def test_error_context_creation(self):
        """测试错误上下文创建"""
        context = ErrorContext(
            operation="test_operation",
            component="test_component",
            user_id="user123",
            request_id="req456"
        )
        
        assert context.operation == "test_operation"
        assert context.component == "test_component"
        assert context.user_id == "user123"
        assert context.request_id == "req456"
        assert context.timestamp is not None


class TestErrorRecord:
    """错误记录测试"""
    
    def test_error_record_creation(self):
        """测试错误记录创建"""
        exception = ValueError("测试异常")
        context = ErrorContext("test_op", "test_comp")
        stack_trace = "测试堆栈跟踪"
        
        record = ErrorRecord(exception, context, stack_trace)
        
        assert record.exception == exception
        assert record.context == context
        assert record.stack_trace == stack_trace
        assert record.severity == "ERROR"
        assert record.error_id.startswith("test_comp_")
    
    def test_error_record_to_dict(self):
        """测试错误记录转换为字典"""
        exception = ValueError("测试异常")
        context = ErrorContext("test_op", "test_comp")
        record = ErrorRecord(exception, context, "stack_trace")
        
        data = record.to_dict()
        
        assert data["exception_type"] == "ValueError"
        assert data["exception_message"] == "测试异常"
        assert data["operation"] == "test_op"
        assert data["component"] == "test_comp"


class TestErrorMonitor:
    """错误监控器测试"""
    
    def test_error_monitor_creation(self):
        """测试错误监控器创建"""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            monitor = ErrorMonitor(log_file=f.name)
            
            assert monitor.log_file == f.name
            assert len(monitor.error_records) == 0
            assert len(monitor.error_counts) == 0
    
    def test_record_error(self):
        """测试记录错误"""
        monitor = ErrorMonitor()
        exception = ParseError("解析失败")
        context = ErrorContext("parse", "parser")
        
        error_id = monitor.record_error(exception, context)
        
        assert len(monitor.error_records) == 1
        assert monitor.error_counts["ParseError"] == 1
        assert error_id.startswith("parser_")
    
    def test_error_statistics(self):
        """测试错误统计"""
        monitor = ErrorMonitor()
        
        # 记录多个错误
        for i in range(3):
            exception = ParseError(f"错误{i}")
            context = ErrorContext("parse", "parser")
            monitor.record_error(exception, context)
        
        stats = monitor.get_error_statistics()
        
        assert stats["total_errors"] == 3
        assert stats["error_counts"]["ParseError"] == 3
        assert len(stats["recent_errors"]) == 3


class TestGlobalErrorHandler:
    """全局错误处理器测试"""
    
    def test_error_handler_creation(self):
        """测试错误处理器创建"""
        handler = GlobalErrorHandler()
        
        assert len(handler.recovery_strategies) == 0
        assert len(handler.fallback_handlers) == 0
    
    def test_register_recovery_strategy(self):
        """测试注册恢复策略"""
        handler = GlobalErrorHandler()
        
        def recovery_func(exc, ctx):
            return "recovered"
        
        handler.register_recovery_strategy(ParseError, recovery_func)
        
        assert ParseError in handler.recovery_strategies
        assert handler.recovery_strategies[ParseError] == recovery_func
    
    def test_register_fallback_handler(self):
        """测试注册降级处理器"""
        handler = GlobalErrorHandler()
        
        def fallback_func(ctx):
            return "fallback"
        
        handler.register_fallback_handler("parser", fallback_func)
        
        assert "parser" in handler.fallback_handlers
        assert handler.fallback_handlers["parser"] == fallback_func
    
    def test_handle_error_with_recovery(self):
        """测试带恢复的错误处理"""
        handler = GlobalErrorHandler()
        
        def recovery_func(exc, ctx):
            return "recovered"
        
        handler.register_recovery_strategy(ParseError, recovery_func)
        
        exception = ParseError("测试错误")
        context = ErrorContext("parse", "parser")
        
        result = handler.handle_error(exception, context)
        
        assert result == "recovered"
    
    def test_handle_error_with_fallback(self):
        """测试带降级的错误处理"""
        handler = GlobalErrorHandler()
        
        def fallback_func(ctx):
            return "fallback"
        
        handler.register_fallback_handler("parser", fallback_func)
        
        exception = ParseError("测试错误")
        context = ErrorContext("parse", "parser")
        
        result = handler.handle_error(exception, context)
        
        assert result == "fallback"
    
    def test_handle_error_reraise(self):
        """测试重新抛出异常"""
        handler = GlobalErrorHandler()
        exception = ParseError("测试错误")
        context = ErrorContext("parse", "parser")
        
        with pytest.raises(ParseError):
            handler.handle_error(exception, context)


class TestErrorHandlerDecorator:
    """错误处理装饰器测试"""
    
    def test_sync_error_handler_success(self):
        """测试同步错误处理装饰器成功情况"""
        @error_handler(component="test", operation="test_op")
        def test_func():
            return "success"
        
        result = test_func()
        assert result == "success"
    
    def test_sync_error_handler_with_fallback(self):
        """测试同步错误处理装饰器降级情况"""
        @error_handler(component="test", operation="test_op", reraise=False, fallback_value="fallback")
        def test_func():
            raise ValueError("测试错误")
        
        result = test_func()
        assert result == "fallback"
    
    def test_sync_error_handler_reraise(self):
        """测试同步错误处理装饰器重新抛出异常"""
        @error_handler(component="test", operation="test_op", reraise=True)
        def test_func():
            raise ValueError("测试错误")
        
        with pytest.raises(ValueError):
            test_func()
    
    @pytest.mark.asyncio
    async def test_async_error_handler_success(self):
        """测试异步错误处理装饰器成功情况"""
        @error_handler(component="test", operation="test_op")
        async def test_func():
            return "success"
        
        result = await test_func()
        assert result == "success"
    
    @pytest.mark.asyncio
    async def test_async_error_handler_with_fallback(self):
        """测试异步错误处理装饰器降级情况"""
        @error_handler(component="test", operation="test_op", reraise=False, fallback_value="fallback")
        async def test_func():
            raise ValueError("测试错误")
        
        result = await test_func()
        assert result == "fallback"


class TestCircuitBreaker:
    """熔断器测试"""
    
    def test_circuit_breaker_closed_state(self):
        """测试熔断器关闭状态"""
        @CircuitBreaker(failure_threshold=2, recovery_timeout=1)
        def test_func():
            return "success"
        
        # 熔断器应该处于关闭状态，允许调用
        result = test_func()
        assert result == "success"
    
    def test_circuit_breaker_open_state(self):
        """测试熔断器打开状态"""
        breaker = CircuitBreaker(failure_threshold=2, recovery_timeout=60)
        
        @breaker
        def test_func():
            raise ValueError("测试错误")
        
        # 触发失败次数达到阈值
        with pytest.raises(ValueError):
            test_func()
        with pytest.raises(ValueError):
            test_func()
        
        # 现在熔断器应该打开，阻止调用
        from src.codenexus.exceptions import ServiceUnavailableError
        with pytest.raises(ServiceUnavailableError):
            test_func()
    
    def test_circuit_breaker_half_open_state(self):
        """测试熔断器半开状态"""
        breaker = CircuitBreaker(failure_threshold=1, recovery_timeout=0.1)
        
        call_count = 0
        
        @breaker
        def test_func():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ValueError("第一次失败")
            return "success"
        
        # 第一次调用失败，触发熔断
        with pytest.raises(ValueError):
            test_func()
        
        # 等待恢复时间
        import time
        time.sleep(0.2)
        
        # 现在应该进入半开状态，允许一次调用
        result = test_func()
        assert result == "success"
        
        # 成功后应该回到关闭状态
        result = test_func()
        assert result == "success"