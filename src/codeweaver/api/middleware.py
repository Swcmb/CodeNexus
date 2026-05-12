"""
API中间件

提供日志记录、错误处理、请求追踪等中间件功能。
"""

import time
import uuid
import logging
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from ..utils.error_handler import global_error_handler, ErrorContext
from ..utils.monitoring import metrics_collector

logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """请求日志中间件"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """处理请求并记录日志"""
        # 生成请求ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # 记录请求开始
        start_time = time.time()
        logger.info(
            f"请求开始 - ID: {request_id}, 方法: {request.method}, "
            f"路径: {request.url.path}, 客户端: {request.client.host if request.client else 'unknown'}"
        )
        
        # 记录请求到监控系统
        metrics_collector.record_request(f"{request.method} {request.url.path}")
        
        try:
            # 处理请求
            response = await call_next(request)
            
            # 计算处理时间
            process_time = time.time() - start_time
            
            # 记录响应时间到监控系统
            metrics_collector.record_response_time(process_time * 1000)  # 转换为毫秒
            
            # 记录请求完成
            logger.info(
                f"请求完成 - ID: {request_id}, 状态码: {response.status_code}, "
                f"处理时间: {process_time:.3f}s"
            )
            
            # 添加响应头
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Process-Time"] = str(process_time)
            
            return response
            
        except Exception as exc:
            # 记录异常
            process_time = time.time() - start_time
            logger.error(
                f"请求异常 - ID: {request_id}, 异常: {exc}, "
                f"处理时间: {process_time:.3f}s",
                exc_info=True
            )
            
            # 记录错误到监控系统
            metrics_collector.record_error(type(exc).__name__)
            
            raise


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """错误处理中间件"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """处理请求并捕获未处理的异常"""
        try:
            response = await call_next(request)
            return response
            
        except Exception as exc:
            # 记录异常详情
            request_id = getattr(request.state, 'request_id', 'unknown')
            logger.error(
                f"未处理的异常 - 请求ID: {request_id}, 异常类型: {type(exc).__name__}, "
                f"异常信息: {str(exc)}",
                exc_info=True
            )
            
            # 记录到错误处理系统
            context = ErrorContext(
                operation=f"{request.method} {request.url.path}",
                component="api",
                request_id=request_id
            )
            global_error_handler.handle_error(exc, context, attempt_recovery=False)
            
            # 记录错误到监控系统
            metrics_collector.record_error(type(exc).__name__)
            
            # 返回统一的错误响应
            return JSONResponse(
                status_code=500,
                content={
                    "error": "INTERNAL_SERVER_ERROR",
                    "message": "服务器内部错误",
                    "request_id": request_id,
                    "details": None
                }
            )


class RateLimitMiddleware(BaseHTTPMiddleware):
    """速率限制中间件"""
    
    def __init__(self, app, calls: int = 100, period: int = 60):
        """
        初始化速率限制中间件
        
        Args:
            app: FastAPI应用实例
            calls: 允许的调用次数
            period: 时间窗口（秒）
        """
        super().__init__(app)
        self.calls = calls
        self.period = period
        self.clients = {}  # 简单的内存存储，生产环境应使用Redis
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """检查速率限制"""
        client_ip = request.client.host if request.client else "unknown"
        current_time = time.time()
        
        # 清理过期记录
        self.clients = {
            ip: calls for ip, calls in self.clients.items()
            if any(call_time > current_time - self.period for call_time in calls)
        }
        
        # 检查当前客户端的调用记录
        if client_ip not in self.clients:
            self.clients[client_ip] = []
        
        # 过滤时间窗口内的调用
        recent_calls = [
            call_time for call_time in self.clients[client_ip]
            if call_time > current_time - self.period
        ]
        
        # 检查是否超过限制
        if len(recent_calls) >= self.calls:
            return JSONResponse(
                status_code=429,
                content={
                    "error": "RATE_LIMIT_EXCEEDED",
                    "message": f"请求频率过高，每{self.period}秒最多允许{self.calls}次请求",
                    "retry_after": self.period
                },
                headers={"Retry-After": str(self.period)}
            )
        
        # 记录当前调用
        self.clients[client_ip] = recent_calls + [current_time]
        
        # 继续处理请求
        response = await call_next(request)
        
        # 添加速率限制相关的响应头
        response.headers["X-RateLimit-Limit"] = str(self.calls)
        response.headers["X-RateLimit-Remaining"] = str(self.calls - len(self.clients[client_ip]))
        response.headers["X-RateLimit-Reset"] = str(int(current_time + self.period))
        
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """安全头中间件"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """添加安全相关的HTTP头"""
        response = await call_next(request)
        
        # 添加安全头
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        return response