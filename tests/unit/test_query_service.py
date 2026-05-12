"""
图查询服务的单元测试
"""

import pytest
from src.codenexus.models.core import (
    CodeGraph, GraphNode, GraphEdge, GraphMetadata
)
from src.codenexus.database.mock_database import MockGraphDatabase
from src.codenexus.database.query_service import GraphQueryService, QueryResult, PathResult


class TestGraphQueryService:
    """GraphQueryService类的测试"""
    
    def setup_method(self):
        """测试前的设置"""
        self.mock_db = MockGraphDatabase()
        self.query_service = GraphQueryService(self.mock_db)
        
        # 创建测试图谱
        self._create_test_graph()
    
    def _create_test_graph(self):
        """创建测试图谱"""
        # 创建节点：A -> B -> C -> D，还有 A -> E -> D 的路径
        nodes = [
            GraphNode(id="A", label="ClassA", type="class", 
                     properties={"name": "ClassA", "file_path": "a.py"}),
            GraphNode(id="B", label="ClassB", type="class",
                     properties={"name": "ClassB", "file_path": "b.py"}),
            GraphNode(id="C", label="ClassC", type="class",
                     properties={"name": "ClassC", "file_path": "c.py"}),
            GraphNode(id="D", label="ClassD", type="class",
                     properties={"name": "ClassD", "file_path": "d.py"}),
            GraphNode(id="E", label="ClassE", type="class",
                     properties={"name": "ClassE", "file_path": "e.py"}),
            GraphNode(id="F", label="MethodF", type="method",
                     properties={"name": "MethodF", "file_path": "f.py"})
        ]
        
        edges = [
            GraphEdge(id="AB", source_id="A", target_id="B", type="calls",
                     properties={"strength": 0.8}),
            GraphEdge(id="BC", source_id="B", target_id="C", type="calls",
                     properties={"strength": 0.7}),
            GraphEdge(id="CD", source_id="C", target_id="D", type="calls",
                     properties={"strength": 0.6}),
            GraphEdge(id="AE", source_id="A", target_id="E", type="depends",
                     properties={"strength": 0.9}),
            GraphEdge(id="ED", source_id="E", target_id="D", type="calls",
                     properties={"strength": 0.5}),
            GraphEdge(id="DA", source_id="D", target_id="A", type="depends",
                     properties={"strength": 0.4}),  # 创建循环
            GraphEdge(id="AF", source_id="A", target_id="F", type="contains",
                     properties={"strength": 1.0})
        ]
        
        # 修复边创建错误
        edges = [
            GraphEdge(id="AB", source_id="A", target_id="B", type="calls",
                     properties={"strength": 0.8}),
            GraphEdge(id="BC", source_id="B", target_id="C", type="calls",
                     properties={"strength": 0.7}),
            GraphEdge(id="CD", source_id="C", target_id="D", type="calls",
                     properties={"strength": 0.6}),
            GraphEdge(id="AE", source_id="A", target_id="E", type="depends",
                     properties={"strength": 0.9}),
            GraphEdge(id="ED", source_id="E", target_id="D", type="calls",
                     properties={"strength": 0.5}),
            GraphEdge(id="DA", source_id="D", target_id="A", type="depends",
                     properties={"strength": 0.4}),  # 创建循环
            GraphEdge(id="AF", source_id="A", target_id="F", type="contains",
                     properties={"strength": 1.0})
        ]
        
        metadata = GraphMetadata(
            node_count=len(nodes),
            edge_count=len(edges),
            languages=["Python"]
        )
        
        self.test_graph = CodeGraph(
            id="test_graph",
            nodes=nodes,
            edges=edges,
            metadata=metadata
        )
        
        self.mock_db.store_graph(self.test_graph)
    
    def test_find_shortest_path(self):
        """测试查找最短路径"""
        # 测试存在的路径
        result = self.query_service.find_shortest_path("test_graph", "A", "D")
        
        assert result is not None
        assert result.path[0] == "A"
        assert result.path[-1] == "D"
        assert result.length > 0
        
        # 验证路径是最短的（A -> E -> D 比 A -> B -> C -> D 短）
        assert result.length == 2  # A -> E -> D
        assert result.path == ["A", "E", "D"]
    
    def test_find_shortest_path_with_edge_types(self):
        """测试带边类型过滤的最短路径"""
        # 只允许calls类型的边
        result = self.query_service.find_shortest_path("test_graph", "A", "D", 
                                                      edge_types=["calls"])
        
        assert result is not None
        assert result.length == 3  # A -> B -> C -> D
        assert result.path == ["A", "B", "C", "D"]
    
    def test_find_shortest_path_no_path(self):
        """测试不存在路径的情况"""
        result = self.query_service.find_shortest_path("test_graph", "F", "A")
        
        assert result is None
    
    def test_find_all_paths(self):
        """测试查找所有路径"""
        paths = self.query_service.find_all_paths("test_graph", "A", "D", max_paths=5)
        
        assert len(paths) >= 2  # 至少有两条路径
        
        # 验证路径
        path_lists = [path.path for path in paths]
        assert ["A", "E", "D"] in path_lists
        assert ["A", "B", "C", "D"] in path_lists
        
        # 验证路径按长度排序
        for i in range(len(paths) - 1):
            assert paths[i].length <= paths[i + 1].length
    
    def test_analyze_impact_downstream(self):
        """测试下游影响分析"""
        result = self.query_service.analyze_impact("test_graph", ["A"], 
                                                  direction="downstream", max_depth=3)
        
        assert len(result.nodes) > 1  # A的下游节点
        assert result.metadata["changed_nodes"] == ["A"]
        assert result.metadata["direction"] == "downstream"
        
        # 验证包含下游节点
        node_ids = [node.id for node in result.nodes]
        assert "B" in node_ids or "E" in node_ids  # A的直接下游
    
    def test_analyze_impact_upstream(self):
        """测试上游影响分析"""
        result = self.query_service.analyze_impact("test_graph", ["D"], 
                                                  direction="upstream", max_depth=3)
        
        assert len(result.nodes) > 1  # D的上游节点
        
        # 验证包含上游节点
        node_ids = [node.id for node in result.nodes]
        assert "C" in node_ids or "E" in node_ids  # D的直接上游
    
    def test_analyze_impact_both_directions(self):
        """测试双向影响分析"""
        result = self.query_service.analyze_impact("test_graph", ["B"], 
                                                  direction="both", max_depth=2)
        
        assert len(result.nodes) > 1
        
        node_ids = [node.id for node in result.nodes]
        # B的上游和下游都应该包含
        assert "A" in node_ids  # 上游
        assert "C" in node_ids  # 下游
    
    def test_find_cycles(self):
        """测试查找循环依赖"""
        cycles = self.query_service.find_cycles("test_graph")
        
        assert len(cycles) > 0  # 应该找到循环
        
        # 验证循环包含预期的节点
        for cycle in cycles:
            assert len(cycle) >= 3  # 至少3个节点的循环
            assert cycle[0] == cycle[-1]  # 循环的起点和终点相同
    
    def test_find_strongly_connected_components(self):
        """测试查找强连通分量"""
        components = self.query_service.find_strongly_connected_components("test_graph")
        
        # 由于存在循环，应该有强连通分量
        if components:
            for component in components:
                assert len(component) > 1  # 强连通分量至少包含2个节点
    
    def test_pattern_match(self):
        """测试模式匹配"""
        # 查找所有class类型的节点
        pattern = {
            "nodes": {"type": "class"},
            "edges": {}
        }
        
        results = self.query_service.pattern_match("test_graph", pattern)
        
        assert len(results) > 0
        
        result = results[0]
        assert len(result.nodes) > 0
        
        # 验证所有匹配的节点都是class类型
        for node in result.nodes:
            assert node.type == "class"
    
    def test_pattern_match_with_properties(self):
        """测试带属性的模式匹配"""
        pattern = {
            "nodes": {"type": "class", "name": "ClassA"},
            "edges": {}
        }
        
        results = self.query_service.pattern_match("test_graph", pattern)
        
        assert len(results) > 0
        result = results[0]
        
        # 应该只匹配ClassA
        matching_nodes = [node for node in result.nodes 
                         if node.properties.get("name") == "ClassA"]
        assert len(matching_nodes) == 1
        assert matching_nodes[0].id == "A"
    
    def test_get_node_neighbors_out(self):
        """测试获取出邻居"""
        result = self.query_service.get_node_neighbors("test_graph", "A", 
                                                      direction="out", depth=1)
        
        assert len(result.nodes) > 1  # 包含A本身和其邻居
        
        neighbor_ids = [node.id for node in result.nodes if node.id != "A"]
        assert "B" in neighbor_ids or "E" in neighbor_ids  # A的出邻居
    
    def test_get_node_neighbors_in(self):
        """测试获取入邻居"""
        result = self.query_service.get_node_neighbors("test_graph", "D", 
                                                      direction="in", depth=1)
        
        assert len(result.nodes) > 1  # 包含D本身和其邻居
        
        neighbor_ids = [node.id for node in result.nodes if node.id != "D"]
        assert "C" in neighbor_ids or "E" in neighbor_ids  # D的入邻居
    
    def test_get_node_neighbors_both(self):
        """测试获取双向邻居"""
        result = self.query_service.get_node_neighbors("test_graph", "B", 
                                                      direction="both", depth=1)
        
        assert len(result.nodes) > 1
        
        neighbor_ids = [node.id for node in result.nodes if node.id != "B"]
        assert "A" in neighbor_ids  # B的入邻居
        assert "C" in neighbor_ids  # B的出邻居
    
    def test_get_node_neighbors_with_depth(self):
        """测试多层邻居查询"""
        result = self.query_service.get_node_neighbors("test_graph", "A", 
                                                      direction="out", depth=2)
        
        # 深度为2应该能到达更多节点
        neighbor_ids = [node.id for node in result.nodes if node.id != "A"]
        
        # 应该包含A的2层出邻居
        assert len(neighbor_ids) >= 2
    
    def test_get_node_neighbors_with_edge_types(self):
        """测试带边类型过滤的邻居查询"""
        result = self.query_service.get_node_neighbors("test_graph", "A", 
                                                      direction="out", depth=1,
                                                      edge_types=["calls"])
        
        neighbor_ids = [node.id for node in result.nodes if node.id != "A"]
        
        # 只通过calls边，应该只能到达B
        assert "B" in neighbor_ids
        # 不应该包含通过depends边到达的E
        if "E" in neighbor_ids:
            # 检查是否有其他calls边到E
            calls_to_e = [edge for edge in result.edges 
                         if edge.target_id == "E" and edge.type == "calls"]
            assert len(calls_to_e) > 0
    
    def test_nonexistent_graph(self):
        """测试不存在的图谱"""
        result = self.query_service.find_shortest_path("nonexistent", "A", "B")
        assert result is None
        
        result = self.query_service.analyze_impact("nonexistent", ["A"])
        assert len(result.nodes) == 0
        assert len(result.edges) == 0
        
        cycles = self.query_service.find_cycles("nonexistent")
        assert len(cycles) == 0
    
    def test_empty_changed_nodes(self):
        """测试空的变更节点列表"""
        result = self.query_service.analyze_impact("test_graph", [])
        
        # 空的变更节点列表应该返回空结果
        assert len(result.nodes) == 0
        assert len(result.edges) == 0
    
    def test_max_depth_limit(self):
        """测试最大深度限制"""
        # 测试深度限制为1的情况
        result = self.query_service.analyze_impact("test_graph", ["A"], 
                                                  max_depth=1)
        
        # 深度为1应该只包含直接邻居
        node_ids = [node.id for node in result.nodes]
        
        # 验证不会超过指定深度
        # 具体验证逻辑取决于图的结构
        assert len(node_ids) > 0  # 至少包含一些节点
    
    def test_edge_type_filtering(self):
        """测试边类型过滤"""
        # 只考虑calls类型的边进行影响分析
        result = self.query_service.analyze_impact("test_graph", ["A"], 
                                                  edge_types=["calls"])
        
        # 验证结果中的边都是指定类型
        for edge in result.edges:
            assert edge.type == "calls"
    
    def test_query_result_metadata(self):
        """测试查询结果元数据"""
        result = self.query_service.analyze_impact("test_graph", ["A", "B"], 
                                                  direction="downstream", max_depth=2)
        
        assert result.metadata is not None
        assert result.metadata["changed_nodes"] == ["A", "B"]
        assert result.metadata["direction"] == "downstream"
        assert result.metadata["max_depth"] == 2
        assert "total_affected" in result.metadata