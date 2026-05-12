"""
图构建器

将代码解析结果转换为图结构数据。
"""

from typing import Dict, List, Optional, Set, Tuple
from collections import defaultdict
import uuid

from ..models.core import (
    CodeElement, ElementType, ParseResult, Relationship, RelationType,
    CodeGraph, GraphNode, GraphEdge, GraphMetadata
)
from ..utils.logger import parser_logger


class GraphBuilder:
    """图构建器类"""
    
    def __init__(self):
        """初始化图构建器"""
        self.node_cache: Dict[str, GraphNode] = {}
        self.edge_cache: Dict[str, GraphEdge] = {}
        self.element_to_node: Dict[str, str] = {}  # element_id -> node_id
        self.parse_results: List[ParseResult] = []
    
    def add_parse_result(self, parse_result: ParseResult) -> None:
        """
        添加解析结果
        
        Args:
            parse_result: 解析结果对象
        """
        self.parse_results.append(parse_result)
    
    def build_from_added_results(self) -> CodeGraph:
        """
        从已添加的解析结果构建图谱
        
        Returns:
            构建的代码图谱
        """
        return self.build_graph(self.parse_results)
        
    def build_graph(self, parse_results: List[ParseResult]) -> CodeGraph:
        """
        构建代码知识图谱
        
        Args:
            parse_results: 解析结果列表
            
        Returns:
            构建的代码图谱
        """
        parser_logger.info(f"开始构建图谱，包含 {len(parse_results)} 个解析结果")
        
        # 清空缓存
        self.node_cache.clear()
        self.edge_cache.clear()
        self.element_to_node.clear()
        
        # 收集所有元素和关系
        all_elements = []
        all_relationships = []
        
        for result in parse_results:
            if result.parse_result:
                all_elements.extend(result.parse_result.elements)
                all_relationships.extend(result.parse_result.relationships)
        
        # 创建节点
        nodes = self.create_nodes(all_elements)
        
        # 创建边
        edges = self.create_edges(all_relationships)
        
        # 创建图谱元数据
        metadata = self._create_graph_metadata(parse_results, nodes, edges)
        
        # 构建图谱
        graph = CodeGraph(
            nodes=nodes,
            edges=edges,
            metadata=metadata
        )
        
        # 优化图谱
        optimized_graph = self.optimize_graph(graph)
        
        parser_logger.info(f"图谱构建完成，包含 {len(optimized_graph.nodes)} 个节点，{len(optimized_graph.edges)} 条边")
        return optimized_graph
    
    def create_nodes(self, elements: List[CodeElement]) -> List[GraphNode]:
        """
        创建图节点
        
        Args:
            elements: 代码元素列表
            
        Returns:
            图节点列表
        """
        nodes = []
        
        for element in elements:
            node = self._create_node_from_element(element)
            nodes.append(node)
            
            # 缓存节点
            self.node_cache[node.id] = node
            self.element_to_node[element.id] = node.id
        
        parser_logger.info(f"创建了 {len(nodes)} 个图节点")
        return nodes
    
    def create_edges(self, relationships: List[Relationship]) -> List[GraphEdge]:
        """
        创建图边
        
        Args:
            relationships: 关系列表
            
        Returns:
            图边列表
        """
        edges = []
        
        for relationship in relationships:
            edge = self._create_edge_from_relationship(relationship)
            if edge:
                edges.append(edge)
                self.edge_cache[edge.id] = edge
        
        parser_logger.info(f"创建了 {len(edges)} 条图边")
        return edges
    
    def optimize_graph(self, graph: CodeGraph) -> CodeGraph:
        """
        优化图结构
        
        Args:
            graph: 原始图谱
            
        Returns:
            优化后的图谱
        """
        parser_logger.info("开始优化图谱结构")
        
        # 使用专门的图优化器
        from .graph_optimizer import GraphOptimizer
        optimizer = GraphOptimizer()
        
        # 应用基础优化
        optimized_graph = optimizer.optimize_graph(graph, {
            'remove_duplicates': True,
            'merge_similar_nodes': False,  # 保守的合并策略
            'remove_isolated_nodes': False,  # 默认保留孤立节点
            'optimize_edges': True,
            'compress_chains': False  # 默认不压缩链
        })
        
        parser_logger.info(f"图谱优化完成，节点数: {len(optimized_graph.nodes)}, 边数: {len(optimized_graph.edges)}")
        return optimized_graph
    
    def _create_node_from_element(self, element: CodeElement) -> GraphNode:
        """从代码元素创建图节点"""
        node_id = f"node_{uuid.uuid4().hex[:8]}"
        
        # 计算节点属性
        properties = {
            "element_id": element.id,
            "name": element.name,
            "type": element.type.value,
            "file_path": element.file_path,
            "line_number": element.line_number,
            "complexity": element.complexity,
            "visibility": element.visibility,
            "is_abstract": element.is_abstract,
            "is_static": element.is_static
        }
        
        # 添加元数据
        properties.update(element.metadata)
        
        return GraphNode(
            id=node_id,
            label=element.name,
            type=element.type.value,
            properties=properties
        )
    
    def _create_edge_from_relationship(self, relationship: Relationship) -> Optional[GraphEdge]:
        """从关系创建图边"""
        # 查找源节点和目标节点
        source_node_id = self.element_to_node.get(relationship.source_id)
        target_node_id = self.element_to_node.get(relationship.target_id)
        
        if not source_node_id or not target_node_id:
            # 如果找不到对应的节点，跳过这条边
            return None
        
        edge_id = f"edge_{uuid.uuid4().hex[:8]}"
        
        # 计算边属性
        properties = {
            "relationship_id": relationship.id,
            "type": relationship.type.value,
            "line_number": relationship.line_number,
            "context": relationship.context,
            "strength": self._calculate_relationship_strength(relationship)
        }
        
        # 添加元数据
        properties.update(relationship.metadata)
        
        return GraphEdge(
            id=edge_id,
            source_id=source_node_id,
            target_id=target_node_id,
            type=relationship.type.value,
            properties=properties
        )
    
    def _calculate_relationship_strength(self, relationship: Relationship) -> float:
        """计算关系强度"""
        # 基于关系类型设置基础强度
        base_strength = {
            RelationType.INHERITS: 0.9,
            RelationType.IMPLEMENTS: 0.8,
            RelationType.CALLS: 0.6,
            RelationType.DEPENDS: 0.5,
            RelationType.COMPOSES: 0.7,
            RelationType.IMPORTS: 0.4
        }.get(relationship.type, 0.5)
        
        # 根据上下文调整强度
        if relationship.context and len(relationship.context) > 50:
            base_strength += 0.1  # 详细上下文增加强度
        
        # 根据元数据调整强度
        if "call_count" in relationship.metadata:
            call_count = relationship.metadata["call_count"]
            if call_count > 10:
                base_strength += 0.2
            elif call_count > 5:
                base_strength += 0.1
        
        return min(1.0, base_strength)
    
    def _create_graph_metadata(
        self, 
        parse_results: List[ParseResult], 
        nodes: List[GraphNode], 
        edges: List[GraphEdge]
    ) -> GraphMetadata:
        """创建图谱元数据"""
        # 统计文件信息
        files = set()
        languages = set()
        
        for result in parse_results:
            if hasattr(result, 'file_path'):
                files.add(result.file_path)
                # 从文件扩展名推断语言
                if result.file_path.endswith('.py'):
                    languages.add('Python')
                elif result.file_path.endswith('.java'):
                    languages.add('Java')
                elif result.file_path.endswith('.js'):
                    languages.add('JavaScript')
                elif result.file_path.endswith('.cs'):
                    languages.add('C#')
        
        # 统计节点类型
        node_types = defaultdict(int)
        for node in nodes:
            node_types[node.type] += 1
        
        # 统计边类型
        edge_types = defaultdict(int)
        for edge in edges:
            edge_types[edge.type] += 1
        
        return GraphMetadata(
            node_count=len(nodes),
            edge_count=len(edges),
            file_count=len(files),
            languages=list(languages),
            node_types=dict(node_types),
            edge_types=dict(edge_types),
            creation_time=None,  # 将在GraphMetadata中设置
            version="1.0"
        )
    
    def _deduplicate_nodes(self, nodes: List[GraphNode]) -> List[GraphNode]:
        """去重节点"""
        seen = set()
        unique_nodes = []
        
        for node in nodes:
            # 基于名称、类型和文件路径创建唯一标识
            key = (
                node.properties.get("name"),
                node.properties.get("type"),
                node.properties.get("file_path")
            )
            
            if key not in seen:
                seen.add(key)
                unique_nodes.append(node)
        
        return unique_nodes
    
    def _deduplicate_edges(self, edges: List[GraphEdge]) -> List[GraphEdge]:
        """去重边"""
        seen = set()
        unique_edges = []
        
        for edge in edges:
            # 基于源节点、目标节点和关系类型创建唯一标识
            key = (edge.source_id, edge.target_id, edge.type)
            
            if key not in seen:
                seen.add(key)
                unique_edges.append(edge)
        
        return unique_edges
    
    def _remove_isolated_nodes(
        self, 
        nodes: List[GraphNode], 
        edges: List[GraphEdge],
        remove_isolated: bool = True
    ) -> List[GraphNode]:
        """移除孤立节点（没有任何连接的节点）"""
        if not remove_isolated:
            return nodes
            
        # 收集所有连接的节点ID
        connected_node_ids = set()
        for edge in edges:
            connected_node_ids.add(edge.source_id)
            connected_node_ids.add(edge.target_id)
        
        # 保留连接的节点
        connected_nodes = [
            node for node in nodes 
            if node.id in connected_node_ids
        ]
        
        removed_count = len(nodes) - len(connected_nodes)
        if removed_count > 0:
            parser_logger.info(f"移除了 {removed_count} 个孤立节点")
        
        return connected_nodes
    
    def _merge_similar_nodes(
        self, 
        nodes: List[GraphNode], 
        edges: List[GraphEdge]
    ) -> Tuple[List[GraphNode], List[GraphEdge]]:
        """合并相似节点（可选的高级优化）"""
        # 目前简单返回原始数据，可以在后续版本中实现更复杂的合并逻辑
        return nodes, edges
    
    def get_node_by_element_id(self, element_id: str) -> Optional[GraphNode]:
        """根据元素ID获取对应的图节点"""
        node_id = self.element_to_node.get(element_id)
        if node_id:
            return self.node_cache.get(node_id)
        return None
    
    def get_connected_nodes(self, node_id: str, edges: List[GraphEdge]) -> List[str]:
        """获取与指定节点连接的所有节点ID"""
        connected = set()
        
        for edge in edges:
            if edge.source_id == node_id:
                connected.add(edge.target_id)
            elif edge.target_id == node_id:
                connected.add(edge.source_id)
        
        return list(connected)
    
    def calculate_node_metrics(self, node_id: str, edges: List[GraphEdge]) -> Dict[str, int]:
        """计算节点的图谱指标"""
        in_degree = 0
        out_degree = 0
        
        for edge in edges:
            if edge.target_id == node_id:
                in_degree += 1
            elif edge.source_id == node_id:
                out_degree += 1
        
        return {
            "in_degree": in_degree,
            "out_degree": out_degree,
            "total_degree": in_degree + out_degree
        }