"""
内存优化的图构建器

针对大型项目优化内存使用，支持增量构建和内存管理。
"""

import gc
import logging
from typing import Dict, List, Optional, Iterator, Tuple
from collections import defaultdict
import weakref
import uuid

from ..models.core import (
    CodeElement, ElementType, ParseResult, Relationship, RelationType,
    CodeGraph, GraphNode, GraphEdge, GraphMetadata
)
from ..utils.logger import parser_logger
from .graph_builder import GraphBuilder


logger = logging.getLogger(__name__)


class MemoryOptimizedGraphBuilder(GraphBuilder):
    """内存优化的图构建器
    
    通过增量构建、弱引用和内存管理优化大型项目的图构建过程。
    """
    
    def __init__(self, memory_limit_mb: int = 1024):
        """初始化内存优化图构建器
        
        Args:
            memory_limit_mb: 内存限制（MB）
        """
        super().__init__()
        self.memory_limit_mb = memory_limit_mb
        self._weak_node_cache = weakref.WeakValueDictionary()
        self._weak_edge_cache = weakref.WeakValueDictionary()
        self._build_stats = {
            "nodes_created": 0,
            "edges_created": 0,
            "gc_triggered": 0,
            "memory_optimizations": 0
        }
    
    def build_graph_incremental(
        self, 
        parse_results: Iterator[ParseResult],
        chunk_size: int = 100
    ) -> CodeGraph:
        """增量构建图谱
        
        Args:
            parse_results: 解析结果迭代器
            chunk_size: 每次处理的结果数量
            
        Returns:
            构建的代码图谱
        """
        logger.info("开始增量构建图谱")
        
        # 初始化累积器
        all_nodes = []
        all_edges = []
        processed_count = 0
        
        # 分块处理解析结果
        chunk = []
        for result in parse_results:
            chunk.append(result)
            
            if len(chunk) >= chunk_size:
                nodes, edges = self._process_chunk(chunk)
                all_nodes.extend(nodes)
                all_edges.extend(edges)
                
                processed_count += len(chunk)
                logger.debug(f"已处理 {processed_count} 个解析结果")
                
                # 清空当前块并触发垃圾回收
                chunk.clear()
                self._maybe_trigger_gc()
        
        # 处理剩余的结果
        if chunk:
            nodes, edges = self._process_chunk(chunk)
            all_nodes.extend(nodes)
            all_edges.extend(edges)
            processed_count += len(chunk)
        
        # 创建图谱元数据
        metadata = GraphMetadata(
            node_count=len(all_nodes),
            edge_count=len(all_edges),
            file_count=processed_count,
            languages=[],  # 将在后续填充
            node_types={},
            edge_types={},
            version="1.0"
        )
        
        # 构建最终图谱
        graph = CodeGraph(
            nodes=all_nodes,
            edges=all_edges,
            metadata=metadata
        )
        
        # 应用最终优化
        optimized_graph = self._apply_memory_optimizations(graph)
        
        logger.info(f"增量图谱构建完成，统计: {self._build_stats}")
        return optimized_graph
    
    def _process_chunk(self, parse_results: List[ParseResult]) -> Tuple[List[GraphNode], List[GraphEdge]]:
        """处理一个结果块
        
        Args:
            parse_results: 解析结果列表
            
        Returns:
            节点和边的元组
        """
        # 收集当前块的所有元素和关系
        chunk_elements = []
        chunk_relationships = []
        
        for result in parse_results:
            chunk_elements.extend(result.elements)
            chunk_relationships.extend(result.relationships)
        
        # 创建节点和边
        nodes = self._create_nodes_optimized(chunk_elements)
        edges = self._create_edges_optimized(chunk_relationships)
        
        return nodes, edges
    
    def _create_nodes_optimized(self, elements: List[CodeElement]) -> List[GraphNode]:
        """优化的节点创建
        
        Args:
            elements: 代码元素列表
            
        Returns:
            图节点列表
        """
        nodes = []
        
        for element in elements:
            # 检查是否已存在相似节点
            existing_node = self._find_similar_node(element)
            if existing_node:
                # 合并信息而不是创建新节点
                self._merge_element_info(existing_node, element)
                continue
            
            # 创建新节点
            node = self._create_lightweight_node(element)
            nodes.append(node)
            
            # 使用弱引用缓存
            self._weak_node_cache[node.id] = node
            self.element_to_node[element.id] = node.id
            
            self._build_stats["nodes_created"] += 1
        
        return nodes
    
    def _create_edges_optimized(self, relationships: List[Relationship]) -> List[GraphEdge]:
        """优化的边创建
        
        Args:
            relationships: 关系列表
            
        Returns:
            图边列表
        """
        edges = []
        edge_signatures = set()  # 用于去重
        
        for relationship in relationships:
            # 创建边签名用于去重
            signature = (
                relationship.source_id,
                relationship.target_id,
                relationship.type.value
            )
            
            if signature in edge_signatures:
                continue
            
            edge = self._create_lightweight_edge(relationship)
            if edge:
                edges.append(edge)
                edge_signatures.add(signature)
                
                # 使用弱引用缓存
                self._weak_edge_cache[edge.id] = edge
                
                self._build_stats["edges_created"] += 1
        
        return edges
    
    def _find_similar_node(self, element: CodeElement) -> Optional[GraphNode]:
        """查找相似的现有节点
        
        Args:
            element: 代码元素
            
        Returns:
            相似的节点，如果不存在则返回None
        """
        # 基于名称、类型和文件路径查找相似节点
        for node in self._weak_node_cache.values():
            if (node.properties.get("name") == element.name and
                node.properties.get("type") == element.type.value and
                node.properties.get("file_path") == element.file_path):
                return node
        
        return None
    
    def _merge_element_info(self, node: GraphNode, element: CodeElement):
        """合并元素信息到现有节点
        
        Args:
            node: 现有节点
            element: 新元素
        """
        # 更新复杂度（取最大值）
        current_complexity = node.properties.get("complexity", 0)
        if element.complexity > current_complexity:
            node.properties["complexity"] = element.complexity
        
        # 合并元数据
        if element.metadata:
            node_metadata = node.properties.get("metadata", {})
            node_metadata.update(element.metadata)
            node.properties["metadata"] = node_metadata
    
    def _create_lightweight_node(self, element: CodeElement) -> GraphNode:
        """创建轻量级节点
        
        Args:
            element: 代码元素
            
        Returns:
            轻量级图节点
        """
        node_id = f"node_{uuid.uuid4().hex[:8]}"
        
        # 只保留必要的属性
        essential_properties = {
            "element_id": element.id,
            "name": element.name,
            "type": element.type.value,
            "file_path": element.file_path,
            "line_number": element.line_number,
            "complexity": element.complexity
        }
        
        # 有选择地添加其他属性
        if element.visibility != "public":
            essential_properties["visibility"] = element.visibility
        
        if element.is_abstract:
            essential_properties["is_abstract"] = True
        
        if element.is_static:
            essential_properties["is_static"] = True
        
        return GraphNode(
            id=node_id,
            label=element.name,
            type=element.type.value,
            properties=essential_properties
        )
    
    def _create_lightweight_edge(self, relationship: Relationship) -> Optional[GraphEdge]:
        """创建轻量级边
        
        Args:
            relationship: 关系
            
        Returns:
            轻量级图边
        """
        # 查找源节点和目标节点
        source_node_id = self.element_to_node.get(relationship.source_id)
        target_node_id = self.element_to_node.get(relationship.target_id)
        
        if not source_node_id or not target_node_id:
            return None
        
        edge_id = f"edge_{uuid.uuid4().hex[:8]}"
        
        # 只保留必要的属性
        essential_properties = {
            "type": relationship.type.value,
            "strength": self._calculate_relationship_strength(relationship)
        }
        
        # 有选择地添加其他属性
        if relationship.line_number:
            essential_properties["line_number"] = relationship.line_number
        
        return GraphEdge(
            id=edge_id,
            source_id=source_node_id,
            target_id=target_node_id,
            type=relationship.type.value,
            properties=essential_properties
        )
    
    def _apply_memory_optimizations(self, graph: CodeGraph) -> CodeGraph:
        """应用内存优化
        
        Args:
            graph: 原始图谱
            
        Returns:
            优化后的图谱
        """
        logger.info("应用内存优化")
        
        # 1. 移除重复节点
        unique_nodes = self._deduplicate_nodes_efficient(graph.nodes)
        
        # 2. 移除重复边
        unique_edges = self._deduplicate_edges_efficient(graph.edges)
        
        # 3. 压缩节点属性
        compressed_nodes = self._compress_node_properties(unique_nodes)
        
        # 4. 优化边属性
        optimized_edges = self._optimize_edge_properties(unique_edges)
        
        # 5. 更新元数据
        optimized_metadata = self._create_optimized_metadata(compressed_nodes, optimized_edges)
        
        self._build_stats["memory_optimizations"] += 1
        
        return CodeGraph(
            nodes=compressed_nodes,
            edges=optimized_edges,
            metadata=optimized_metadata
        )
    
    def _deduplicate_nodes_efficient(self, nodes: List[GraphNode]) -> List[GraphNode]:
        """高效的节点去重
        
        Args:
            nodes: 节点列表
            
        Returns:
            去重后的节点列表
        """
        seen_signatures = set()
        unique_nodes = []
        
        for node in nodes:
            # 创建节点签名
            signature = (
                node.properties.get("name"),
                node.properties.get("type"),
                node.properties.get("file_path"),
                node.properties.get("line_number")
            )
            
            if signature not in seen_signatures:
                seen_signatures.add(signature)
                unique_nodes.append(node)
        
        logger.debug(f"节点去重: {len(nodes)} -> {len(unique_nodes)}")
        return unique_nodes
    
    def _deduplicate_edges_efficient(self, edges: List[GraphEdge]) -> List[GraphEdge]:
        """高效的边去重
        
        Args:
            edges: 边列表
            
        Returns:
            去重后的边列表
        """
        seen_signatures = set()
        unique_edges = []
        
        for edge in edges:
            signature = (edge.source_id, edge.target_id, edge.type)
            
            if signature not in seen_signatures:
                seen_signatures.add(signature)
                unique_edges.append(edge)
        
        logger.debug(f"边去重: {len(edges)} -> {len(unique_edges)}")
        return unique_edges
    
    def _compress_node_properties(self, nodes: List[GraphNode]) -> List[GraphNode]:
        """压缩节点属性
        
        Args:
            nodes: 节点列表
            
        Returns:
            压缩后的节点列表
        """
        for node in nodes:
            # 移除空值属性
            node.properties = {
                k: v for k, v in node.properties.items()
                if v is not None and v != "" and v != []
            }
            
            # 压缩字符串属性
            for key, value in node.properties.items():
                if isinstance(value, str) and len(value) > 1000:
                    # 截断过长的字符串
                    node.properties[key] = value[:1000] + "..."
        
        return nodes
    
    def _optimize_edge_properties(self, edges: List[GraphEdge]) -> List[GraphEdge]:
        """优化边属性
        
        Args:
            edges: 边列表
            
        Returns:
            优化后的边列表
        """
        for edge in edges:
            # 移除空值属性
            edge.properties = {
                k: v for k, v in edge.properties.items()
                if v is not None and v != "" and v != []
            }
        
        return edges
    
    def _create_optimized_metadata(
        self, 
        nodes: List[GraphNode], 
        edges: List[GraphEdge]
    ) -> GraphMetadata:
        """创建优化的元数据
        
        Args:
            nodes: 节点列表
            edges: 边列表
            
        Returns:
            优化的图谱元数据
        """
        # 统计节点类型
        node_types = defaultdict(int)
        for node in nodes:
            node_types[node.type] += 1
        
        # 统计边类型
        edge_types = defaultdict(int)
        for edge in edges:
            edge_types[edge.type] += 1
        
        # 统计文件数量
        files = set()
        for node in nodes:
            file_path = node.properties.get("file_path")
            if file_path:
                files.add(file_path)
        
        return GraphMetadata(
            node_count=len(nodes),
            edge_count=len(edges),
            file_count=len(files),
            languages=[],  # 可以从文件扩展名推断
            node_types=dict(node_types),
            edge_types=dict(edge_types),
            version="1.0"
        )
    
    def _maybe_trigger_gc(self):
        """根据内存使用情况触发垃圾回收"""
        import psutil
        
        process = psutil.Process()
        memory_mb = process.memory_info().rss / 1024 / 1024
        
        if memory_mb > self.memory_limit_mb * 0.8:  # 80%阈值
            logger.debug(f"触发垃圾回收，当前内存使用: {memory_mb:.1f}MB")
            gc.collect()
            self._build_stats["gc_triggered"] += 1
    
    def get_build_stats(self) -> Dict[str, int]:
        """获取构建统计信息
        
        Returns:
            构建统计信息
        """
        return self._build_stats.copy()
    
    def clear_caches(self):
        """清空缓存"""
        self._weak_node_cache.clear()
        self._weak_edge_cache.clear()
        self.node_cache.clear()
        self.edge_cache.clear()
        self.element_to_node.clear()
        gc.collect()
        logger.debug("已清空所有缓存")


class GraphStreamBuilder:
    """流式图构建器
    
    用于处理超大型项目，采用流式处理避免内存溢出。
    """
    
    def __init__(self, output_handler: callable):
        """初始化流式图构建器
        
        Args:
            output_handler: 输出处理函数，接收构建的图谱片段
        """
        self.output_handler = output_handler
        self.builder = MemoryOptimizedGraphBuilder()
        self.accumulated_nodes = []
        self.accumulated_edges = []
        self.flush_threshold = 1000  # 累积阈值
    
    def add_parse_result(self, parse_result: ParseResult):
        """添加解析结果
        
        Args:
            parse_result: 解析结果
        """
        # 处理当前结果
        nodes, edges = self.builder._process_chunk([parse_result])
        
        self.accumulated_nodes.extend(nodes)
        self.accumulated_edges.extend(edges)
        
        # 检查是否需要刷新
        if (len(self.accumulated_nodes) >= self.flush_threshold or
            len(self.accumulated_edges) >= self.flush_threshold):
            self._flush_accumulated()
    
    def _flush_accumulated(self):
        """刷新累积的节点和边"""
        if self.accumulated_nodes or self.accumulated_edges:
            # 创建图谱片段
            metadata = GraphMetadata(
                node_count=len(self.accumulated_nodes),
                edge_count=len(self.accumulated_edges),
                file_count=1,  # 片段
                languages=[],
                node_types={},
                edge_types={},
                version="1.0"
            )
            
            graph_fragment = CodeGraph(
                nodes=self.accumulated_nodes.copy(),
                edges=self.accumulated_edges.copy(),
                metadata=metadata
            )
            
            # 输出图谱片段
            self.output_handler(graph_fragment)
            
            # 清空累积器
            self.accumulated_nodes.clear()
            self.accumulated_edges.clear()
            
            # 触发垃圾回收
            gc.collect()
    
    def finalize(self):
        """完成处理"""
        # 刷新剩余的数据
        self._flush_accumulated()
        logger.info("流式图构建完成")