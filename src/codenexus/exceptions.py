"""
自定义异常类

定义codenexus系统的自定义异常。
"""

from typing import Any


class codenexusError(Exception):
    """codenexus基础异常类"""
    pass


class codenexusException(Exception):
    """codenexus HTTP异常类"""
    
    def __init__(self, message: str, status_code: int = 500, error_code: str = "INTERNAL_ERROR", details: Any = None):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details = details
        super().__init__(message)


class ParseError(codenexusError):
    """代码解析异常"""
    pass


class GraphBuildError(codenexusError):
    """图构建异常"""
    pass


class DatabaseError(codenexusError):
    """数据库操作异常"""
    pass


class AIServiceError(codenexusError):
    """AI服务异常"""
    pass


class AILayerError(codenexusError):
    """AI层异常"""
    pass


class ConfigurationError(codenexusError):
    """配置异常"""
    pass


class ValidationError(codenexusError):
    """数据验证异常"""
    pass


class ServiceUnavailableError(codenexusError):
    """服务不可用异常"""
    pass


class DocumentationError(codenexusError):
    """文档生成异常"""
    pass


class QAServiceError(codenexusError):
    """问答服务异常"""
    pass


class CacheServiceError(codenexusError):
    """缓存服务异常"""
    pass


class PerformanceError(codenexusError):
    """性能管理异常"""
    pass