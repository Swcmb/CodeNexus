"""
codenexus Web API模块

提供RESTful API接口，用于代码分析、图谱查询、文档生成等功能。
"""

from .app import create_app, get_app

__all__ = [
    "create_app",
    "get_app",
]
