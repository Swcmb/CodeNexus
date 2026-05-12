"""
图优化器的单元测试
"""

import pytest
from src.codenexus.models.core import (
    CodeGraph, GraphNode, GraphEdge, GraphMetadata, ElementType, RelationType
)
from src.codenexus.graph.graph_optimizer import GraphOptimizer


class TestGraphOptimizer:
    """GraphOptimizer类的测试"""
    
    def setup_method(self):
        """测试前的设置"""
        self.optimizer = GraphOptimizer()
    
    def test_optimizer_initialization(self):
        """测试优化器初始化"""
        optimizer = GraphOptimizer()
        
        assert optimizer.optimization_stats['nodes_removed'] == 0
        assert optimizer.optimization_stats['edges_removed'] == 0
        assert optimizer.optimization_stats['nodes_merged'] == 0
        assert optimizer.optimization_stats['edges_merged'] == 0
    
    def test_remove_duplicate_nodes(self):
        """测试移除重复节点"""
        # 创建包含重复节点的图
        nodes = [
            GraphNode(
                id="node1",
                label="TestClass",
                type="class",
                properties={"name": "TestClass", "file_path": "test.py", "line_number": 1}
            ),
            GraphNode(
                id="node2",
                label="TestClass",  # 重复节点
                type="class",
                properties={"name": "TestClass", "file_path": "test.py", "line_number": 1}
            ),
            GraphNode(
                id="node3",
                label="AnotherClass",
                type="class",
                properties={"name": "AnotherClass", "file_path": "test.py", "line_number": 10}
            )
        ]
        
        edges = [
            GraphEdge(id="edge1", source_id="node1", target_id="node3", type="calls"),
            GraphEdge(id="edge2", source_id="node2", target_id="node3", type="calls")  # 重复边（因为node1和node2重复）
        ]
        
        graph = CodeGraph(
            nodes=nodes,
            edges=edges,
            metadata=GraphMetadata(node_count=3, edge_count=2)
        )
        
        # 优化图
        optimized_graph = self.optimizer.remove_duplicate_nodes_and_edges(graph)
        
        # 验证去重结果
        assert len(optimized_graph.nodes) == 2  # 移除了一个重复节点
        assert len(optimized_graph.edges) == 1   # 合并了重复边
        assert self.optimizer.optimization_stats['nodes_removed'] == 1
    
    def test_merge_similar_nodes(self):
        """测试合并相似节点"""
        # 创建相似节点
        nodes = [
            GraphNode(
                id="node1",
                label="getUserData",
                type="method",
                properties={"name": "getUserData", "file_path": "user.py", "complexity": 3}
            ),
            GraphNode(
                id="node2",
                label="getUserInfo",  # 相似名称
                type="method",
                properties={"name": "getUserInfo", "file_path": "user.py", "complexity": 2}
            ),
            GraphNode(
                id="node3",
                label="processData",  # 不相似
                type="method",
                properties={"name": "processData", "file_path": "data.py", "complexity": 5}
            )
        ]
        
        edges = [
            GraphEdge(id="edge1", source_id="node1", target_id="node3", type="calls"),
            GraphEdge(id="edge2", source_id="node2", target_id="node3", type="calls")
        ]
        
        graph = CodeGraph(
            nodes=nodes,
            edges=edges,
            metadata=GraphMetadata()
        )
        
        # 合并相似节点
        optimized_graph = self.optimizer.merge_similar_nodes(graph)
        
        # 验证合并结果
        assert len(optimized_graph.nodes) <= len(nodes)  # 节点数量应该减少或保持不变
        
        # 检查是否有节点被合并
        node_names = [node.label for node in optimized_graph.nodes]
        assert "processData" in node_names  # 不相似的节点应该保留
    
    def test_remove_isolated_nodes(self):
        """测试移除孤立节点"""
        # 创建包含孤立节点的图
        nodes = [
            GraphNode(id="node1", label="Connected1", type="class"),
            GraphNode(id="node2", label="Connected2", type="class"),
            GraphNode(id="node3", label="Isolated", type="class")  # 孤立节点
        ]
        
        edges = [
            GraphEdge(id="edge1", source_id="node1", target_id="node2", type="calls")
        ]
        
        graph = CodeGraph(
            nodes=nodes,
            edges=edges,
            metadata=GraphMetadata()
        )
        
        # 移除孤立节点
        optimized_graph = self.optimizer.remove_isolated_nodes(graph)
        
        # 验证结果
        assert len(optimized_graph.nodes) == 2  # 移除了孤立节点
        assert self.optimizer.optimization_stats['nodes_removed'] == 1
        
        # 验证保留的节点
        node_ids = [node.id for node in optimized_graph.nodes]
        assert "node1" in node_ids
        assert "node2" in node_ids
        assert "node3" not in node_ids
    
    def test_optimize_edges(self):
        """测试边优化"""
        # 创建包含重复边的图
        nodes = [
            GraphNode(id="node1", label="ClassA", type="class"),
            GraphNode(id="node2", label="ClassB", type="class")
        ]
        
        edges = [
            GraphEdge(
                id="edge1",
                source_id="node1",
                target_id="node2",
                type="calls",
                properties={"call_count": 5, "strength": 0.6}
            ),
            GraphEdge(
                id="edge2",
                source_id="node1",
                target_id="node2",
                type="calls",
                properties={"call_count": 3, "strength": 0.4}
            )
        ]
        
        graph = CodeGraph(
            nodes=nodes,
            edges=edges,
            metadata=GraphMetadata()
        )
        
        # 优化边
        optimized_graph = self.optimizer.optimize_edges(graph)
        
        # 验证结果
        assert len(optimized_graph.edges) == 1  # 合并了重复边
        assert self.optimizer.optimization_stats['edges_merged'] == 1
        
        # 验证合并后的边属性
        merged_edge = optimized_graph.edges[0]
        assert merged_edge.properties['call_count'] == 8  # 5 + 3
    
    def test_split_graph_by_components(self):
        """测试按连通分量分割图"""
        # 创建包含多个连通分量的图
        nodes = [
            # 第一个分量
            GraphNode(id="node1", label="A1", type="class"),
            GraphNode(id="node2", label="A2", type="class"),
            # 第二个分量
            GraphNode(id="node3", label="B1", type="class"),
            GraphNode(id="node4", label="B2", type="class"),
            # 孤立节点
            GraphNode(id="node5", label="Isolated", type="class")
        ]
        
        edges = [
            GraphEdge(id="edge1", source_id="node1", target_id="node2", type="calls"),
            GraphEdge(id="edge2", source_id="node3", target_id="node4", type="calls")
        ]
        
        graph = CodeGraph(
            nodes=nodes,
            edges=edges,
            metadata=GraphMetadata(languages=["Python"], file_count=2)
        )
        
        # 分割图
        subgraphs = self.optimizer.split_graph_by_components(graph)
        
        # 验证分割结果
        assert len(subgraphs) == 3  # 两个连通分量 + 一个孤立节点
        
        # 验证每个子图的结构
        component_sizes = [len(subgraph.nodes) for subgraph in subgraphs]
        component_sizes.sort()
        assert component_sizes == [1, 2, 2]  # 一个孤立节点，两个2节点分量
        
        # 验证子图元数据
        for subgraph in subgraphs:
            assert subgraph.metadata.node_count == len(subgraph.nodes)
            assert subgraph.metadata.edge_count == len(subgraph.edges)
            assert subgraph.metadata.languages == ["Python"]
    
    def test_merge_graphs(self):
        """测试合并多个图"""
        # 创建两个图
        graph1 = CodeGraph(
            nodes=[
                GraphNode(id="node1", label="Class1", type="class"),
                GraphNode(id="node2", label="Method1", type="method")
            ],
            edges=[
                GraphEdge(id="edge1", source_id="node1", target_id="node2", type="contains")
            ],
            metadata=GraphMetadata(languages=["Python"], file_count=1)
        )
        
        graph2 = CodeGraph(
            nodes=[
                GraphNode(id="node3", label="Class2", type="class"),
                GraphNode(id="node4", label="Method2", type="method")
            ],
            edges=[
                GraphEdge(id="edge2", source_id="node3", target_id="node4", type="contains")
            ],
            metadata=GraphMetadata(languages=["Java"], file_count=1)
        )
        
        # 合并图
        merged_graph = self.optimizer.merge_graphs([graph1, graph2])
        
        # 验证合并结果
        assert len(merged_graph.nodes) == 4
        assert len(merged_graph.edges) == 2
        assert merged_graph.metadata.file_count == 2
        assert set(merged_graph.metadata.languages) == {"Python", "Java"}
        
        # 验证节点类型统计
        assert merged_graph.metadata.node_types["class"] == 2
        assert merged_graph.metadata.node_types["method"] == 2
    
    def test_comprehensive_optimization(self):
        """测试综合优化"""
        # 创建复杂的图用于综合测试
        nodes = [
            GraphNode(id="node1", label="ClassA", type="class", properties={"complexity": 5}),
            GraphNode(id="node2", label="ClassA", type="class", properties={"complexity": 3}),  # 重复
            GraphNode(id="node3", label="ClassB", type="class", properties={"complexity": 4}),
            GraphNode(id="node4", label="Isolated", type="class", properties={"complexity": 1})  # 孤立
        ]
        
        edges = [
            GraphEdge(id="edge1", source_id="node1", target_id="node3", type="calls"),
            GraphEdge(id="edge2", source_id="node2", target_id="node3", type="calls"),  # 重复（因为node1和node2重复）
            GraphEdge(id="edge3", source_id="node1", target_id="node3", type="depends")  # 不同类型的边
        ]
        
        graph = CodeGraph(
            nodes=nodes,
            edges=edges,
            metadata=GraphMetadata()
        )
        
        # 执行综合优化
        optimized_graph = self.optimizer.optimize_graph(graph, {
            'remove_duplicates': True,
            'merge_similar_nodes': False,
            'remove_isolated_nodes': True,
            'optimize_edges': True,
            'compress_chains': False
        })
        
        # 验证优化结果
        assert len(optimized_graph.nodes) < len(nodes)  # 应该移除了重复和孤立节点
        assert len(optimized_graph.edges) <= len(edges)  # 边数量应该减少或保持不变
        
        # 验证统计信息
        stats = self.optimizer.get_optimization_stats()
        assert stats['nodes_removed'] > 0
    
    def test_linear_chain_compression(self):
        """测试线性链压缩"""
        # 创建线性链结构: A -> B -> C -> D
        nodes = [
            GraphNode(id="nodeA", label="ClassA", type="class"),
            GraphNode(id="nodeB", label="ClassB", type="class"),
            GraphNode(id="nodeC", label="ClassC", type="class"),
            GraphNode(id="nodeD", label="ClassD", type="class")
        ]
        
        edges = [
            GraphEdge(id="edge1", source_id="nodeA", target_id="nodeB", type="calls"),
            GraphEdge(id="edge2", source_id="nodeB", target_id="nodeC", type="calls"),
            GraphEdge(id="edge3", source_id="nodeC", target_id="nodeD", type="calls")
        ]
        
        graph = CodeGraph(
            nodes=nodes,
            edges=edges,
            metadata=GraphMetadata()
        )
        
        # 启用链压缩优化
        optimized_graph = self.optimizer.optimize_graph(graph, {
            'remove_duplicates': False,
            'merge_similar_nodes': False,
            'remove_isolated_nodes': False,
            'optimize_edges': False,
            'compress_chains': True
        })
        
        # 验证压缩结果（具体行为取决于实现策略）
        assert len(optimized_graph.nodes) <= len(nodes)
        assert len(optimized_graph.edges) <= len(edges)
    
    def test_circular_reference_handling(self):
        """测试循环引用处理"""
        # 创建循环引用: A -> B -> C -> A
        nodes = [
            GraphNode(id="nodeA", label="ClassA", type="class", properties={"file_path": "a.py"}),
            GraphNode(id="nodeB", label="ClassB", type="class", properties={"file_path": "b.py"}),
            GraphNode(id="nodeC", label="ClassC", type="class", properties={"file_path": "c.py"})
        ]
        
        edges = [
            GraphEdge(id="edge1", source_id="nodeA", target_id="nodeB", type="calls"),
            GraphEdge(id="edge2", source_id="nodeB", target_id="nodeC", type="calls"),
            GraphEdge(id="edge3", source_id="nodeC", target_id="nodeA", type="calls")  # 循环
        ]
        
        graph = CodeGraph(
            nodes=nodes,
            edges=edges,
            metadata=GraphMetadata()
        )
        
        # 优化包含循环引用的图，但不合并相似节点
        optimized_graph = self.optimizer.optimize_graph(graph, {
            'remove_duplicates': True,
            'merge_similar_nodes': False,  # 不合并相似节点
            'remove_isolated_nodes': False,
            'optimize_edges': True,
            'compress_chains': False
        })
        
        # 验证循环结构被正确处理
        assert len(optimized_graph.nodes) == 3  # 节点应该保留
        assert len(optimized_graph.edges) == 3  # 边也应该保留
        
        # 验证循环结构完整性
        edge_pairs = [(e.source_id, e.target_id) for e in optimized_graph.edges]
        
        # 检查每个节点都有连接
        node_ids = [node.id for node in optimized_graph.nodes]
        for node_id in node_ids:
            has_outgoing = any(source == node_id for source, _ in edge_pairs)
            has_incoming = any(target == node_id for _, target in edge_pairs)
            assert has_outgoing or has_incoming, f"节点 {node_id} 应该至少有一个连接"
    
    def test_empty_graph_optimization(self):
        """测试空图优化"""
        empty_graph = CodeGraph(
            nodes=[],
            edges=[],
            metadata=GraphMetadata()
        )
        
        # 优化空图
        optimized_graph = self.optimizer.optimize_graph(empty_graph)
        
        # 验证空图处理
        assert len(optimized_graph.nodes) == 0
        assert len(optimized_graph.edges) == 0
        assert optimized_graph.metadata.node_count == 0
        assert optimized_graph.metadata.edge_count == 0
    
    def test_single_node_graph_optimization(self):
        """测试单节点图优化"""
        single_node_graph = CodeGraph(
            nodes=[GraphNode(id="node1", label="OnlyClass", type="class")],
            edges=[],
            metadata=GraphMetadata()
        )
        
        # 优化单节点图
        optimized_graph = self.optimizer.optimize_graph(single_node_graph, {
            'remove_isolated_nodes': True
        })
        
        # 单节点在移除孤立节点选项下会被移除
        assert len(optimized_graph.nodes) == 0
        
        # 不移除孤立节点的情况
        optimized_graph2 = self.optimizer.optimize_graph(single_node_graph, {
            'remove_isolated_nodes': False
        })
        
        assert len(optimized_graph2.nodes) == 1
    
    def test_optimization_statistics(self):
        """测试优化统计信息"""
        # 创建需要优化的图
        nodes = [
            GraphNode(id="node1", label="Class1", type="class"),
            GraphNode(id="node2", label="Class1", type="class"),  # 重复
            GraphNode(id="node3", label="Isolated", type="class")  # 孤立
        ]
        
        edges = [
            GraphEdge(id="edge1", source_id="node1", target_id="node2", type="calls")
        ]
        
        graph = CodeGraph(nodes=nodes, edges=edges, metadata=GraphMetadata())
        
        # 执行优化
        self.optimizer.optimize_graph(graph, {
            'remove_duplicates': True,
            'remove_isolated_nodes': True
        })
        
        # 检查统计信息
        stats = self.optimizer.get_optimization_stats()
        
        assert 'nodes_removed' in stats
        assert 'edges_removed' in stats
        assert 'nodes_merged' in stats
        assert 'edges_merged' in stats
        
        # 验证统计数据的合理性
        assert stats['nodes_removed'] >= 0
        assert stats['edges_removed'] >= 0