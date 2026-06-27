"""
模拟图数据库实现

用于测试和开发环境，不需要真实的Neo4j数据库。
"""

from typing import Dict, List, Optional, Any
import json
from copy import deepcopy

from ..models.core import CodeGraph, GraphNode, GraphEdge, GraphMetadata
from ..utils.logger import parser_logger


class MockGraphDatabase:
    """模拟图数据库类，用于测试"""
    
    def __init__(self):
        """初始化模拟数据库"""
        self.graphs: Dict[str, CodeGraph] = {}
        self._connected = True
        parser_logger.info("初始化模拟图数据库")
    
    def connect(self) -> None:
        """模拟连接"""
        self._connected = True
        parser_logger.info("模拟数据库连接成功")
    
    def disconnect(self) -> None:
        """模拟断开连接"""
        self._connected = False
        parser_logger.info("模拟数据库连接已断开")
    
    def is_connected(self) -> bool:
        """检查连接状态"""
        return self._connected
    
    def store_graph(self, graph: CodeGraph) -> str:
        """
        存储图谱到模拟数据库
        
        Args:
            graph: 要存储的图谱
            
        Returns:
            图谱ID
        """
        if not self._connected:
            raise Exception("数据库未连接")
        
        # 深拷贝图谱以避免外部修改
        stored_graph = deepcopy(graph)
        self.graphs[graph.id] = stored_graph
        
        parser_logger.info(f"模拟存储图谱 {graph.id}，包含 {len(graph.nodes)} 个节点，{len(graph.edges)} 条边")
        return graph.id
    
    def retrieve_graph(self, graph_id: str) -> Optional[CodeGraph]:
        """
        从模拟数据库检索图谱
        
        Args:
            graph_id: 图谱ID
            
        Returns:
            图谱对象，如果不存在则返回None
        """
        if not self._connected:
            raise Exception("数据库未连接")
        
        if graph_id in self.graphs:
            # 返回深拷贝以避免外部修改
            retrieved_graph = deepcopy(self.graphs[graph_id])
            parser_logger.info(f"模拟检索图谱 {graph_id}")
            return retrieved_graph
        
        parser_logger.warning(f"图谱 {graph_id} 不存在")
        return None
    
    def delete_graph(self, graph_id: str) -> bool:
        """
        删除图谱
        
        Args:
            graph_id: 图谱ID
            
        Returns:
            是否成功删除
        """
        if not self._connected:
            raise Exception("数据库未连接")
        
        if graph_id in self.graphs:
            del self.graphs[graph_id]
            parser_logger.info(f"模拟删除图谱 {graph_id}")
            return True
        
        return False
    
    def query_nodes(self, graph_id: str, node_type: Optional[str] = None,
                   properties: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        查询节点
        
        Args:
            graph_id: 图谱ID
            node_type: 节点类型过滤
            properties: 属性过滤
            
        Returns:
            匹配的节点列表
        """
        if not self._connected:
            raise Exception("数据库未连接")
        
        if graph_id not in self.graphs:
            return []
        
        graph = self.graphs[graph_id]
        matching_nodes = []
        
        for node in graph.nodes:
            # 类型过滤
            if node_type and node.type != node_type:
                continue
            
            # 属性过滤
            if properties:
                match = True
                for key, value in properties.items():
                    if key not in node.properties or node.properties[key] != value:
                        match = False
                        break
                if not match:
                    continue
            
            # 转换为字典格式
            node_dict = {
                "id": node.id,
                "label": node.label,
                "type": node.type,
                "properties": node.properties.copy()
            }
            matching_nodes.append(node_dict)
        
        return matching_nodes
    
    def query_edges(self, graph_id: str, edge_type: Optional[str] = None,
                   source_id: Optional[str] = None, target_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        查询边
        
        Args:
            graph_id: 图谱ID
            edge_type: 边类型过滤
            source_id: 源节点ID过滤
            target_id: 目标节点ID过滤
            
        Returns:
            匹配的边列表
        """
        if not self._connected:
            raise Exception("数据库未连接")
        
        if graph_id not in self.graphs:
            return []
        
        graph = self.graphs[graph_id]
        matching_edges = []
        
        # 创建节点ID到节点的映射
        node_map = {node.id: node for node in graph.nodes}
        
        for edge in graph.edges:
            # 类型过滤
            if edge_type and edge.type != edge_type:
                continue
            
            # 源节点过滤
            if source_id and edge.source_id != source_id:
                continue
            
            # 目标节点过滤
            if target_id and edge.target_id != target_id:
                continue
            
            # 转换为字典格式，包含源节点和目标节点信息
            edge_dict = {
                "id": edge.id,
                "source_id": edge.source_id,
                "target_id": edge.target_id,
                "type": edge.type,
                "properties": edge.properties.copy()
            }
            
            # 添加源节点和目标节点信息
            if edge.source_id in node_map:
                source_node = node_map[edge.source_id]
                edge_dict["source_node"] = {
                    "id": source_node.id,
                    "label": source_node.label,
                    "type": source_node.type,
                    "properties": source_node.properties.copy()
                }
            
            if edge.target_id in node_map:
                target_node = node_map[edge.target_id]
                edge_dict["target_node"] = {
                    "id": target_node.id,
                    "label": target_node.label,
                    "type": target_node.type,
                    "properties": target_node.properties.copy()
                }
            
            matching_edges.append(edge_dict)
        
        return matching_edges
    
    def execute_cypher(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        模拟执行Cypher查询
        
        Args:
            query: Cypher查询语句
            parameters: 查询参数
            
        Returns:
            模拟查询结果
        """
        parser_logger.info(f"模拟执行Cypher查询: {query}")
        
        # 这里只是一个简单的模拟实现
        # 实际应用中可以根据需要实现更复杂的查询逻辑
        
        if "RETURN 1" in query:
            return [{"1": 1}]
        
        if "count(" in query.lower():
            # 模拟计数查询
            total_nodes = sum(len(graph.nodes) for graph in self.graphs.values())
            total_edges = sum(len(graph.edges) for graph in self.graphs.values())
            return [{"count": total_nodes + total_edges}]
        
        # 默认返回空结果
        return []
    
    def get_graph_statistics(self, graph_id: str) -> Dict[str, Any]:
        """
        获取图谱统计信息
        
        Args:
            graph_id: 图谱ID
            
        Returns:
            统计信息字典
        """
        if graph_id not in self.graphs:
            return {
                "node_count": 0,
                "edge_count": 0,
                "node_types": [],
                "edge_types": []
            }
        
        graph = self.graphs[graph_id]
        
        # 统计节点类型
        node_types = list(set(node.type for node in graph.nodes))
        
        # 统计边类型
        edge_types = list(set(edge.type for edge in graph.edges))
        
        return {
            "node_count": len(graph.nodes),
            "edge_count": len(graph.edges),
            "node_types": node_types,
            "edge_types": edge_types
        }
    
    def clear_all(self) -> None:
        """清空所有数据（仅用于测试）"""
        self.graphs.clear()
        parser_logger.info("清空模拟数据库所有数据")
    
    def list_graphs(self) -> List[str]:
        """列出所有图谱ID"""
        return list(self.graphs.keys())
    
    def export_graph(self, graph_id: str) -> Optional[Dict[str, Any]]:
        """
        导出图谱为JSON格式
        
        Args:
            graph_id: 图谱ID
            
        Returns:
            图谱的JSON表示
        """
        if graph_id not in self.graphs:
            return None
        
        graph = self.graphs[graph_id]
        
        return {
            "id": graph.id,
            "nodes": [
                {
                    "id": node.id,
                    "label": node.label,
                    "type": node.type,
                    "properties": node.properties
                }
                for node in graph.nodes
            ],
            "edges": [
                {
                    "id": edge.id,
                    "source_id": edge.source_id,
                    "target_id": edge.target_id,
                    "type": edge.type,
                    "properties": edge.properties
                }
                for edge in graph.edges
            ],
            "metadata": {
                "node_count": graph.metadata.node_count,
                "edge_count": graph.metadata.edge_count,
                "file_count": graph.metadata.file_count,
                "languages": graph.metadata.languages,
                "node_types": graph.metadata.node_types,
                "edge_types": graph.metadata.edge_types,
                "creation_time": graph.metadata.creation_time,
                "version": graph.metadata.version
            }
        }
    
    def import_graph(self, graph_data: Dict[str, Any]) -> str:
        """
        从JSON格式导入图谱
        
        Args:
            graph_data: 图谱的JSON表示
            
        Returns:
            导入的图谱ID
        """
        # 重建节点
        nodes = []
        for node_data in graph_data.get("nodes", []):
            node = GraphNode(
                id=node_data["id"],
                label=node_data["label"],
                type=node_data["type"],
                properties=node_data["properties"]
            )
            nodes.append(node)
        
        # 重建边
        edges = []
        for edge_data in graph_data.get("edges", []):
            edge = GraphEdge(
                id=edge_data["id"],
                source_id=edge_data["source_id"],
                target_id=edge_data["target_id"],
                type=edge_data["type"],
                properties=edge_data["properties"]
            )
            edges.append(edge)
        
        # 重建元数据
        metadata_data = graph_data.get("metadata", {})
        metadata = GraphMetadata(
            node_count=metadata_data.get("node_count", 0),
            edge_count=metadata_data.get("edge_count", 0),
            file_count=metadata_data.get("file_count", 0),
            languages=metadata_data.get("languages", []),
            node_types=metadata_data.get("node_types", {}),
            edge_types=metadata_data.get("edge_types", {}),
            creation_time=metadata_data.get("creation_time"),
            version=metadata_data.get("version", "1.0")
        )
        
        # 创建图谱
        graph = CodeGraph(
            id=graph_data["id"],
            nodes=nodes,
            edges=edges,
            metadata=metadata
        )
        
        # 存储图谱
        return self.store_graph(graph)