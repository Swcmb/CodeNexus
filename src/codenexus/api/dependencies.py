"""
API依赖注入

提供FastAPI路由的依赖注入功能，包括服务实例、数据库连接等。
"""

import logging
from typing import Dict, Optional
from functools import lru_cache

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from ..config import get_settings
from ..parser import get_default_parser
from ..graph import GraphBuilder, GraphOptimizer
from ..database import MockGraphDatabase  # 使用Mock数据库进行开发
from ..ai import create_ai_layer
from ..services import (
    ImpactAnalyzer, 
    ImpactVisualizer,
    QAService,
    RiskDetectionService
)

logger = logging.getLogger(__name__)

# 安全相关
security = HTTPBearer(auto_error=False)


# 配置依赖
@lru_cache()
def get_app_settings():
    """获取应用配置"""
    return get_settings()


# 认证依赖（可选）
async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    settings = Depends(get_app_settings)
):
    """
    获取当前用户（如果启用了认证）
    
    目前是可选的，可以根据需要启用JWT认证。
    """
    if not settings.server.enable_auth:
        return None
    
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="需要认证令牌",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # TODO: 实现JWT令牌验证
    # 这里可以添加JWT令牌解析和验证逻辑
    
    return {"user_id": "anonymous"}


# 服务依赖
@lru_cache()
def get_parser_service():
    """获取代码解析器服务"""
    try:
        return get_default_parser()
    except Exception as e:
        logger.error(f"初始化解析器服务失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="解析器服务不可用"
        )


@lru_cache()
def get_graph_builder_service():
    """获取图构建器服务"""
    try:
        return GraphBuilder()
    except Exception as e:
        logger.error(f"初始化图构建器服务失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="图构建器服务不可用"
        )


@lru_cache()
def get_graph_optimizer_service():
    """获取图优化器服务"""
    try:
        return GraphOptimizer()
    except Exception as e:
        logger.error(f"初始化图优化器服务失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="图优化器服务不可用"
        )


async def get_database_service():
    """获取数据库服务"""
    try:
        # 使用Mock数据库进行开发和测试
        db = MockGraphDatabase()
        # 检查连接
        if not await db.connect():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="数据库连接失败"
            )
        return db
    except Exception as e:
        logger.error(f"获取数据库服务失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="数据库服务不可用"
        )


async def get_ai_service():
    """获取AI服务"""
    try:
        return create_ai_layer()
    except Exception as e:
        logger.error(f"获取AI服务失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI服务不可用"
        )


@lru_cache()
def get_impact_analyzer_service():
    """获取影响分析器服务"""
    try:
        # 创建一个模拟的查询服务
        from ...database.query_service import GraphQueryService
        query_service = GraphQueryService()  # 这里应该传入实际的数据库连接
        return ImpactAnalyzer(query_service=query_service)
    except Exception as e:
        logger.error(f"初始化影响分析器服务失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="影响分析器服务不可用"
        )


@lru_cache()
def get_impact_visualizer_service():
    """获取影响可视化服务"""
    try:
        return ImpactVisualizer()
    except Exception as e:
        logger.error(f"初始化影响可视化服务失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="影响可视化服务不可用"
        )


async def get_qa_service():
    """获取问答服务"""
    try:
        ai_service = await get_ai_service()
        db_service = await get_database_service()
        return QAService(ai_layer=ai_service, graph_db=db_service)
    except Exception as e:
        logger.error(f"初始化问答服务失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="问答服务不可用"
        )


async def get_risk_detection_service():
    """获取风险检测服务"""
    try:
        ai_service = await get_ai_service()
        return RiskDetectionService(ai_layer=ai_service)
    except Exception as e:
        logger.error(f"初始化风险检测服务失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="风险检测服务不可用"
        )


# 健康检查依赖
async def get_database_status() -> Dict[str, str]:
    """获取数据库状态"""
    try:
        db = MockGraphDatabase()
        if await db.connect():
            await db.disconnect()
            return {"status": "healthy"}
        else:
            return {"status": "unhealthy", "error": "连接失败"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


async def get_ai_service_status() -> Dict[str, str]:
    """获取AI服务状态"""
    try:
        ai_service = create_ai_layer()
        # 这里可以添加AI服务的健康检查逻辑
        return {"status": "healthy"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


# 请求验证依赖
def validate_project_path(project_path: str) -> str:
    """验证项目路径"""
    import os
    
    if not project_path or not project_path.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="项目路径不能为空"
        )
    
    project_path = project_path.strip()
    
    if not os.path.exists(project_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"项目路径不存在: {project_path}"
        )
    
    if not os.path.isdir(project_path):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"路径不是目录: {project_path}"
        )
    
    return project_path


def validate_file_path(file_path: str) -> str:
    """验证文件路径"""
    import os
    
    if not file_path or not file_path.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="文件路径不能为空"
        )
    
    file_path = file_path.strip()
    
    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"文件不存在: {file_path}"
        )
    
    if not os.path.isfile(file_path):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"路径不是文件: {file_path}"
        )
    
    return file_path