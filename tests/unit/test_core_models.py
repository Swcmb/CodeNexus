"""
核心数据模型的单元测试
"""

import pytest
from src.codenexus.models.core import (
    CodeElement,
    CodeGraph,
    ElementType,
    GraphEdge,
    GraphNode,
    Relationship,
    RelationType,
)


class TestCodeElement:
    """CodeElement类的测试"""
    
    def test_code_element_creation(self):
        """测试代码元素创建"""
        element = CodeElement(
            name="TestClass",
            type=ElementType.CLASS,
            file_path="test.py",
            line_number=10
        )
        
        assert element.name == "TestClass"
        assert element.type == ElementType.CLASS
        assert element.file_path == "test.py"
        assert element.line_number == 10
        assert element.end_line_number == 10  # 默认值
        assert element.id != ""  # 应该有自动生成的ID
    
    def test_code_element_with_end_line(self):
        """测试带结束行号的代码元素"""
        element = CodeElement(
            name="TestMethod",
            type=ElementType.METHOD,
            line_number=5,
            end_line_number=15
        )
        
        assert element.line_number == 5
        assert element.end_line_number == 15


class TestRelationship:
    """Relationship类的测试"""
    
    def test_relationship_creation(self):
        """测试关系创建"""
        rel = Relationship(
            source_id="class1",
            target_id="class2",
            type=RelationType.INHERITS,
            strength=0.8
        )
        
        assert rel.source_id == "class1"
        assert rel.target_id == "class2"
        assert rel.type == RelationType.INHERITS
        assert rel.strength == 0.8
        assert rel.id != ""  # 应该有自动生成的ID


class TestCodeGraph:
    """CodeGraph类的测试"""
    
    def test_empty_graph_creation(self):
        """测试空图创建"""
        graph = CodeGraph()
        
        assert len(graph.nodes) == 0
        assert len(graph.edges) == 0
        assert graph.metadata.node_count == 0
        assert graph.metadata.edge_count == 0
    
    def test_add_node(self):
        """测试添加节点"""
        graph = CodeGraph()
        node = GraphNode(
            id="node1", 
            label="TestClass", 
            type="class",
            properties={"name": "TestClass", "file_path": "test.py"}
        )
        
        graph.add_node(node)
        
        assert len(graph.nodes) == 1
        assert graph.nodes[0].id == "node1"
        assert graph.metadata.node_count == 1
    
    def test_add_edge(self):
        """测试添加边"""
        graph = CodeGraph()
        
        # 创建两个节点
        node1 = GraphNode(id="node1", label="ClassA", type="class")
        node2 = GraphNode(id="node2", label="ClassB", type="class")
        
        graph.add_node(node1)
        graph.add_node(node2)
        
        # 创建边
        edge = GraphEdge(
            id="edge1",
            source_id="node1",
            target_id="node2",
            type="inherits"
        )
        
        graph.add_edge(edge)
        
        assert len(graph.edges) == 1
        assert graph.edges[0].id == "edge1"
        assert graph.metadata.edge_count == 1
    
    def test_get_node_by_id(self):
        """测试根据ID获取节点"""
        graph = CodeGraph()
        node = GraphNode(id="test_node", label="TestClass", type="class")
        graph.add_node(node)
        
        found_node = graph.get_node_by_id("test_node")
        assert found_node is not None
        assert found_node.id == "test_node"
        
        not_found = graph.get_node_by_id("nonexistent")
        assert not_found is None
    
    def test_get_edge_by_id(self):
        """测试根据ID获取边"""
        graph = CodeGraph()
        
        # 添加节点和边
        node1 = GraphNode(id="node1", label="ClassA", type="class")
        node2 = GraphNode(id="node2", label="ClassB", type="class")
        graph.add_node(node1)
        graph.add_node(node2)
        
        edge = GraphEdge(id="test_edge", source_id="node1", target_id="node2", type="calls")
        graph.add_edge(edge)
        
        found_edge = graph.get_edge_by_id("test_edge")
        assert found_edge is not None
        assert found_edge.id == "test_edge"
        
        not_found = graph.get_edge_by_id("nonexistent")
        assert not_found is None
    
    def test_get_edges_by_source_and_target(self):
        """测试根据源节点和目标节点获取边"""
        graph = CodeGraph()
        
        # 添加节点
        node1 = GraphNode(id="node1", label="ClassA", type="class")
        node2 = GraphNode(id="node2", label="ClassB", type="class")
        node3 = GraphNode(id="node3", label="ClassC", type="class")
        graph.add_node(node1)
        graph.add_node(node2)
        graph.add_node(node3)
        
        # 添加边
        edge1 = GraphEdge(id="edge1", source_id="node1", target_id="node2", type="calls")
        edge2 = GraphEdge(id="edge2", source_id="node1", target_id="node3", type="calls")
        edge3 = GraphEdge(id="edge3", source_id="node2", target_id="node1", type="inherits")
        
        graph.add_edge(edge1)
        graph.add_edge(edge2)
        graph.add_edge(edge3)
        
        # 测试获取出边
        outgoing_edges = graph.get_edges_by_source("node1")
        assert len(outgoing_edges) == 2
        assert {edge.id for edge in outgoing_edges} == {"edge1", "edge2"}
        
        # 测试获取入边
        incoming_edges = graph.get_edges_by_target("node1")
        assert len(incoming_edges) == 1
        assert incoming_edges[0].id == "edge3"


class TestGraphEdge:
    """GraphEdge类的测试"""
    
    def test_edge_creation(self):
        """测试边创建"""
        edge = GraphEdge(
            id="test_edge",
            source_id="node1",
            target_id="node2",
            type="calls",
            properties={"strength": 0.8, "context": "method call"}
        )
        
        assert edge.id == "test_edge"
        assert edge.source_id == "node1"
        assert edge.target_id == "node2"
        assert edge.type == "calls"
        assert edge.properties["strength"] == 0.8
        assert edge.properties["context"] == "method call"
    
    def test_edge_property_management(self):
        """测试边属性管理"""
        edge = GraphEdge(id="edge1", source_id="node1", target_id="node2", type="calls")
        
        # 设置属性
        edge.set_property("call_count", 10)
        edge.set_property("line_number", 25)
        
        # 获取属性
        assert edge.get_property("call_count") == 10
        assert edge.get_property("line_number") == 25
        assert edge.get_property("nonexistent", "default") == "default"


class TestGraphNode:
    """GraphNode类的测试"""
    
    def test_node_creation(self):
        """测试节点创建"""
        node = GraphNode(
            id="test_node",
            label="TestClass",
            type="class",
            properties={"name": "TestClass", "file_path": "test.py"}
        )
        
        assert node.id == "test_node"
        assert node.label == "TestClass"
        assert node.type == "class"
        assert node.properties["name"] == "TestClass"
        assert node.properties["file_path"] == "test.py"
    
    def test_node_property_management(self):
        """测试节点属性管理"""
        node = GraphNode(id="node1", label="TestClass", type="class")
        
        # 设置属性
        node.set_property("complexity", 5)
        node.set_property("visibility", "public")
        
        # 获取属性
        assert node.get_property("complexity") == 5
        assert node.get_property("visibility") == "public"
        assert node.get_property("nonexistent", "default") == "default"