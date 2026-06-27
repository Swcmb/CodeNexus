"""
代码解析路由

提供代码解析相关的API端点。
"""

import asyncio
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from fastapi.responses import JSONResponse

from ..models import (
    ParseProjectRequest,
    ParseFileRequest, 
    ParseResultResponse,
    CodeElementResponse,
    RelationshipResponse,
    BaseResponse
)
from ..dependencies import (
    get_parser_service,
    get_current_user,
    validate_project_path,
    validate_file_path
)
from ...parser import TreeSitterParser
from ...models.core import ParseResult

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/project", response_model=ParseResultResponse)
async def parse_project(
    request: ParseProjectRequest,
    background_tasks: BackgroundTasks,
    parser: TreeSitterParser = Depends(get_parser_service),
    current_user = Depends(get_current_user)
):
    """
    解析整个项目
    
    解析指定项目路径下的所有源代码文件，提取代码元素和关系。
    """
    try:
        # 验证项目路径
        project_path = validate_project_path(request.project_path)
        
        logger.info(f"开始解析项目: {project_path}")
        
        # 执行解析
        parse_results = parser.parse_project(project_path)
        
        # 转换为响应格式
        all_elements = []
        all_relationships = []
        
        for result in parse_results:
            # 转换代码元素
            for element in result.elements:
                all_elements.append(CodeElementResponse(
                    id=element.id,
                    name=element.name,
                    type=element.type.value,
                    file_path=element.file_path,
                    line_number=element.line_number,
                    complexity=element.complexity,
                    metadata=element.metadata
                ))
            
            # 转换关系
            for relationship in result.relationships:
                all_relationships.append(RelationshipResponse(
                    source_id=relationship.source_id,
                    target_id=relationship.target_id,
                    type=relationship.type.value,
                    strength=relationship.strength,
                    metadata=relationship.metadata
                ))
        
        # 统计信息
        statistics = {
            "total_files": len(parse_results),
            "total_elements": len(all_elements),
            "total_relationships": len(all_relationships),
            "element_types": {},
            "relationship_types": {}
        }
        
        # 统计元素类型
        for element in all_elements:
            element_type = element.type
            statistics["element_types"][element_type] = statistics["element_types"].get(element_type, 0) + 1
        
        # 统计关系类型
        for relationship in all_relationships:
            rel_type = relationship.type
            statistics["relationship_types"][rel_type] = statistics["relationship_types"].get(rel_type, 0) + 1
        
        logger.info(f"项目解析完成: {project_path}, 元素数量: {len(all_elements)}, 关系数量: {len(all_relationships)}")
        
        return ParseResultResponse(
            elements=all_elements,
            relationships=all_relationships,
            statistics=statistics,
            message=f"成功解析项目 {project_path}"
        )
        
    except Exception as e:
        logger.error(f"解析项目失败: {project_path}, 错误: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"解析项目失败: {str(e)}"
        )


@router.post("/file", response_model=ParseResultResponse)
async def parse_file(
    request: ParseFileRequest,
    parser: TreeSitterParser = Depends(get_parser_service),
    current_user = Depends(get_current_user)
):
    """
    解析单个文件
    
    解析指定的源代码文件，提取代码元素和关系。
    """
    try:
        # 验证文件路径
        file_path = validate_file_path(request.file_path)
        
        logger.info(f"开始解析文件: {file_path}")
        
        # 执行解析
        result = parser.parse_file(file_path)
        
        # 转换代码元素
        elements = []
        relationships = []
        
        if result.parse_result:
            for element in result.parse_result.elements:
                elements.append(CodeElementResponse(
                    id=element.id,
                    name=element.name,
                    type=element.type.value,
                    file_path=element.file_path,
                    line_number=element.line_number,
                    complexity=element.complexity,
                    metadata=element.metadata
                ))
            
            # 转换关系
            for relationship in result.parse_result.relationships:
                relationships.append(RelationshipResponse(
                    source_id=relationship.source_id,
                    target_id=relationship.target_id,
                    type=relationship.type.value,
                    strength=relationship.strength,
                    metadata=relationship.metadata
                ))
        
        # 统计信息
        statistics = {
            "file_path": file_path,
            "total_elements": len(elements),
            "total_relationships": len(relationships),
            "element_types": {},
            "relationship_types": {}
        }
        
        # 统计元素类型
        for element in elements:
            element_type = element.type
            statistics["element_types"][element_type] = statistics["element_types"].get(element_type, 0) + 1
        
        # 统计关系类型
        for relationship in relationships:
            rel_type = relationship.type
            statistics["relationship_types"][rel_type] = statistics["relationship_types"].get(rel_type, 0) + 1
        
        logger.info(f"文件解析完成: {file_path}, 元素数量: {len(elements)}, 关系数量: {len(relationships)}")
        
        return ParseResultResponse(
            elements=elements,
            relationships=relationships,
            statistics=statistics,
            message=f"成功解析文件 {file_path}"
        )
        
    except Exception as e:
        logger.error(f"解析文件失败: {file_path}, 错误: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"解析文件失败: {str(e)}"
        )


@router.get("/languages")
async def get_supported_languages(
    parser: TreeSitterParser = Depends(get_parser_service)
):
    """
    获取支持的编程语言列表
    
    返回解析器支持的所有编程语言。
    """
    try:
        languages = parser.get_supported_languages()
        return {
            "success": True,
            "languages": languages,
            "message": f"支持 {len(languages)} 种编程语言"
        }
    except Exception as e:
        logger.error(f"获取支持的语言列表失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取语言列表失败: {str(e)}"
        )


@router.get("/status")
async def get_parser_status():
    """
    获取解析器状态
    
    返回解析器的当前状态和配置信息。
    """
    try:
        return {
            "success": True,
            "status": "healthy",
            "message": "解析器服务正常运行",
            "capabilities": {
                "multi_language": True,
                "cross_file_analysis": True,
                "relationship_extraction": True,
                "ast_parsing": True
            }
        }
    except Exception as e:
        logger.error(f"获取解析器状态失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取解析器状态失败: {str(e)}"
        )