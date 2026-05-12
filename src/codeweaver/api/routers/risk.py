"""
风险检测路由

提供代码风险检测和分析相关的API端点。
"""

import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status

from ..models import (
    RiskScanRequest,
    RiskScanResponse,
    RiskIssueResponse,
    BaseResponse
)
from ..dependencies import (
    get_risk_detection_service,
    get_database_service,
    get_current_user
)
from ...services import RiskDetectionService

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/scan", response_model=RiskScanResponse)
async def scan_risks(
    request: RiskScanRequest,
    risk_service: RiskDetectionService = Depends(get_risk_detection_service),
    db_service = Depends(get_database_service),
    current_user = Depends(get_current_user)
):
    """
    扫描风险
    
    对代码库进行全面的风险扫描，包括安全漏洞、架构问题和代码质量问题。
    """
    try:
        logger.info(f"开始风险扫描: 类型={request.scan_types}")
        
        # 获取代码图谱（这里应该从数据库获取）
        # 目前使用空图谱作为占位符
        from ...models.core import CodeGraph
        graph = CodeGraph(nodes=[], edges=[], metadata={})
        
        # 执行风险扫描
        all_issues = []
        
        if "security" in request.scan_types:
            security_issues = await risk_service.scan_security_risks(graph)
            all_issues.extend(security_issues)
        
        if "architecture" in request.scan_types:
            architecture_issues = await risk_service.detect_architecture_smells(graph)
            all_issues.extend(architecture_issues)
        
        if "quality" in request.scan_types:
            quality_result = await risk_service.analyze_code_quality(graph)
            # 将质量问题转换为风险问题
            for issue in quality_result.get("issues", []):
                all_issues.append(issue)
        
        # 应用严重程度过滤
        if request.severity_filter:
            all_issues = [
                issue for issue in all_issues
                if issue.get("severity") == request.severity_filter
            ]
        
        # 转换为响应格式
        issue_responses = []
        for issue in all_issues:
            issue_responses.append(RiskIssueResponse(
                id=issue.get("id", ""),
                title=issue.get("title", ""),
                description=issue.get("description", ""),
                severity=issue.get("severity", "medium"),
                category=issue.get("category", "unknown"),
                affected_elements=issue.get("affected_elements", []),
                suggestions=issue.get("suggestions", []) if request.include_suggestions else [],
                metadata=issue.get("metadata", {})
            ))
        
        # 生成摘要
        summary = {
            "total": len(issue_responses),
            "critical": len([i for i in issue_responses if i.severity == "critical"]),
            "high": len([i for i in issue_responses if i.severity == "high"]),
            "medium": len([i for i in issue_responses if i.severity == "medium"]),
            "low": len([i for i in issue_responses if i.severity == "low"])
        }
        
        # 扫描元数据
        scan_metadata = {
            "scan_types": request.scan_types,
            "total_scanned": 0,  # 应该是实际扫描的元素数量
            "scan_duration": 0.0  # 应该是实际扫描时间
        }
        
        logger.info(f"风险扫描完成: 发现 {len(issue_responses)} 个问题")
        
        return RiskScanResponse(
            issues=issue_responses,
            summary=summary,
            scan_metadata=scan_metadata,
            message=f"扫描完成，发现 {len(issue_responses)} 个风险问题"
        )
        
    except Exception as e:
        logger.error(f"风险扫描失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"风险扫描失败: {str(e)}"
        )


@router.get("/issues/{issue_id}")
async def get_issue_details(
    issue_id: str,
    current_user = Depends(get_current_user)
):
    """
    获取风险问题详情
    """
    try:
        # 这里应该从数据库获取问题详情
        # 目前返回模拟数据
        
        issue = {
            "id": issue_id,
            "title": "SQL注入风险",
            "description": "在UserService.login方法中发现潜在的SQL注入漏洞",
            "severity": "high",
            "category": "security",
            "affected_elements": ["UserService.login"],
            "suggestions": [
                "使用参数化查询",
                "添加输入验证",
                "使用ORM框架"
            ],
            "code_snippet": "SELECT * FROM users WHERE username = '" + username + "'",
            "references": [
                "https://owasp.org/www-community/attacks/SQL_Injection"
            ]
        }
        
        return {
            "success": True,
            "issue": issue,
            "message": "获取问题详情成功"
        }
        
    except Exception as e:
        logger.error(f"获取问题详情失败: {issue_id}, 错误: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取问题详情失败: {str(e)}"
        )


@router.post("/report")
async def generate_risk_report(
    format_type: str = "markdown",
    include_suggestions: bool = True,
    risk_service: RiskDetectionService = Depends(get_risk_detection_service),
    current_user = Depends(get_current_user)
):
    """
    生成风险报告
    
    生成详细的风险分析报告。
    """
    try:
        # 获取所有风险问题
        from ...models.core import CodeGraph
        graph = CodeGraph(nodes=[], edges=[], metadata={})
        
        security_issues = await risk_service.scan_security_risks(graph)
        architecture_issues = await risk_service.detect_architecture_smells(graph)
        quality_result = await risk_service.analyze_code_quality(graph)
        
        all_issues = security_issues + architecture_issues + quality_result.get("issues", [])
        
        # 生成报告
        report = await risk_service.generate_risk_report(all_issues)
        
        return {
            "success": True,
            "report": report,
            "format": format_type,
            "message": "风险报告生成成功"
        }
        
    except Exception as e:
        logger.error(f"生成风险报告失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"生成风险报告失败: {str(e)}"
        )


@router.get("/rules")
async def get_detection_rules():
    """
    获取检测规则列表
    """
    rules = [
        {
            "id": "sql-injection",
            "name": "SQL注入检测",
            "category": "security",
            "severity": "high",
            "enabled": True
        },
        {
            "id": "circular-dependency",
            "name": "循环依赖检测",
            "category": "architecture",
            "severity": "medium",
            "enabled": True
        },
        {
            "id": "high-complexity",
            "name": "高复杂度检测",
            "category": "quality",
            "severity": "medium",
            "enabled": True
        }
    ]
    
    return {
        "success": True,
        "rules": rules,
        "total": len(rules),
        "message": f"获取到 {len(rules)} 条检测规则"
    }