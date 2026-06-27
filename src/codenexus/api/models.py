"""
API请求和响应模型

定义FastAPI的Pydantic模型，用于请求验证和响应序列化。
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field, validator


# 基础响应模型
class BaseResponse(BaseModel):
    """基础响应模型"""
    success: bool = True
    message: str = "操作成功"
    timestamp: datetime = Field(default_factory=datetime.now)


class ErrorResponse(BaseModel):
    """错误响应模型"""
    success: bool = False
    error: str
    message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.now)


# 代码解析相关模型
class ParseProjectRequest(BaseModel):
    """解析项目请求"""
    project_path: str = Field(..., description="项目路径")
    languages: Optional[List[str]] = Field(default=None, description="指定解析的编程语言")
    exclude_patterns: Optional[List[str]] = Field(default=None, description="排除的文件模式")
    include_tests: bool = Field(default=True, description="是否包含测试文件")
    
    @validator('project_path')
    def validate_project_path(cls, v):
        if not v or not v.strip():
            raise ValueError('项目路径不能为空')
        return v.strip()


class ParseFileRequest(BaseModel):
    """解析文件请求"""
    file_path: str = Field(..., description="文件路径")
    language: Optional[str] = Field(default=None, description="编程语言")


class CodeElementResponse(BaseModel):
    """代码元素响应"""
    id: str
    name: str
    type: str
    file_path: str
    line_number: int
    complexity: Optional[int] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class RelationshipResponse(BaseModel):
    """关系响应"""
    source_id: str
    target_id: str
    type: str
    strength: float = Field(ge=0.0, le=1.0)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ParseResultResponse(BaseResponse):
    """解析结果响应"""
    elements: List[CodeElementResponse]
    relationships: List[RelationshipResponse]
    statistics: Dict[str, Any] = Field(default_factory=dict)


# 图查询相关模型
class GraphQueryRequest(BaseModel):
    """图查询请求"""
    query_type: str = Field(..., description="查询类型")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="查询参数")
    limit: int = Field(default=100, ge=1, le=1000, description="结果限制")
    offset: int = Field(default=0, ge=0, description="结果偏移")


class GraphNodeResponse(BaseModel):
    """图节点响应"""
    id: str
    label: str
    type: str
    properties: Dict[str, Any] = Field(default_factory=dict)


class GraphEdgeResponse(BaseModel):
    """图边响应"""
    source: str
    target: str
    type: str
    properties: Dict[str, Any] = Field(default_factory=dict)


class GraphQueryResponse(BaseResponse):
    """图查询响应"""
    nodes: List[GraphNodeResponse]
    edges: List[GraphEdgeResponse]
    total_count: int
    has_more: bool


class ImpactAnalysisRequest(BaseModel):
    """影响分析请求"""
    node_id: str = Field(..., description="节点ID")
    max_depth: int = Field(default=5, ge=1, le=10, description="最大深度")
    include_reverse: bool = Field(default=True, description="是否包含反向依赖")


class ImpactAnalysisResponse(BaseResponse):
    """影响分析响应"""
    target_node: GraphNodeResponse
    impacted_nodes: List[GraphNodeResponse]
    impact_paths: List[List[str]]
    impact_metrics: Dict[str, float]


# 文档生成相关模型
class DocumentationRequest(BaseModel):
    """文档生成请求"""
    target_type: str = Field(..., description="目标类型: api, module, project")
    target_ids: List[str] = Field(..., description="目标ID列表")
    format_type: str = Field(default="markdown", description="输出格式")
    include_examples: bool = Field(default=True, description="是否包含示例")
    language: str = Field(default="zh", description="文档语言")


class DocumentationResponse(BaseResponse):
    """文档生成响应"""
    content: str
    format_type: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


# 问答相关模型
class QuestionRequest(BaseModel):
    """问题请求"""
    question: str = Field(..., min_length=1, max_length=1000, description="问题内容")
    context_ids: Optional[List[str]] = Field(default=None, description="上下文节点ID")
    language: str = Field(default="zh", description="回答语言")
    
    @validator('question')
    def validate_question(cls, v):
        if not v or not v.strip():
            raise ValueError('问题内容不能为空')
        return v.strip()


class AnswerResponse(BaseResponse):
    """回答响应"""
    answer: str
    relevant_code: List[CodeElementResponse]
    confidence: float = Field(ge=0.0, le=1.0)
    sources: List[str] = Field(default_factory=list)


# 风险检测相关模型
class RiskScanRequest(BaseModel):
    """风险扫描请求"""
    scan_types: List[str] = Field(default=["security", "architecture", "quality"], description="扫描类型")
    severity_filter: Optional[str] = Field(default=None, description="严重程度过滤")
    include_suggestions: bool = Field(default=True, description="是否包含修复建议")


class RiskIssueResponse(BaseModel):
    """风险问题响应"""
    id: str
    title: str
    description: str
    severity: str
    category: str
    affected_elements: List[str]
    suggestions: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class RiskScanResponse(BaseResponse):
    """风险扫描响应"""
    issues: List[RiskIssueResponse]
    summary: Dict[str, int]
    scan_metadata: Dict[str, Any] = Field(default_factory=dict)


# 可视化相关模型
class VisualizationRequest(BaseModel):
    """可视化请求"""
    graph_type: str = Field(..., description="图类型")
    filters: Optional[Dict[str, Any]] = Field(default=None, description="过滤条件")
    layout: str = Field(default="force", description="布局算法")
    max_nodes: int = Field(default=500, ge=1, le=2000, description="最大节点数")


class VisualNodeResponse(BaseModel):
    """可视化节点响应"""
    id: str
    label: str
    type: str
    x: Optional[float] = None
    y: Optional[float] = None
    size: float = Field(default=1.0)
    color: Optional[str] = None
    properties: Dict[str, Any] = Field(default_factory=dict)


class VisualEdgeResponse(BaseModel):
    """可视化边响应"""
    source: str
    target: str
    type: str
    weight: float = Field(default=1.0)
    color: Optional[str] = None
    properties: Dict[str, Any] = Field(default_factory=dict)


class VisualizationResponse(BaseResponse):
    """可视化响应"""
    nodes: List[VisualNodeResponse]
    edges: List[VisualEdgeResponse]
    layout_info: Dict[str, Any] = Field(default_factory=dict)
    statistics: Dict[str, Any] = Field(default_factory=dict)


# 健康检查模型
class HealthCheckResponse(BaseModel):
    """健康检查响应"""
    status: str = "healthy"
    version: str = "0.1.0"
    timestamp: datetime = Field(default_factory=datetime.now)
    services: Dict[str, str] = Field(default_factory=dict)
    uptime: Optional[float] = None


# 分页模型
class PaginationParams(BaseModel):
    """分页参数"""
    page: int = Field(default=1, ge=1, description="页码")
    size: int = Field(default=20, ge=1, le=100, description="每页大小")
    
    @property
    def offset(self) -> int:
        """计算偏移量"""
        return (self.page - 1) * self.size


class PaginatedResponse(BaseResponse):
    """分页响应"""
    data: List[Any]
    pagination: Dict[str, Any]
    
    @classmethod
    def create(
        cls,
        data: List[Any],
        total: int,
        page: int,
        size: int,
        message: str = "查询成功"
    ):
        """创建分页响应"""
        total_pages = (total + size - 1) // size
        has_next = page < total_pages
        has_prev = page > 1
        
        return cls(
            data=data,
            message=message,
            pagination={
                "page": page,
                "size": size,
                "total": total,
                "total_pages": total_pages,
                "has_next": has_next,
                "has_prev": has_prev
            }
        )