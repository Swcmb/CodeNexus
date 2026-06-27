"""
图查询服务

提供复杂的图查询功能，包括路径查询、影响分析、图遍历和模式匹配。
"""

from typing import Dict, List, Optional, Any, Set, Tuple, Union
from collections import deque, defaultdict
from dataclasses import dataclass
import heapq

from ..models.core import CodeGraph, GraphNode, GraphEdge
from ..utils.logger import parser_logger


@dataclass
class QueryResult:
    """查询结果数据类"""
    nodes: List[GraphNode]
    edges: List[GraphEdge]
    paths: List[List[str]] = None
    metadata: Dict[str, Any] = None


@dataclass
class PathResult:
    """路径查询结果"""
    path: List[str]  # 节点ID列表
    length: int
    total_weight: float
    edges: List[GraphEdge]


class GraphQueryService:
    """图查询服务类"""
    
    def __init__(self, database, cache_service=None):
        """
        初始化查询服务
        
        Args:
            database: 图数据库实例（GraphDatabase或MockGraphDatabase）
            cache_service: 缓存服务实例（可选）
        """
        self.database = database
        self.cache_service = cache_service
        self.cache_strategy = None
        if cache_service:
            # 延迟导入避免循环依赖
            try:
                from ..services.cache_service import SmartCacheStrategy
                self.cache_strategy = SmartCacheStrategy(cache_service)
            except ImportError:
                parser_logger.warning("无法导入SmartCacheStrategy，缓存功能将被禁用")
        parser_logger.info("初始化图查询服务")
    
    def find_shortest_path(self, graph_id: str, source_id: str, target_id: str,
                          edge_types: Optional[List[str]] = None,
                          max_depth: int = 10) -> Optional[PathResult]:
        """
        查找两个节点之间的最短路径
        
        Args:
            graph_id: 图谱ID
            source_id: 源节点ID
            target_id: 目标节点ID
            edge_types: 允许的边类型列表，None表示所有类型
            max_depth: 最大搜索深度
            
        Returns:
            路径结果，如果不存在路径则返回None
        """
        parser_logger.info(f"查找从 {source_id} 到 {target_id} 的最短路径")
        
        # 尝试从缓存获取结果
        if self.cache_service:
            # 延迟导入避免循环依赖
            try:
                from ..services.cache_service import CacheService
                cache_key = CacheService.generate_cache_key(
                    "path_query", graph_id, source_id, target_id, 
                    edge_types=edge_types, max_depth=max_depth
                )
                cached_result = self.cache_service.get(cache_key)
                if cached_result:
                    parser_logger.debug("从缓存返回路径查询结果")
                    return PathResult(**cached_result) if cached_result else None
            except ImportError:
                parser_logger.warning("无法导入CacheService，跳过缓存查询")
        
        # 获取图谱
        graph = self.database.retrieve_graph(graph_id)
        if not graph:
            return None
        
        # 构建邻接表
        adjacency = self._build_adjacency_list(graph, edge_types)
        
        # 使用BFS查找最短路径
        queue = deque([(source_id, [source_id], 0.0, [])])
        visited = {source_id}
        
        while queue:
            current_id, path, total_weight, path_edges = queue.popleft()
            
            if len(path) > max_depth:
                continue
            
            if current_id == target_id:
                result = PathResult(
                    path=path,
                    length=len(path) - 1,
                    total_weight=total_weight,
                    edges=path_edges
                )
                
                # 缓存结果
                if self.cache_service and self.cache_strategy:
                    ttl = self.cache_strategy.get_ttl("path_query", len(path))
                    self.cache_service.set(cache_key, result.__dict__, ttl)
                
                return result
            
            for neighbor_id, edge in adjacency.get(current_id, []):
                if neighbor_id not in visited:
                    visited.add(neighbor_id)
                    new_path = path + [neighbor_id]
                    new_weight = total_weight + edge.properties.get('strength', 1.0)
                    new_edges = path_edges + [edge]
                    
                    queue.append((neighbor_id, new_path, new_weight, new_edges))
        
        # 缓存空结果
        if self.cache_service:
            self.cache_service.set(cache_key, None, 300)  # 5分钟TTL
        
        return None
    
    def find_all_paths(self, graph_id: str, source_id: str, target_id: str,
                      edge_types: Optional[List[str]] = None,
                      max_depth: int = 5,
                      max_paths: int = 10) -> List[PathResult]:
        """
        查找两个节点之间的所有路径
        
        Args:
            graph_id: 图谱ID
            source_id: 源节点ID
            target_id: 目标节点ID
            edge_types: 允许的边类型列表
            max_depth: 最大搜索深度
            max_paths: 最大返回路径数
            
        Returns:
            路径结果列表
        """
        parser_logger.info(f"查找从 {source_id} 到 {target_id} 的所有路径")
        
        graph = self.database.retrieve_graph(graph_id)
        if not graph:
            return []
        
        adjacency = self._build_adjacency_list(graph, edge_types)
        paths = []
        
        def dfs(current_id: str, path: List[str], total_weight: float, 
                path_edges: List[GraphEdge], visited: Set[str]):
            if len(paths) >= max_paths or len(path) > max_depth:
                return
            
            if current_id == target_id:
                paths.append(PathResult(
                    path=path.copy(),
                    length=len(path) - 1,
                    total_weight=total_weight,
                    edges=path_edges.copy()
                ))
                return
            
            for neighbor_id, edge in adjacency.get(current_id, []):
                if neighbor_id not in visited:
                    visited.add(neighbor_id)
                    path.append(neighbor_id)
                    path_edges.append(edge)
                    
                    dfs(neighbor_id, path, 
                        total_weight + edge.properties.get('strength', 1.0),
                        path_edges, visited)
                    
                    path.pop()
                    path_edges.pop()
                    visited.remove(neighbor_id)
        
        dfs(source_id, [source_id], 0.0, [], {source_id})
        
        # 按路径长度排序
        paths.sort(key=lambda p: (p.length, p.total_weight))
        return paths[:max_paths]
    
    def analyze_impact(self, graph_id: str, changed_node_ids: List[str],
                      direction: str = "downstream",
                      max_depth: int = 5,
                      edge_types: Optional[List[str]] = None) -> QueryResult:
        """
        分析代码变更的影响范围
        
        Args:
            graph_id: 图谱ID
            changed_node_ids: 发生变更的节点ID列表
            direction: 影响方向，"downstream"（下游）、"upstream"（上游）或"both"（双向）
            max_depth: 最大分析深度
            edge_types: 考虑的边类型列表
            
        Returns:
            影响分析结果
        """
        parser_logger.info(f"分析节点 {changed_node_ids} 的影响范围")
        
        # 尝试从缓存获取结果
        if self.cache_service:
            # 延迟导入避免循环依赖
            try:
                from ..services.cache_service import CacheService
                cache_key = CacheService.generate_cache_key(
                    "impact_analysis", graph_id, changed_node_ids,
                    direction=direction, max_depth=max_depth, edge_types=edge_types
                )
                cached_result = self.cache_service.get(cache_key)
                if cached_result:
                    parser_logger.debug("从缓存返回影响分析结果")
                    # 重构QueryResult对象
                    return QueryResult(
                        nodes=[GraphNode(**node) for node in cached_result.get("nodes", [])],
                        edges=[GraphEdge(**edge) for edge in cached_result.get("edges", [])],
                        paths=cached_result.get("paths"),
                        metadata=cached_result.get("metadata")
                    )
            except ImportError:
                parser_logger.warning("无法导入CacheService，跳过缓存查询")
        graph = self.database.retrieve_graph(graph_id)
        if not graph:
            return QueryResult(nodes=[], edges=[])
        
        # 构建邻接表
        adjacency = self._build_adjacency_list(graph, edge_types)
        reverse_adjacency = self._build_reverse_adjacency_list(graph, edge_types)
        
        affected_nodes = set()
        affected_edges = []
        
        # 根据方向选择搜索策略
        if direction in ("downstream", "both"):
            downstream_nodes, downstream_edges = self._traverse_graph(
                changed_node_ids, adjacency, max_depth
            )
            affected_nodes.update(downstream_nodes)
            affected_edges.extend(downstream_edges)
        
        if direction in ("upstream", "both"):
            upstream_nodes, upstream_edges = self._traverse_graph(
                changed_node_ids, reverse_adjacency, max_depth
            )
            affected_nodes.update(upstream_nodes)
            affected_edges.extend(upstream_edges)
        
        # 获取受影响的节点对象
        node_map = {node.id: node for node in graph.nodes}
        result_nodes = [node_map[node_id] for node_id in affected_nodes 
                       if node_id in node_map]
        
        # 去重边
        unique_edges = []
        seen_edge_ids = set()
        for edge in affected_edges:
            if edge.id not in seen_edge_ids:
                unique_edges.append(edge)
                seen_edge_ids.add(edge.id)
        
        result = QueryResult(
            nodes=result_nodes,
            edges=unique_edges,
            metadata={
                "changed_nodes": changed_node_ids,
                "direction": direction,
                "max_depth": max_depth,
                "total_affected": len(result_nodes)
            }
        )
        
        # 缓存结果
        if self.cache_service and self.cache_strategy:
            if self.cache_strategy.should_cache("impact_analysis", result):
                ttl = self.cache_strategy.get_ttl("impact_analysis", len(result_nodes))
                # 序列化结果用于缓存
                cache_data = {
                    "nodes": [node.__dict__ for node in result_nodes],
                    "edges": [edge.__dict__ for edge in unique_edges],
                    "paths": result.paths,
                    "metadata": result.metadata
                }
                self.cache_service.set(cache_key, cache_data, ttl)
        
        return result
    
    def find_cycles(self, graph_id: str, max_cycle_length: int = 10) -> List[List[str]]:
        """
        查找图中的循环依赖
        
        Args:
            graph_id: 图谱ID
            max_cycle_length: 最大循环长度
            
        Returns:
            循环路径列表
        """
        parser_logger.info("查找图中的循环依赖")
        
        graph = self.database.retrieve_graph(graph_id)
        if not graph:
            return []
        
        adjacency = self._build_adjacency_list(graph)
        cycles = []
        visited = set()
        rec_stack = set()
        
        def dfs_cycle(node_id: str, path: List[str]):
            if len(path) > max_cycle_length:
                return
            
            visited.add(node_id)
            rec_stack.add(node_id)
            path.append(node_id)
            
            for neighbor_id, _ in adjacency.get(node_id, []):
                if neighbor_id in path:
                    # 找到循环
                    cycle_start = path.index(neighbor_id)
                    cycle = path[cycle_start:] + [neighbor_id]
                    if len(cycle) > 2:  # 至少3个节点的循环
                        cycles.append(cycle)
                elif neighbor_id not in visited:
                    dfs_cycle(neighbor_id, path)
            
            path.pop()
            rec_stack.remove(node_id)
        
        # 对每个未访问的节点进行DFS
        for node in graph.nodes:
            if node.id not in visited:
                dfs_cycle(node.id, [])
        
        # 去重循环（相同的循环可能从不同起点发现）
        unique_cycles = []
        seen_cycles = set()
        
        for cycle in cycles:
            # 标准化循环表示（从最小节点ID开始）
            min_idx = cycle.index(min(cycle[:-1]))  # 排除最后一个重复节点
            normalized = cycle[min_idx:-1] + cycle[:min_idx] + [cycle[min_idx]]
            cycle_key = tuple(normalized)
            
            if cycle_key not in seen_cycles:
                seen_cycles.add(cycle_key)
                unique_cycles.append(normalized)
        
        return unique_cycles
    
    def find_strongly_connected_components(self, graph_id: str) -> List[List[str]]:
        """
        查找强连通分量
        
        Args:
            graph_id: 图谱ID
            
        Returns:
            强连通分量列表
        """
        parser_logger.info("查找强连通分量")
        
        graph = self.database.retrieve_graph(graph_id)
        if not graph:
            return []
        
        adjacency = self._build_adjacency_list(graph)
        
        # Tarjan算法查找强连通分量
        index_counter = [0]
        stack = []
        lowlinks = {}
        index = {}
        on_stack = {}
        components = []
        
        def strongconnect(node_id: str):
            index[node_id] = index_counter[0]
            lowlinks[node_id] = index_counter[0]
            index_counter[0] += 1
            stack.append(node_id)
            on_stack[node_id] = True
            
            for neighbor_id, _ in adjacency.get(node_id, []):
                if neighbor_id not in index:
                    strongconnect(neighbor_id)
                    lowlinks[node_id] = min(lowlinks[node_id], lowlinks[neighbor_id])
                elif on_stack.get(neighbor_id, False):
                    lowlinks[node_id] = min(lowlinks[node_id], index[neighbor_id])
            
            if lowlinks[node_id] == index[node_id]:
                component = []
                while True:
                    w = stack.pop()
                    on_stack[w] = False
                    component.append(w)
                    if w == node_id:
                        break
                components.append(component)
        
        for node in graph.nodes:
            if node.id not in index:
                strongconnect(node.id)
        
        # 只返回包含多个节点的强连通分量
        return [comp for comp in components if len(comp) > 1]
    
    def pattern_match(self, graph_id: str, pattern: Dict[str, Any]) -> List[QueryResult]:
        """
        模式匹配查询
        
        Args:
            graph_id: 图谱ID
            pattern: 查询模式，包含节点和边的约束条件
            
        Returns:
            匹配结果列表
        """
        parser_logger.info("执行模式匹配查询")
        
        graph = self.database.retrieve_graph(graph_id)
        if not graph:
            return []
        
        # 简化的模式匹配实现
        # 实际应用中可以实现更复杂的模式匹配算法
        
        node_constraints = pattern.get("nodes", {})
        edge_constraints = pattern.get("edges", {})
        
        matching_results = []
        
        # 查找匹配的节点
        candidate_nodes = []
        for node in graph.nodes:
            if self._node_matches_constraints(node, node_constraints):
                candidate_nodes.append(node)
        
        # 查找匹配的边
        candidate_edges = []
        for edge in graph.edges:
            if self._edge_matches_constraints(edge, edge_constraints):
                candidate_edges.append(edge)
        
        # 构建匹配结果
        if candidate_nodes or candidate_edges:
            matching_results.append(QueryResult(
                nodes=candidate_nodes,
                edges=candidate_edges,
                metadata={"pattern": pattern, "matches": len(candidate_nodes)}
            ))
        
        return matching_results
    
    def get_node_neighbors(self, graph_id: str, node_id: str, 
                          direction: str = "both",
                          edge_types: Optional[List[str]] = None,
                          depth: int = 1) -> QueryResult:
        """
        获取节点的邻居
        
        Args:
            graph_id: 图谱ID
            node_id: 节点ID
            direction: 方向，"in"（入邻居）、"out"（出邻居）或"both"（双向）
            edge_types: 边类型过滤
            depth: 邻居深度
            
        Returns:
            邻居查询结果
        """
        graph = self.database.retrieve_graph(graph_id)
        if not graph:
            return QueryResult(nodes=[], edges=[])
        
        adjacency = self._build_adjacency_list(graph, edge_types)
        reverse_adjacency = self._build_reverse_adjacency_list(graph, edge_types)
        
        visited_nodes = set()
        result_edges = []
        
        # BFS遍历指定深度的邻居
        queue = deque([(node_id, 0)])
        visited_nodes.add(node_id)
        
        while queue:
            current_id, current_depth = queue.popleft()
            
            if current_depth >= depth:
                continue
            
            # 出邻居
            if direction in ("out", "both"):
                for neighbor_id, edge in adjacency.get(current_id, []):
                    result_edges.append(edge)
                    if neighbor_id not in visited_nodes:
                        visited_nodes.add(neighbor_id)
                        queue.append((neighbor_id, current_depth + 1))
            
            # 入邻居
            if direction in ("in", "both"):
                for neighbor_id, edge in reverse_adjacency.get(current_id, []):
                    result_edges.append(edge)
                    if neighbor_id not in visited_nodes:
                        visited_nodes.add(neighbor_id)
                        queue.append((neighbor_id, current_depth + 1))
        
        # 获取节点对象
        node_map = {node.id: node for node in graph.nodes}
        result_nodes = [node_map[node_id] for node_id in visited_nodes 
                       if node_id in node_map]
        
        return QueryResult(
            nodes=result_nodes,
            edges=result_edges,
            metadata={
                "center_node": node_id,
                "direction": direction,
                "depth": depth,
                "neighbor_count": len(result_nodes) - 1  # 排除中心节点
            }
        )
    
    def _build_adjacency_list(self, graph: CodeGraph, 
                             edge_types: Optional[List[str]] = None) -> Dict[str, List[Tuple[str, GraphEdge]]]:
        """构建邻接表"""
        adjacency = defaultdict(list)
        
        for edge in graph.edges:
            if edge_types is None or edge.type in edge_types:
                adjacency[edge.source_id].append((edge.target_id, edge))
        
        return adjacency
    
    def _build_reverse_adjacency_list(self, graph: CodeGraph,
                                     edge_types: Optional[List[str]] = None) -> Dict[str, List[Tuple[str, GraphEdge]]]:
        """构建反向邻接表"""
        reverse_adjacency = defaultdict(list)
        
        for edge in graph.edges:
            if edge_types is None or edge.type in edge_types:
                reverse_adjacency[edge.target_id].append((edge.source_id, edge))
        
        return reverse_adjacency
    
    def _traverse_graph(self, start_nodes: List[str], 
                       adjacency: Dict[str, List[Tuple[str, GraphEdge]]],
                       max_depth: int) -> Tuple[Set[str], List[GraphEdge]]:
        """图遍历"""
        visited_nodes = set(start_nodes)
        visited_edges = []
        
        queue = deque([(node_id, 0) for node_id in start_nodes])
        
        while queue:
            current_id, depth = queue.popleft()
            
            if depth >= max_depth:
                continue
            
            for neighbor_id, edge in adjacency.get(current_id, []):
                visited_edges.append(edge)
                if neighbor_id not in visited_nodes:
                    visited_nodes.add(neighbor_id)
                    queue.append((neighbor_id, depth + 1))
        
        return visited_nodes, visited_edges
    
    def _node_matches_constraints(self, node: GraphNode, constraints: Dict[str, Any]) -> bool:
        """检查节点是否匹配约束条件"""
        for key, value in constraints.items():
            if key == "type" and node.type != value:
                return False
            elif key == "label" and node.label != value:
                return False
            elif key in node.properties and node.properties[key] != value:
                return False
        
        return True
    
    def _edge_matches_constraints(self, edge: GraphEdge, constraints: Dict[str, Any]) -> bool:
        """检查边是否匹配约束条件"""
        for key, value in constraints.items():
            if key == "type" and edge.type != value:
                return False
            elif key in edge.properties and edge.properties[key] != value:
                return False
        
        return True