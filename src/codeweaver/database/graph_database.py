"""
图数据库接口

提供内存图数据库的连接和基础操作功能。
"""

import logging
from typing import Dict, List, Optional, Any

from .memory_graph import MemoryGraphDatabase
from ..models.core import CodeGraph, GraphNode, GraphEdge, GraphMetadata
from ..exceptions import DatabaseError


logger = logging.getLogger(__name__)


class GraphDatabase:
    """图数据库连接管理类"""
    
    def __init__(self):
        """初始化图数据库连接"""
        self.memory_db: Optional[MemoryGraphDatabase] = None
        self._is_connected = False
        
    def connect(self) -> bool:
        """连接到内存图数据库
        
        Returns:
            连接是否成功
        """
        try:
            logger.info("初始化内存图数据库连接")
            
            self.memory_db = MemoryGraphDatabase("default")
            self.memory_db.connect()
            
            self._is_connected = True
            logger.info("内存图数据库连接成功")
            return True
            
        except Exception as e:
            logger.error(f"内存图数据库连接失败: {e}")
            self._is_connected = False
            return False
    
    def disconnect(self) -> None:
        """断开数据库连接"""
        if self.memory_db:
            self.memory_db.disconnect()
            self.memory_db = None
        self._is_connected = False
        logger.info("内存图数据库连接已断开")
    
    def is_connected(self) -> bool:
        """检查连接状态"""
        return self._is_connected
    
    def save_graph(self, graph: CodeGraph) -> bool:
        """保存图数据
        
        Args:
            graph: 代码图谱
            
        Returns:
            是否保存成功
        """
        if not self._is_connected or not self.memory_db:
            raise DatabaseError("数据库未连接")
        
        return self.memory_db.save_graph(graph)
    
    def load_graph(self) -> Optional[CodeGraph]:
        """加载图数据
        
        Returns:
            代码图谱或None
        """
        if not self._is_connected or not self.memory_db:
            raise DatabaseError("数据库未连接")
        
        return self.memory_db.load_graph()
    
    def export_to_file(self, file_path: str, format: str = "json") -> bool:
        """导出图数据到文件
        
        Args:
            file_path: 文件路径
            format: 导出格式
            
        Returns:
            是否导出成功
        """
        if not self._is_connected or not self.memory_db:
            raise DatabaseError("数据库未连接")
        
        return self.memory_db.export_to_file(file_path, format)
    
    def import_from_file(self, file_path: str, format: str = "json") -> bool:
        """从文件导入图数据
        
        Args:
            file_path: 文件路径
            format: 导入格式
            
        Returns:
            是否导入成功
        """
        if not self._is_connected or not self.memory_db:
            raise DatabaseError("数据库未连接")
        
        return self.memory_db.import_from_file(file_path, format)
    
    def get_database_info(self) -> Dict[str, Any]:
        """获取数据库信息"""
        if not self._is_connected or not self.memory_db:
            return {"status": "disconnected"}
        
        try:
            stats = self.memory_db.get_statistics()
            return {
                "status": "connected",
                "uri": "memory://default",
                "node_count": stats["node_count"],
                "relationship_count": stats["edge_count"]
            }
        except Exception as e:
            logger.error(f"获取数据库信息失败: {e}")
            return {"status": "error", "error": str(e)}
    
    def clear_database(self) -> bool:
        """清空数据库"""
        if not self._is_connected or not self.memory_db:
            return False
        
        try:
            self.memory_db.clear()
            logger.info("数据库已清空")
            return True
        except Exception as e:
            logger.error(f"清空数据库失败: {e}")
            return False
    
    def get_memory_db(self) -> Optional[MemoryGraphDatabase]:
        """获取内存图数据库实例"""
        return self.memory_db