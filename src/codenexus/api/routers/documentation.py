"""
文档生成路由

提供自动文档生成相关的API端点。
"""

import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response

from ..models import (
    DocumentationRequest,
    DocumentationResponse,
    BaseResponse
)
from ..dependencies import (
    get_ai_service,
    get_database_service,
    get_current_user
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/generate", response_model=DocumentationResponse)
async def generate_documentation(
    request: DocumentationRequest,
    ai_service = Depends(get_ai_service),
    db_service = Depends(get_database_service),
    current_user = Depends(get_current_user)
):
    """
    生成文档
    
    根据指定的代码元素生成结构化文档。
    """
    try:
        logger.info(f"开始生成文档: 类型={request.target_type}, 目标数量={len(request.target_ids)}")
        
        # 获取目标代码元素
        target_elements = []
        for target_id in request.target_ids:
            nodes = await db_service.query_nodes({"id": target_id})
            if nodes:
                target_elements.extend(nodes)
        
        if not target_elements:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="未找到指定的代码元素"
            )
        
        # 构建文档生成上下文
        context = {
            "target_type": request.target_type,
            "elements": target_elements,
            "include_examples": request.include_examples,
            "language": request.language
        }
        
        # 调用AI服务生成文档
        content = await ai_service.generate_documentation(context)
        
        # 构建元数据
        metadata = {
            "target_count": len(target_elements),
            "format_type": request.format_type,
            "language": request.language,
            "generated_at": "2024-01-01T00:00:00Z"  # 实际应该使用当前时间
        }
        
        logger.info(f"文档生成完成: 长度={len(content)} 字符")
        
        return DocumentationResponse(
            content=content,
            format_type=request.format_type,
            metadata=metadata,
            message="文档生成成功"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"文档生成失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"文档生成失败: {str(e)}"
        )


@router.post("/export")
async def export_documentation(
    content: str,
    format_type: str = "html",
    current_user = Depends(get_current_user)
):
    """
    导出文档
    
    将文档内容导出为指定格式的文件。
    """
    try:
        # 这里应该实现文档导出逻辑
        # 目前返回简单的文本响应
        
        if format_type == "html":
            # 简单的Markdown到HTML转换
            html_content = f"<html><body><pre>{content}</pre></body></html>"
            return Response(
                content=html_content,
                media_type="text/html",
                headers={"Content-Disposition": "attachment; filename=documentation.html"}
            )
        elif format_type == "pdf":
            # PDF导出需要额外的库支持
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail="PDF导出功能尚未实现"
            )
        else:
            # 默认返回Markdown
            return Response(
                content=content,
                media_type="text/markdown",
                headers={"Content-Disposition": "attachment; filename=documentation.md"}
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"文档导出失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"文档导出失败: {str(e)}"
        )


@router.get("/templates")
async def get_documentation_templates():
    """
    获取文档模板列表
    """
    templates = [
        {
            "id": "api",
            "name": "API文档模板",
            "description": "用于生成API接口文档",
            "supported_types": ["method", "class", "interface"]
        },
        {
            "id": "module",
            "name": "模块文档模板", 
            "description": "用于生成模块级别的文档",
            "supported_types": ["module", "package", "namespace"]
        },
        {
            "id": "project",
            "name": "项目文档模板",
            "description": "用于生成整个项目的文档",
            "supported_types": ["project"]
        }
    ]
    
    return {
        "success": True,
        "templates": templates,
        "message": f"获取到 {len(templates)} 个文档模板"
    }