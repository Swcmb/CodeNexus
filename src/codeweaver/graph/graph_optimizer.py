"""
图优化器

实现高级的图结构优化算法，包括去重、合并、分割等功能。
"""

from typing import Dict, List, Optional, Set, Tuple, Union
from collections import defaultdict, deque
import copy

from ..models.core import CodeGraph, GraphNode, GraphEdge, GraphMetadata
from ..utils.logger import parser_logger


class GraphOptimizer:
    """图优化器类"""
    
    def __init__(self):
        """初始化图优化器"""
        self.optimization_stats = {
            'nodes_removed': 0,
            'edges_removed': 0,
            'nodes_merged': 0,
            'edges_merged': 0
        }
    
    def optimize_graph(
        self, 
        graph: CodeGraph, 
        options: Optional[Dict[str, bool]] = None
    ) -> CodeGraph:
        """
        全面优化图结构
        
        Args:
            graph: 待优化的图
            options: 优化选项
            
        Returns:
            优化后的图
        """
        if options is None:
            options = {
                'remove_duplicates': True,
                'merge_similar_nodes': True,
                'remove_isolated_nodes': False,
                'optimize_edges': True,
                'compress_chains': True
            }
        
        parser_logger.info(f"开始优化图，原始节点数: {len(graph.nodes)}, 边数: {len(graph.edges)}")
        
        # 重置统计信息
        self.optimization_stats = {
            'nodes_removed': 0,
            'edges_removed': 0,
            'nodes_merged': 0,
            'edges_merged': 0
        }
        
        optimized_graph = copy.deepcopy(graph)
        
        # 执行各种优化步骤
        if options.get('remove_duplicates', True):
            optimized_graph = self.remove_duplicate_nodes_and_edges(optimized_graph)
        
        if options.get('merge_similar_nodes', True):
            optimized_graph = self.merge_similar_nodes(optimized_graph)
        
        if options.get('remove_isolated_nodes', False):
            optimized_graph = self.remove_isolated_nodes(optimized_graph)
        
        if options.get('optimize_edges', True):
            optimized_graph = self.optimize_edges(optimized_graph)
        
        if options.get('compress_chains', True):
            optimized_graph = self.compress_linear_chains(optimized_graph)
        
        # 更新元数据
        optimized_graph.metadata.node_count = len(optimized_graph.nodes)
        optimized_graph.metadata.edge_count = len(optimized_graph.edges)
        
        parser_logger.info(
            f"图优化完成，优化后节点数: {len(optimized_graph.nodes)}, 边数: {len(optimized_graph.edges)}"
        )
        parser_logger.info(f"优化统计: {self.optimization_stats}")
        
        return optimized_graph
    
    def remove_duplicate_nodes_and_edges(self, graph: CodeGraph) -> CodeGraph:
        """移除重复的节点和边"""
        # 移除重复节点
        unique_nodes = []
        seen_node_signatures = set()
        node_id_mapping = {}  # 旧ID -> 新ID的映射
        
        for node in graph.nodes:
            # 创建节点签名用于去重
            signature = self._create_node_signature(node)
            
            if signature not in seen_node_signatures:
                seen_node_signatures.add(signature)
                unique_nodes.append(node)
                node_id_mapping[node.id] = node.id
            else:
                # 找到重复节点，记录ID映射
                for existing_node in unique_nodes:
                    if self._create_node_signature(existing_node) == signature:
                        node_id_mapping[node.id] = existing_node.id
                        self.optimization_stats['nodes_removed'] += 1
                        break
        
        # 移除重复边并更新节点引用
        unique_edges = []
        seen_edge_signatures = set()
        
        for edge in graph.edges:
            # 更新边的节点引用
            new_source_id = node_id_mapping.get(edge.source_id, edge.source_id)
            new_target_id = node_id_mapping.get(edge.target_id, edge.target_id)
            
            # 创建边签名用于去重
            signature = (new_source_id, new_target_id, edge.type)
            
            if signature not in seen_edge_signatures:
                seen_edge_signatures.add(signature)
                # 更新边的节点引用
                edge.source_id = new_source_id
                edge.target_id = new_target_id
                unique_edges.append(edge)
            else:
                self.optimization_stats['edges_removed'] += 1
        
        return CodeGraph(
            id=graph.id,
            nodes=unique_nodes,
            edges=unique_edges,
            metadata=graph.metadata
        )
    
    def merge_similar_nodes(self, graph: CodeGraph) -> CodeGraph:
        """合并相似的节点"""
        # 按相似性分组节点
        similarity_groups = self._group_nodes_by_similarity(graph.nodes)
        
        merged_nodes = []
        node_id_mapping = {}
        
        for group in similarity_groups:
            if len(group) > 1:
                # 合并组内节点
                merged_node = self._merge_node_group(group)
                merged_nodes.append(merged_node)
                
                # 记录ID映射
                for node in group:
                    node_id_mapping[node.id] = merged_node.id
                    if node.id != merged_node.id:
                        self.optimization_stats['nodes_merged'] += 1
            else:
                # 单个节点直接保留
                merged_nodes.append(group[0])
                node_id_mapping[group[0].id] = group[0].id
        
        # 更新边的节点引用
        updated_edges = []
        for edge in graph.edges:
            new_source_id = node_id_mapping.get(edge.source_id, edge.source_id)
            new_target_id = node_id_mapping.get(edge.target_id, edge.target_id)
            
            # 避免自环（除非原本就是自环）
            if new_source_id != new_target_id or edge.source_id == edge.target_id:
                edge.source_id = new_source_id
                edge.target_id = new_target_id
                updated_edges.append(edge)
            else:
                self.optimization_stats['edges_removed'] += 1
        
        return CodeGraph(
            id=graph.id,
            nodes=merged_nodes,
            edges=updated_edges,
            metadata=graph.metadata
        )
    
    def remove_isolated_nodes(self, graph: CodeGraph) -> CodeGraph:
        """移除孤立节点"""
        # 收集所有连接的节点ID
        connected_node_ids = set()
        for edge in graph.edges:
            connected_node_ids.add(edge.source_id)
            connected_node_ids.add(edge.target_id)
        
        # 保留连接的节点
        connected_nodes = []
        for node in graph.nodes:
            if node.id in connected_node_ids:
                connected_nodes.append(node)
            else:
                self.optimization_stats['nodes_removed'] += 1
        
        return CodeGraph(
            id=graph.id,
            nodes=connected_nodes,
            edges=graph.edges,
            metadata=graph.metadata
        )
    
    def optimize_edges(self, graph: CodeGraph) -> CodeGraph:
        """优化边结构"""
        optimized_edges = []
        edge_groups = defaultdict(list)
        
        # 按源节点和目标节点分组边
        for edge in graph.edges:
            key = (edge.source_id, edge.target_id)
            edge_groups[key].append(edge)
        
        # 合并相同方向的多条边
        for (source_id, target_id), edges in edge_groups.items():
            if len(edges) > 1:
                # 合并多条边
                merged_edge = self._merge_edges(edges)
                optimized_edges.append(merged_edge)
                self.optimization_stats['edges_merged'] += len(edges) - 1
            else:
                optimized_edges.append(edges[0])
        
        return CodeGraph(
            id=graph.id,
            nodes=graph.nodes,
            edges=optimized_edges,
            metadata=graph.metadata
        )
    
    def compress_linear_chains(self, graph: CodeGraph) -> CodeGraph:
        """压缩线性链结构"""
        # 找到可以压缩的线性链
        chains = self._find_linear_chains(graph)
        
        if not chains:
            return graph
        
        # 创建节点和边的副本
        nodes = list(graph.nodes)
        edges = list(graph.edges)
        
        # 压缩每个链
        for chain in chains:
            if len(chain) >= 3:  # 至少3个节点才值得压缩
                compressed_result = self._compress_chain(chain, nodes, edges)
                nodes, edges = compressed_result
        
        return CodeGraph(
            id=graph.id,
            nodes=nodes,
            edges=edges,
            metadata=graph.metadata
        )
    
    def split_graph_by_components(self, graph: CodeGraph) -> List[CodeGraph]:
        """将图按连通分量分割"""
        components = self._find_connected_components(graph)
        
        subgraphs = []
        for i, component_nodes in enumerate(components):
            component_node_ids = {node.id for node in component_nodes}
            
            # 找到属于该分量的边
            component_edges = [
                edge for edge in graph.edges
                if edge.source_id in component_node_ids and edge.target_id in component_node_ids
            ]
            
            # 创建子图元数据
            subgraph_metadata = GraphMetadata(
                node_count=len(component_nodes),
                edge_count=len(component_edges),
                file_count=graph.metadata.file_count,
                languages=graph.metadata.languages.copy(),
                node_types=self._count_node_types(component_nodes),
                edge_types=self._count_edge_types(component_edges),
                version=graph.metadata.version
            )
            
            subgraph = CodeGraph(
                nodes=component_nodes,
                edges=component_edges,
                metadata=subgraph_metadata
            )
            subgraphs.append(subgraph)
        
        parser_logger.info(f"图分割完成，生成 {len(subgraphs)} 个连通分量")
        return subgraphs
    
    def merge_graphs(self, graphs: List[CodeGraph]) -> CodeGraph:
        """合并多个图"""
        if not graphs:
            return CodeGraph(nodes=[], edges=[], metadata=GraphMetadata())
        
        if len(graphs) == 1:
            return graphs[0]
        
        # 合并所有节点和边
        all_nodes = []
        all_edges = []
        all_languages = set()
        total_files = 0
        
        for graph in graphs:
            all_nodes.extend(graph.nodes)
            all_edges.extend(graph.edges)
            all_languages.update(graph.metadata.languages)
            total_files += graph.metadata.file_count
        
        # 去重处理
        merged_graph = CodeGraph(
            nodes=all_nodes,
            edges=all_edges,
            metadata=GraphMetadata()
        )
        
        # 应用去重优化
        optimized_graph = self.remove_duplicate_nodes_and_edges(merged_graph)
        
        # 更新合并后的元数据
        optimized_graph.metadata = GraphMetadata(
            node_count=len(optimized_graph.nodes),
            edge_count=len(optimized_graph.edges),
            file_count=total_files,
            languages=list(all_languages),
            node_types=self._count_node_types(optimized_graph.nodes),
            edge_types=self._count_edge_types(optimized_graph.edges),
            version="1.0"
        )
        
        parser_logger.info(f"图合并完成，合并了 {len(graphs)} 个图")
        return optimized_graph
    
    def _create_node_signature(self, node: GraphNode) -> Tuple:
        """创建节点签名用于去重"""
        key_properties = ['name', 'type', 'file_path', 'line_number']
        signature_parts = [node.label, node.type]
        
        for prop in key_properties:
            if prop in node.properties:
                signature_parts.append(node.properties[prop])
        
        return tuple(signature_parts)
    
    def _group_nodes_by_similarity(self, nodes: List[GraphNode]) -> List[List[GraphNode]]:
        """按相似性分组节点"""
        groups = []
        ungrouped_nodes = list(nodes)
        
        while ungrouped_nodes:
            current_node = ungrouped_nodes.pop(0)
            current_group = [current_node]
            
            # 找到与当前节点相似的节点
            remaining_nodes = []
            for node in ungrouped_nodes:
                if self._are_nodes_similar(current_node, node):
                    current_group.append(node)
                else:
                    remaining_nodes.append(node)
            
            ungrouped_nodes = remaining_nodes
            groups.append(current_group)
        
        return groups
    
    def _are_nodes_similar(self, node1: GraphNode, node2: GraphNode) -> bool:
        """判断两个节点是否相似"""
        # 类型必须相同
        if node1.type != node2.type:
            return False
        
        # 名称相似性检查
        if node1.label == node2.label:
            return True
        
        # 文件路径相同且名称相似
        file1 = node1.properties.get('file_path', '')
        file2 = node2.properties.get('file_path', '')
        
        if file1 == file2 and self._are_names_similar(node1.label, node2.label):
            return True
        
        return False
    
    def _are_names_similar(self, name1: str, name2: str) -> bool:
        """判断两个名称是否相似"""
        # 简单的相似性检查
        if not name1 or not name2:
            return False
        
        # 编辑距离检查
        if self._edit_distance(name1.lower(), name2.lower()) <= 2:
            return True
        
        # 前缀/后缀检查
        if (name1.startswith(name2) or name2.startswith(name1) or
            name1.endswith(name2) or name2.endswith(name1)):
            return True
        
        return False
    
    def _edit_distance(self, s1: str, s2: str) -> int:
        """计算编辑距离"""
        if len(s1) < len(s2):
            s1, s2 = s2, s1
        
        if len(s2) == 0:
            return len(s1)
        
        previous_row = list(range(len(s2) + 1))
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        
        return previous_row[-1]
    
    def _merge_node_group(self, nodes: List[GraphNode]) -> GraphNode:
        """合并一组相似节点"""
        if len(nodes) == 1:
            return nodes[0]
        
        # 选择最具代表性的节点作为基础
        base_node = max(nodes, key=lambda n: n.properties.get('complexity', 0))
        
        # 合并属性
        merged_properties = base_node.properties.copy()
        
        # 收集所有文件路径
        file_paths = set()
        for node in nodes:
            if 'file_path' in node.properties:
                file_paths.add(node.properties['file_path'])
        
        if len(file_paths) > 1:
            merged_properties['file_paths'] = list(file_paths)
        
        # 合并复杂度（取最大值）
        max_complexity = max(
            node.properties.get('complexity', 0) for node in nodes
        )
        merged_properties['complexity'] = max_complexity
        
        return GraphNode(
            id=base_node.id,
            label=base_node.label,
            type=base_node.type,
            properties=merged_properties
        )
    
    def _merge_edges(self, edges: List[GraphEdge]) -> GraphEdge:
        """合并多条边"""
        if len(edges) == 1:
            return edges[0]
        
        # 选择最强的边作为基础
        base_edge = max(edges, key=lambda e: e.properties.get('strength', 0.5))
        
        # 合并属性
        merged_properties = base_edge.properties.copy()
        
        # 合并调用次数
        total_calls = sum(
            edge.properties.get('call_count', 1) for edge in edges
        )
        merged_properties['call_count'] = total_calls
        
        # 合并上下文
        contexts = [edge.properties.get('context', '') for edge in edges if edge.properties.get('context')]
        if contexts:
            merged_properties['context'] = '; '.join(contexts)
        
        # 重新计算强度
        merged_properties['strength'] = min(1.0, base_edge.properties.get('strength', 0.5) + 0.1 * (len(edges) - 1))
        
        return GraphEdge(
            id=base_edge.id,
            source_id=base_edge.source_id,
            target_id=base_edge.target_id,
            type=base_edge.type,
            properties=merged_properties
        )
    
    def _find_linear_chains(self, graph: CodeGraph) -> List[List[str]]:
        """找到线性链结构"""
        # 计算每个节点的度数
        node_degrees = defaultdict(lambda: {'in': 0, 'out': 0})
        
        for edge in graph.edges:
            node_degrees[edge.source_id]['out'] += 1
            node_degrees[edge.target_id]['in'] += 1
        
        # 找到链的起始节点（入度为0或1，出度为1）
        chains = []
        visited = set()
        
        for node_id, degrees in node_degrees.items():
            if (node_id not in visited and 
                degrees['in'] <= 1 and degrees['out'] == 1):
                
                chain = self._trace_chain(node_id, graph.edges, visited)
                if len(chain) >= 3:  # 至少3个节点的链才有意义
                    chains.append(chain)
        
        return chains
    
    def _trace_chain(self, start_node_id: str, edges: List[GraphEdge], visited: Set[str]) -> List[str]:
        """追踪线性链"""
        chain = [start_node_id]
        visited.add(start_node_id)
        current_node = start_node_id
        
        while True:
            # 找到从当前节点出发的边
            next_edges = [e for e in edges if e.source_id == current_node]
            
            if len(next_edges) != 1:
                break
            
            next_node = next_edges[0].target_id
            
            if next_node in visited:
                break
            
            # 检查下一个节点的入度是否为1
            incoming_edges = [e for e in edges if e.target_id == next_node]
            if len(incoming_edges) != 1:
                break
            
            chain.append(next_node)
            visited.add(next_node)
            current_node = next_node
        
        return chain
    
    def _compress_chain(self, chain: List[str], nodes: List[GraphNode], edges: List[GraphEdge]) -> Tuple[List[GraphNode], List[GraphEdge]]:
        """压缩线性链"""
        # 这是一个简化的实现，实际应用中可能需要更复杂的逻辑
        # 目前只是移除中间节点，保留首尾连接
        
        if len(chain) < 3:
            return nodes, edges
        
        # 保留首尾节点，移除中间节点
        nodes_to_remove = set(chain[1:-1])
        
        # 过滤节点
        filtered_nodes = [node for node in nodes if node.id not in nodes_to_remove]
        
        # 过滤边并创建新的直接连接
        filtered_edges = []
        for edge in edges:
            if edge.source_id not in nodes_to_remove and edge.target_id not in nodes_to_remove:
                filtered_edges.append(edge)
        
        # 创建从链首到链尾的直接边
        chain_edges = [e for e in edges if e.source_id in chain and e.target_id in chain]
        if chain_edges:
            # 使用第一条边的属性创建压缩边
            compressed_edge = GraphEdge(
                id=chain_edges[0].id,
                source_id=chain[0],
                target_id=chain[-1],
                type=chain_edges[0].type,
                properties={
                    **chain_edges[0].properties,
                    'compressed_chain': True,
                    'original_length': len(chain)
                }
            )
            filtered_edges.append(compressed_edge)
        
        self.optimization_stats['nodes_removed'] += len(nodes_to_remove)
        
        return filtered_nodes, filtered_edges
    
    def _find_connected_components(self, graph: CodeGraph) -> List[List[GraphNode]]:
        """找到连通分量"""
        # 构建邻接表
        adjacency = defaultdict(set)
        node_map = {node.id: node for node in graph.nodes}
        
        for edge in graph.edges:
            adjacency[edge.source_id].add(edge.target_id)
            adjacency[edge.target_id].add(edge.source_id)
        
        visited = set()
        components = []
        
        for node in graph.nodes:
            if node.id not in visited:
                component = []
                queue = deque([node.id])
                
                while queue:
                    current_id = queue.popleft()
                    if current_id not in visited:
                        visited.add(current_id)
                        component.append(node_map[current_id])
                        
                        # 添加邻居节点
                        for neighbor_id in adjacency[current_id]:
                            if neighbor_id not in visited:
                                queue.append(neighbor_id)
                
                components.append(component)
        
        return components
    
    def _count_node_types(self, nodes: List[GraphNode]) -> Dict[str, int]:
        """统计节点类型"""
        type_counts = defaultdict(int)
        for node in nodes:
            type_counts[node.type] += 1
        return dict(type_counts)
    
    def _count_edge_types(self, edges: List[GraphEdge]) -> Dict[str, int]:
        """统计边类型"""
        type_counts = defaultdict(int)
        for edge in edges:
            type_counts[edge.type] += 1
        return dict(type_counts)
    
    def get_optimization_stats(self) -> Dict[str, int]:
        """获取优化统计信息"""
        return self.optimization_stats.copy()