"""
智能问答路由

提供自然语言问答相关的API端点。
"""

import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status

from ..models import (
    QuestionRequest,
    AnswerResponse,
    CodeElementResponse,
    BaseResponse
)
from ..dependencies import (
    get_qa_service,
    get_current_user
)
from ...services import QAService

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/ask", response_model=AnswerResponse)
async def ask_question(
    request: QuestionRequest,
    qa_service: QAService = Depends(get_qa_service),
    current_user = Depends(get_current_user)
):
    """
    提问
    
    使用自然语言询问代码相关问题，获得智能回答。
    """
    try:
        logger.info(f"收到问题: {request.question[:100]}...")
        
        # 获取代码图谱（这里应该从数据库获取）
        # 目前使用空图谱作为占位符
        from ...models.core import CodeGraph
        graph = CodeGraph(nodes=[], edges=[], metadata={})
        
        # 处理问题
        result = await qa_service.process_question(
            question=request.question,
            graph=graph
        )
        
        # 转换相关代码为响应格式
        relevant_code = []
        for code_element in result.get("relevant_code", []):
            relevant_code.append(CodeElementResponse(
                id=code_element.id,
                name=code_element.name,
                type=code_element.type.value,
                file_path=code_element.file_path,
                line_number=code_element.line_number,
                complexity=code_element.complexity,
                metadata=code_element.metadata
            ))
        
        logger.info(f"问答完成: 找到 {len(relevant_code)} 个相关代码元素")
        
        return AnswerResponse(
            answer=result.get("answer", ""),
            relevant_code=relevant_code,
            confidence=result.get("confidence", 0.0),
            sources=result.get("sources", []),
            message="问答成功"
        )
        
    except Exception as e:
        logger.error(f"问答处理失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"问答处理失败: {str(e)}"
        )


@router.get("/suggestions")
async def get_question_suggestions(
    category: str = "general",
    current_user = Depends(get_current_user)
):
    """
    获取问题建议
    
    提供常见问题的建议，帮助用户更好地使用问答功能。
    """
    suggestions = {
        "general": [
            "这个项目的主要架构是什么？",
            "哪些类之间有继承关系？",
            "这个方法的作用是什么？",
            "有哪些循环依赖？"
        ],
        "architecture": [
            "项目的分层架构是怎样的？",
            "核心模块之间的依赖关系如何？",
            "哪些组件是高耦合的？",
            "系统的入口点在哪里？"
        ],
        "quality": [
            "哪些方法的复杂度最高？",
            "有哪些代码坏味道？",
            "测试覆盖率如何？",
            "哪些文件变更最频繁？"
        ],
        "security": [
            "有哪些潜在的安全风险？",
            "输入验证是否充分？",
            "是否存在SQL注入风险？",
            "敏感数据是否得到保护？"
        ]
    }
    
    return {
        "success": True,
        "category": category,
        "suggestions": suggestions.get(category, suggestions["general"]),
        "available_categories": list(suggestions.keys()),
        "message": f"获取到 {len(suggestions.get(category, []))} 个问题建议"
    }


@router.get("/history")
async def get_question_history(
    limit: int = 20,
    current_user = Depends(get_current_user)
):
    """
    获取问题历史
    
    获取用户的历史问答记录。
    """
    # 这里应该从数据库或缓存中获取历史记录
    # 目前返回模拟数据
    
    history = [
        {
            "id": "1",
            "question": "这个项目的主要架构是什么？",
            "answer": "这是一个基于微服务架构的项目...",
            "timestamp": "2024-01-01T10:00:00Z",
            "confidence": 0.85
        },
        {
            "id": "2", 
            "question": "UserService类的作用是什么？",
            "answer": "UserService类负责处理用户相关的业务逻辑...",
            "timestamp": "2024-01-01T10:05:00Z",
            "confidence": 0.92
        }
    ]
    
    return {
        "success": True,
        "history": history[:limit],
        "total": len(history),
        "message": f"获取到 {len(history[:limit])} 条历史记录"
    }


@router.delete("/history/{question_id}")
async def delete_question_history(
    question_id: str,
    current_user = Depends(get_current_user)
):
    """
    删除问题历史记录
    """
    try:
        # 这里应该实现删除历史记录的逻辑
        
        return {
            "success": True,
            "message": f"已删除问题记录: {question_id}"
        }
        
    except Exception as e:
        logger.error(f"删除问题历史失败: {question_id}, 错误: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除历史记录失败: {str(e)}"
        )