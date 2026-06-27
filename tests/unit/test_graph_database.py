"""
图数据库的单元测试
"""

import pytest
from unittest.mock import Mock, patch

from src.codenexus.models.core import (
    CodeGraph, GraphNode, GraphEdge, GraphMetadata, ElementType, RelationType
)
from src.codenexus.database.mock_database import MockGraphDatabase
from src.codenexus.database.graph_database import GraphDatabase, GraphDatabaseError


class TestMockGraphDatabase:
    """MockGraphDatabase类的测试"""
    
    def setup_method(self):
        """测试前的设置"""
        self.mock_db = MockGraphDatabase()
    
    def test_mock_database_initialization(self):
        """测试模拟数据库初始化"""
        db = MockGraphDatabase()
        
        assert db.is_connected() == True
        assert len(db.graphs) == 0
    
    def test_store_and_retrieve_graph(self):
        """测试存储和检索图谱"""
        # 创建测试图谱
        nodes = [
            GraphNode(id="node1", label="ClassA", type="class", 
                     properties={"name": "ClassA", "file_path": "test.py"}),
            GraphNode(id="node2", label="ClassB", type="class",
                     properties={"name": "ClassB", "file_path": "test.py"})
        ]
        
        edges = [
            GraphEdge(id="edge1", source_id="node1", target_id="node2", type="inherits",
                     properties={"strength": 0.8})
        ]
        
        metadata = GraphMetadata(
            node_count=2,
            edge_count=1,
            languages=["Python"],
            version="1.0"
        )
        
        graph = CodeGraph(
            id="test_graph",
            nodes=nodes,
            edges=edges,
            metadata=metadata
        )
        
        # 存储图谱
        stored_id = self.mock_db.store_graph(graph)
        assert stored_id == "test_graph"
        
        # 检索图谱
        retrieved_graph = self.mock_db.retrieve_graph("test_graph")
        
        assert retrieved_graph is not None
        assert retrieved_graph.id == "test_graph"
        assert len(retrieved_graph.nodes) == 2
        assert len(retrieved_graph.edges) == 1
        assert retrieved_graph.metadata.node_count == 2
        assert retrieved_graph.metadata.edge_count == 1
        assert retrieved_graph.metadata.languages == ["Python"]
    
    def test_retrieve_nonexistent_graph(self):
        """测试检索不存在的图谱"""
        result = self.mock_db.retrieve_graph("nonexistent")
        assert result is None
    
    def test_delete_graph(self):
        """测试删除图谱"""
        # 创建并存储图谱
        graph = CodeGraph(
            id="test_graph",
            nodes=[GraphNode(id="node1", label="Test", type="class")],
            edges=[],
            metadata=GraphMetadata()
        )
        
        self.mock_db.store_graph(graph)
        assert self.mock_db.retrieve_graph("test_graph") is not None
        
        # 删除图谱
        result = self.mock_db.delete_graph("test_graph")
        assert result == True
        assert self.mock_db.retrieve_graph("test_graph") is None
        
        # 删除不存在的图谱
        result = self.mock_db.delete_graph("nonexistent")
        assert result == False
    
    def test_query_nodes(self):
        """测试查询节点"""
        # 创建测试图谱
        nodes = [
            GraphNode(id="node1", label="ClassA", type="class",
                     properties={"name": "ClassA", "visibility": "public"}),
            GraphNode(id="node2", label="MethodB", type="method",
                     properties={"name": "MethodB", "visibility": "private"}),
            GraphNode(id="node3", label="ClassC", type="class",
                     properties={"name": "ClassC", "visibility": "public"})
        ]
        
        graph = CodeGraph(
            id="test_graph",
            nodes=nodes,
            edges=[],
            metadata=GraphMetadata()
        )
        
        self.mock_db.store_graph(graph)
        
        # 查询所有节点
        all_nodes = self.mock_db.query_nodes("test_graph")
        assert len(all_nodes) == 3
        
        # 按类型查询
        class_nodes = self.mock_db.query_nodes("test_graph", node_type="class")
        assert len(class_nodes) == 2
        assert all(node["type"] == "class" for node in class_nodes)
        
        method_nodes = self.mock_db.query_nodes("test_graph", node_type="method")
        assert len(method_nodes) == 1
        assert method_nodes[0]["type"] == "method"
        
        # 按属性查询
        public_nodes = self.mock_db.query_nodes("test_graph", 
                                               properties={"visibility": "public"})
        assert len(public_nodes) == 2
        assert all(node["properties"]["visibility"] == "public" for node in public_nodes)
        
        # 组合查询
        public_classes = self.mock_db.query_nodes("test_graph", 
                                                 node_type="class",
                                                 properties={"visibility": "public"})
        assert len(public_classes) == 2
        assert all(node["type"] == "class" and 
                  node["properties"]["visibility"] == "public" 
                  for node in public_classes)
    
    def test_query_edges(self):
        """测试查询边"""
        # 创建测试图谱
        nodes = [
            GraphNode(id="node1", label="ClassA", type="class"),
            GraphNode(id="node2", label="ClassB", type="class"),
            GraphNode(id="node3", label="ClassC", type="class")
        ]
        
        edges = [
            GraphEdge(id="edge1", source_id="node1", target_id="node2", type="inherits"),
            GraphEdge(id="edge2", source_id="node2", target_id="node3", type="calls"),
            GraphEdge(id="edge3", source_id="node1", target_id="node3", type="depends")
        ]
        
        graph = CodeGraph(
            id="test_graph",
            nodes=nodes,
            edges=edges,
            metadata=GraphMetadata()
        )
        
        self.mock_db.store_graph(graph)
        
        # 查询所有边
        all_edges = self.mock_db.query_edges("test_graph")
        assert len(all_edges) == 3
        
        # 按类型查询
        inherit_edges = self.mock_db.query_edges("test_graph", edge_type="inherits")
        assert len(inherit_edges) == 1
        assert inherit_edges[0]["type"] == "inherits"
        
        # 按源节点查询
        node1_edges = self.mock_db.query_edges("test_graph", source_id="node1")
        assert len(node1_edges) == 2
        assert all(edge["source_id"] == "node1" for edge in node1_edges)
        
        # 按目标节点查询
        node3_edges = self.mock_db.query_edges("test_graph", target_id="node3")
        assert len(node3_edges) == 2
        assert all(edge["target_id"] == "node3" for edge in node3_edges)
        
        # 验证边包含源节点和目标节点信息
        for edge in all_edges:
            assert "source_node" in edge
            assert "target_node" in edge
            assert edge["source_node"]["id"] == edge["source_id"]
            assert edge["target_node"]["id"] == edge["target_id"]
    
    def test_get_graph_statistics(self):
        """测试获取图谱统计信息"""
        # 创建测试图谱
        nodes = [
            GraphNode(id="node1", label="ClassA", type="class"),
            GraphNode(id="node2", label="MethodB", type="method"),
            GraphNode(id="node3", label="ClassC", type="class")
        ]
        
        edges = [
            GraphEdge(id="edge1", source_id="node1", target_id="node2", type="contains"),
            GraphEdge(id="edge2", source_id="node2", target_id="node3", type="calls")
        ]
        
        graph = CodeGraph(
            id="test_graph",
            nodes=nodes,
            edges=edges,
            metadata=GraphMetadata()
        )
        
        self.mock_db.store_graph(graph)
        
        # 获取统计信息
        stats = self.mock_db.get_graph_statistics("test_graph")
        
        assert stats["node_count"] == 3
        assert stats["edge_count"] == 2
        assert set(stats["node_types"]) == {"class", "method"}
        assert set(stats["edge_types"]) == {"contains", "calls"}
        
        # 不存在的图谱
        empty_stats = self.mock_db.get_graph_statistics("nonexistent")
        assert empty_stats["node_count"] == 0
        assert empty_stats["edge_count"] == 0
        assert empty_stats["node_types"] == []
        assert empty_stats["edge_types"] == []
    
    def test_execute_cypher(self):
        """测试执行Cypher查询"""
        # 测试简单查询
        result = self.mock_db.execute_cypher("RETURN 1")
        assert result == [{"1": 1}]
        
        # 测试计数查询
        result = self.mock_db.execute_cypher("MATCH (n) RETURN count(n)")
        assert len(result) == 1
        assert "count" in result[0]
        
        # 测试未知查询
        result = self.mock_db.execute_cypher("UNKNOWN QUERY")
        assert result == []
    
    def test_clear_all(self):
        """测试清空所有数据"""
        # 添加一些数据
        graph = CodeGraph(
            id="test_graph",
            nodes=[GraphNode(id="node1", label="Test", type="class")],
            edges=[],
            metadata=GraphMetadata()
        )
        
        self.mock_db.store_graph(graph)
        assert len(self.mock_db.list_graphs()) == 1
        
        # 清空数据
        self.mock_db.clear_all()
        assert len(self.mock_db.list_graphs()) == 0
    
    def test_export_import_graph(self):
        """测试导出和导入图谱"""
        # 创建测试图谱
        nodes = [
            GraphNode(id="node1", label="ClassA", type="class",
                     properties={"name": "ClassA"})
        ]
        
        edges = [
            GraphEdge(id="edge1", source_id="node1", target_id="node1", type="self_ref",
                     properties={"strength": 0.5})
        ]
        
        metadata = GraphMetadata(
            node_count=1,
            edge_count=1,
            languages=["Python"]
        )
        
        original_graph = CodeGraph(
            id="test_graph",
            nodes=nodes,
            edges=edges,
            metadata=metadata
        )
        
        self.mock_db.store_graph(original_graph)
        
        # 导出图谱
        exported_data = self.mock_db.export_graph("test_graph")
        assert exported_data is not None
        assert exported_data["id"] == "test_graph"
        assert len(exported_data["nodes"]) == 1
        assert len(exported_data["edges"]) == 1
        assert exported_data["metadata"]["languages"] == ["Python"]
        
        # 清空数据库
        self.mock_db.clear_all()
        
        # 导入图谱
        imported_id = self.mock_db.import_graph(exported_data)
        assert imported_id == "test_graph"
        
        # 验证导入的图谱
        imported_graph = self.mock_db.retrieve_graph("test_graph")
        assert imported_graph is not None
        assert imported_graph.id == "test_graph"
        assert len(imported_graph.nodes) == 1
        assert len(imported_graph.edges) == 1
        assert imported_graph.metadata.languages == ["Python"]
        
        # 导出不存在的图谱
        result = self.mock_db.export_graph("nonexistent")
        assert result is None


class TestGraphDatabase:
    """GraphDatabase类的测试（需要Neo4j驱动）"""
    
    def test_initialization_without_neo4j(self):
        """测试在没有Neo4j驱动时的初始化"""
        with patch('src.codeweaver.database.graph_database.NEO4J_AVAILABLE', False):
            with pytest.raises(GraphDatabaseError) as exc_info:
                GraphDatabase()
            
            assert "Neo4j驱动未安装" in str(exc_info.value)
    
    def test_initialization_with_neo4j(self):
        """测试在有Neo4j驱动时的初始化"""
        with patch('src.codeweaver.database.graph_database.NEO4J_AVAILABLE', True):
            db = GraphDatabase()
            assert db.uri == "bolt://localhost:7687"
            assert db.username == "neo4j"
            assert db.password == "password"
            assert db.is_connected() == False
    
    def test_custom_connection_parameters(self):
        """测试自定义连接参数"""
        with patch('src.codeweaver.database.graph_database.NEO4J_AVAILABLE', True):
            db = GraphDatabase(
                uri="bolt://custom:7687",
                username="custom_user",
                password="custom_pass"
            )
            assert db.uri == "bolt://custom:7687"
            assert db.username == "custom_user"
            assert db.password == "custom_pass"