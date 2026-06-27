"""
内存图数据库

使用内存数据结构存储图数据，无需外部数据库依赖。
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, asdict
import pickle

from ..models.core import CodeGraph, GraphNode, GraphEdge, GraphMetadata
from ..exceptions import DatabaseError


logger = logging.getLogger(__name__)


@dataclass
class MemoryGraphStorage:
    """内存图存储结构"""
    nodes: Dict[str, GraphNode] = None
    edges: Dict[str, GraphEdge] = None
    metadata: Optional[GraphMetadata] = None
    adjacency_list: Dict[str, Set[str]] = None  # 邻接表
    
    def __post_init__(self):
        if self.nodes is None:
            self.nodes = {}
        if self.edges is None:
            self.edges = {}
        if self.adjacency_list is None:
            self.adjacency_list = {}


class MemoryGraphDatabase:
    """内存图数据库
    
    提供图数据的存储、查询和管理功能，无需外部数据库。
    """
    
    def __init__(self, name: str = "default"):
        """初始化内存图数据库
        
        Args:
            name: 图数据库名称
        """
        self.name = name
        self.storage = MemoryGraphStorage()
        self._is_connected = True
        
    def connect(self) -> bool:
        """连接到数据库（内存模式总是成功）"""
        self._is_connected = True
        logger.info(f"内存图数据库 '{self.name}' 已连接")
        return True
    
    def disconnect(self) -> None:
        """断开数据库连接"""
        self._is_connected = False
        logger.info(f"内存图数据库 '{self.name}' 已断开")
    
    def is_connected(self) -> bool:
        """检查连接状态"""
        return self._is_connected
    
    def save_graph(self, graph: CodeGraph) -> bool:
        """保存图数据到内存
        
        Args:
            graph: 代码图谱
            
        Returns:
            是否保存成功
        """
        try:
            # 清空现有数据
            self.storage.nodes.clear()
            self.storage.edges.clear()
            self.storage.adjacency_list.clear()
            
            # 保存节点
            for node in graph.nodes:
                self.storage.nodes[node.id] = node
            
            # 保存边并构建邻接表
            for edge in graph.edges:
                self.storage.edges[edge.id] = edge
                
                # 更新邻接表
                if edge.source_id not in self.storage.adjacency_list:
                    self.storage.adjacency_list[edge.source_id] = set()
                if edge.target_id not in self.storage.adjacency_list:
                    self.storage.adjacency_list[edge.target_id] = set()
                    
                self.storage.adjacency_list[edge.source_id].add(edge.target_id)
            
            # 保存元数据
            self.storage.metadata = graph.metadata
            
            logger.info(f"图数据已保存到内存: {len(graph.nodes)} 节点, {len(graph.edges)} 边")
            return True
            
        except Exception as e:
            logger.error(f"保存图数据失败: {e}")
            return False
    
    def load_graph(self) -> Optional[CodeGraph]:
        """从内存加载图数据
        
        Returns:
            代码图谱或None
        """
        try:
            if not self.storage.nodes and not self.storage.edges:
                return None
            
            nodes = list(self.storage.nodes.values())
            edges = list(self.storage.edges.values())
            
            graph = CodeGraph(
                nodes=nodes,
                edges=edges,
                metadata=self.storage.metadata
            )
            
            logger.info(f"从内存加载图数据: {len(nodes)} 节点, {len(edges)} 边")
            return graph
            
        except Exception as e:
            logger.error(f"加载图数据失败: {e}")
            return None
    
    def export_to_file(self, file_path: str, format: str = "json") -> bool:
        """导出图数据到文件
        
        Args:
            file_path: 文件路径
            format: 导出格式 (json, pickle)
            
        Returns:
            是否导出成功
        """
        try:
            graph = self.load_graph()
            if not graph:
                return False
            
            if format.lower() == "json":
                graph_data = {
                    "nodes": [node.to_dict() for node in graph.nodes],
                    "edges": [edge.to_dict() for edge in graph.edges],
                    "metadata": graph.metadata.to_dict() if graph.metadata else {}
                }
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(graph_data, f, ensure_ascii=False, indent=2)
                    
            elif format.lower() == "pickle":
                with open(file_path, 'wb') as f:
                    pickle.dump(graph, f)
            else:
                raise ValueError(f"不支持的导出格式: {format}")
            
            logger.info(f"图数据已导出到: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"导出图数据失败: {e}")
            return False
    
    def import_from_file(self, file_path: str, format: str = "json") -> bool:
        """从文件导入图数据
        
        Args:
            file_path: 文件路径
            format: 导入格式 (json, pickle)
            
        Returns:
            是否导入成功
        """
        try:
            if not Path(file_path).exists():
                logger.error(f"文件不存在: {file_path}")
                return False
            
            if format.lower() == "json":
                with open(file_path, 'r', encoding='utf-8') as f:
                    graph_data = json.load(f)
                
                # 重构图对象
                nodes = []
                edges = []
                
                for node_data in graph_data.get("nodes", []):
                    node = GraphNode(**node_data)
                    nodes.append(node)
                
                for edge_data in graph_data.get("edges", []):
                    edge = GraphEdge(**edge_data)
                    edges.append(edge)
                
                metadata_data = graph_data.get("metadata", {})
                metadata = GraphMetadata(**metadata_data) if metadata_data else None
                
                graph = CodeGraph(
                    nodes=nodes,
                    edges=edges,
                    metadata=metadata
                )
                
            elif format.lower() == "pickle":
                with open(file_path, 'rb') as f:
                    graph = pickle.load(f)
            else:
                raise ValueError(f"不支持的导入格式: {format}")
            
            # 保存到内存
            return self.save_graph(graph)
            
        except Exception as e:
            logger.error(f"导入图数据失败: {e}")
            return False
    
    def get_node_count(self) -> int:
        """获取节点数量"""
        return len(self.storage.nodes)
    
    def get_edge_count(self) -> int:
        """获取边数量"""
        return len(self.storage.edges)
    
    def get_node_by_id(self, node_id: str) -> Optional[GraphNode]:
        """根据ID获取节点"""
        return self.storage.nodes.get(node_id)
    
    def get_edge_by_id(self, edge_id: str) -> Optional[GraphEdge]:
        """根据ID获取边"""
        return self.storage.edges.get(edge_id)
    
    def get_neighbors(self, node_id: str) -> List[str]:
        """获取节点的邻居节点ID列表"""
        return list(self.storage.adjacency_list.get(node_id, []))
    
    def find_nodes_by_type(self, node_type: str) -> List[GraphNode]:
        """根据类型查找节点"""
        return [node for node in self.storage.nodes.values() if node.type == node_type]
    
    def find_edges_by_type(self, edge_type: str) -> List[GraphEdge]:
        """根据类型查找边"""
        return [edge for edge in self.storage.edges.values() if edge.type == edge_type]
    
    def find_nodes_by_property(self, property_name: str, property_value: Any) -> List[GraphNode]:
        """根据属性查找节点"""
        result = []
        for node in self.storage.nodes.values():
            if node.properties.get(property_name) == property_value:
                result.append(node)
        return result
    
    def clear(self) -> None:
        """清空所有数据"""
        self.storage.nodes.clear()
        self.storage.edges.clear()
        self.storage.adjacency_list.clear()
        self.storage.metadata = None
        logger.info("内存图数据库已清空")
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取图数据库统计信息"""
        node_types = {}
        edge_types = {}
        
        for node in self.storage.nodes.values():
            node_types[node.type] = node_types.get(node.type, 0) + 1
        
        for edge in self.storage.edges.values():
            edge_types[edge.type] = edge_types.get(edge.type, 0) + 1
        
        return {
            "name": self.name,
            "node_count": len(self.storage.nodes),
            "edge_count": len(self.storage.edges),
            "node_types": node_types,
            "edge_types": edge_types,
            "is_connected": self._is_connected
        }