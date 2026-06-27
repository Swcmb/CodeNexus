"""
API路由模块

包含所有API端点的路由定义。
"""

from .health import router as health_router
from .parser import router as parser_router
from .graph import router as graph_router
from .documentation import router as documentation_router
from .qa import router as qa_router
from .risk import router as risk_router
from .visualization import router as visualization_router
from .backup import router as backup_router

__all__ = [
    "health_router",
    "parser_router", 
    "graph_router",
    "documentation_router",
    "qa_router",
    "risk_router",
    "visualization_router",
    "backup_router",
]