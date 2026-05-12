"""
FastAPI应用程序主入口

创建和配置FastAPI应用实例，设置中间件、路由和全局配置。
"""

from contextlib import asynccontextmanager
from typing import Dict, Any
import logging

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from ..config import get_settings
from ..exceptions import codenexusException
from ..utils.error_handler import global_error_handler, ErrorContext
from ..utils.monitoring import start_monitoring, stop_monitoring, health_checker
from ..utils.scheduler import async_task_scheduler
from .middleware import LoggingMiddleware, ErrorHandlingMiddleware
from .routers import (
    parser_router,
    graph_router,
    documentation_router,
    qa_router,
    risk_router,
    visualization_router,
    health_router,
    backup_router
)

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 全局应用实例
_app_instance: FastAPI = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    logger.info("codenexus API 启动中...")
    
    # 启动时的初始化逻辑
    settings = get_settings()
    
    # 启动监控系统
    start_monitoring()
    
    # 启动异步任务调度器
    await async_task_scheduler.start()
    
    # 初始化数据库连接等资源
    # TODO: 在这里添加数据库连接初始化
    
    logger.info("codenexus API 启动完成")
    
    yield
    
    # 关闭时的清理逻辑
    logger.info("codenexus API 关闭中...")
    
    # 停止异步任务调度器
    await async_task_scheduler.stop()
    
    # 停止监控系统
    stop_monitoring()
    
    # 清理资源
    # TODO: 在这里添加资源清理逻辑
    
    logger.info("codenexus API 已关闭")


def create_app() -> FastAPI:
    """创建FastAPI应用实例"""
    global _app_instance
    
    if _app_instance is not None:
        return _app_instance
    
    settings = get_settings()
    
    # 创建FastAPI应用
    app = FastAPI(
        title="codenexus API",
        description="智能代码分析与知识图谱构建工具的Web API",
        version="0.1.0",
        docs_url="/docs" if settings.server.debug else None,
        redoc_url="/redoc" if settings.server.debug else None,
        lifespan=lifespan
    )
    
    # 配置CORS中间件
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.server.allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )
    
    # 配置受信任主机中间件
    if settings.server.trusted_hosts and settings.server.trusted_hosts != ["*"]:
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=settings.server.trusted_hosts
        )
    
    # 添加自定义中间件
    app.add_middleware(LoggingMiddleware)
    app.add_middleware(ErrorHandlingMiddleware)
    
    # 注册路由
    app.include_router(health_router, prefix="/api/v1", tags=["健康检查"])
    app.include_router(parser_router, prefix="/api/v1/parser", tags=["代码解析"])
    app.include_router(graph_router, prefix="/api/v1/graph", tags=["知识图谱"])
    app.include_router(documentation_router, prefix="/api/v1/docs", tags=["文档生成"])
    app.include_router(qa_router, prefix="/api/v1/qa", tags=["智能问答"])
    app.include_router(risk_router, prefix="/api/v1/risk", tags=["风险检测"])
    app.include_router(visualization_router, prefix="/api/v1/viz", tags=["可视化"])
    app.include_router(backup_router, prefix="/api/v1/backup", tags=["备份恢复"])
    
    # 全局异常处理器
    @app.exception_handler(codenexusException)
    async def codenexus_exception_handler(request: Request, exc: codenexusException):
        """处理codenexus自定义异常"""
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.error_code,
                "message": exc.message,
                "details": exc.details
            }
        )
    
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """处理HTTP异常"""
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": "HTTP_ERROR",
                "message": exc.detail,
                "details": None
            }
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """处理通用异常"""
        logger.error(f"未处理的异常: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "error": "INTERNAL_SERVER_ERROR",
                "message": "服务器内部错误",
                "details": str(exc) if settings.server.debug else None
            }
        )
    
    # 根路径重定向到API文档
    @app.get("/")
    async def root():
        """根路径"""
        return {
            "message": "欢迎使用codenexus API",
            "version": "0.1.0",
            "docs_url": "/docs",
            "health_check": "/api/v1/health"
        }
    
    _app_instance = app
    return app


def get_app() -> FastAPI:
    """获取应用实例"""
    if _app_instance is None:
        return create_app()
    return _app_instance


def run_server(
    host: str = "0.0.0.0",
    port: int = 8000,
    reload: bool = False,
    log_level: str = "info"
):
    """运行开发服务器"""
    app = create_app()
    uvicorn.run(
        app,
        host=host,
        port=port,
        reload=reload,
        log_level=log_level
    )


if __name__ == "__main__":
    # 开发模式运行
    run_server(reload=True)