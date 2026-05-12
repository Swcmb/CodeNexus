"""
图构建器的单元测试
"""

import pytest
from src.codenexus.models.core import (
    CodeElement, ElementType, Relationship, RelationType, ParseResult
)
from src.codenexus.graph.graph_builder import GraphBuilder


class TestGraphBuilder:
    """GraphBuilder类的测试"""
    
    def setup_method(self):
        """测试前的设置"""
        self.builder = GraphBuilder()
    
    def test_builder_initialization(self):
        """测试图构建器初始化"""
        builder = GraphBuilder()
        
        assert builder.node_cache == {}
        assert builder.edge_cache == {}
        assert builder.element_to_node == {}
    
    def test_create_nodes_from_elements(self):
        """测试从代码元素创建节点"""
        # 创建测试元素
        elements = [
            CodeElement(
                name="TestClass",
                type=ElementType.CLASS,
                file_path="test.py",
                line_number=1,
                complexity=5
            ),
            CodeElement(
                name="test_method",
                type=ElementType.METHOD,
                file_path="test.py",
                line_number=10,
                complexity=2
            )
        ]
        
        # 创建节点
        nodes = self.builder.create_nodes(elements)
        
        # 验证节点创建
        assert len(nodes) == 2
        
        # 验证第一个节点
        class_node = nodes[0]
        assert class_node.label == "TestClass"
        assert class_node.type == "class"
        assert class_node.properties["name"] == "TestClass"
        assert class_node.properties["file_path"] == "test.py"
        assert class_node.properties["complexity"] == 5
        
        # 验证第二个节点
        method_node = nodes[1]
        assert method_node.label == "test_method"
        assert method_node.type == "method"
        assert method_node.properties["name"] == "test_method"
        assert method_node.properties["complexity"] == 2
        
        # 验证缓存
        assert len(self.builder.node_cache) == 2
        assert len(self.builder.element_to_node) == 2
    
    def test_create_edges_from_relationships(self):
        """测试从关系创建边"""
        # 先创建一些元素和节点
        elements = [
            CodeElement(id="elem1", name="ClassA", type=ElementType.CLASS),
            CodeElement(id="elem2", name="ClassB", type=ElementType.CLASS)
        ]
        
        nodes = self.builder.create_nodes(elements)
        
        # 创建关系
        relationships = [
            Relationship(
                source_id="elem1",
                target_id="elem2",
                type=RelationType.INHERITS,
                line_number=5,
                context="ClassA inherits from ClassB"
            )
        ]
        
        # 创建边
        edges = self.builder.create_edges(relationships)
        
        # 验证边创建
        assert len(edges) == 1
        
        edge = edges[0]
        assert edge.type == "inherits"
        assert edge.source_id in self.builder.node_cache
        assert edge.target_id in self.builder.node_cache
        assert edge.properties["context"] == "ClassA inherits from ClassB"
        assert edge.properties["line_number"] == 5
        
        # 验证关系强度计算
        assert "strength" in edge.properties
        assert 0.0 <= edge.properties["strength"] <= 1.0
    
    def test_build_complete_graph(self):
        """测试构建完整图谱"""
        # 创建解析结果
        elements = [
            CodeElement(
                id="class1",
                name="Animal",
                type=ElementType.CLASS,
                file_path="animal.py",
                line_number=1
            ),
            CodeElement(
                id="class2",
                name="Dog",
                type=ElementType.CLASS,
                file_path="dog.py",
                line_number=1
            ),
            CodeElement(
                id="method1",
                name="speak",
                type=ElementType.METHOD,
                file_path="animal.py",
                line_number=5
            )
        ]
        
        relationships = [
            Relationship(
                source_id="class2",
                target_id="class1",
                type=RelationType.INHERITS,
                context="Dog inherits from Animal"
            )
        ]
        
        parse_result = ParseResult(
            file_path="test_project",
            elements=elements,
            relationships=relationships
        )
        
        # 构建图谱
        graph = self.builder.build_graph([parse_result])
        
        # 验证图谱结构
        assert len(graph.nodes) == 3
        assert len(graph.edges) == 1
        
        # 验证元数据
        assert graph.metadata.node_count == 3
        assert graph.metadata.edge_count == 1
        assert graph.metadata.file_count > 0
        assert graph.metadata.version == "1.0"
        
        # 验证节点类型统计
        assert "class" in graph.metadata.node_types
        assert "method" in graph.metadata.node_types
        assert graph.metadata.node_types["class"] == 2
        assert graph.metadata.node_types["method"] == 1
        
        # 验证边类型统计
        assert "inherits" in graph.metadata.edge_types
        assert graph.metadata.edge_types["inherits"] == 1
    
    def test_relationship_strength_calculation(self):
        """测试关系强度计算"""
        # 测试不同类型关系的强度
        relationships = [
            Relationship(type=RelationType.INHERITS),
            Relationship(type=RelationType.CALLS),
            Relationship(type=RelationType.DEPENDS),
            Relationship(
                type=RelationType.CALLS,
                context="This is a very detailed context with lots of information about the call",
                metadata={"call_count": 15}
            )
        ]
        
        for rel in relationships:
            strength = self.builder._calculate_relationship_strength(rel)
            assert 0.0 <= strength <= 1.0
        
        # 继承关系应该有较高强度
        inherit_strength = self.builder._calculate_relationship_strength(relationships[0])
        call_strength = self.builder._calculate_relationship_strength(relationships[1])
        assert inherit_strength > call_strength
        
        # 有详细上下文和高调用次数的关系应该有更高强度
        detailed_strength = self.builder._calculate_relationship_strength(relationships[3])
        assert detailed_strength > call_strength
    
    def test_deduplicate_nodes(self):
        """测试节点去重"""
        from src.codenexus.models.core import GraphNode
        
        # 创建重复节点
        nodes = [
            GraphNode(
                id="node1",
                label="TestClass",
                type="class",
                properties={"name": "TestClass", "type": "class", "file_path": "test.py"}
            ),
            GraphNode(
                id="node2",
                label="TestClass",
                type="class",
                properties={"name": "TestClass", "type": "class", "file_path": "test.py"}
            ),
            GraphNode(
                id="node3",
                label="AnotherClass",
                type="class",
                properties={"name": "AnotherClass", "type": "class", "file_path": "test.py"}
            )
        ]
        
        # 去重
        unique_nodes = self.builder._deduplicate_nodes(nodes)
        
        # 验证去重结果
        assert len(unique_nodes) == 2
        
        # 验证保留的节点
        names = [node.properties.get("name") for node in unique_nodes]
        assert "TestClass" in names
        assert "AnotherClass" in names
    
    def test_deduplicate_edges(self):
        """测试边去重"""
        from src.codenexus.models.core import GraphEdge
        
        # 创建重复边
        edges = [
            GraphEdge(id="edge1", source_id="node1", target_id="node2", type="calls"),
            GraphEdge(id="edge2", source_id="node1", target_id="node2", type="calls"),
            GraphEdge(id="edge3", source_id="node2", target_id="node3", type="inherits")
        ]
        
        # 去重
        unique_edges = self.builder._deduplicate_edges(edges)
        
        # 验证去重结果
        assert len(unique_edges) == 2
        
        # 验证保留的边
        edge_keys = [(edge.source_id, edge.target_id, edge.type) for edge in unique_edges]
        assert ("node1", "node2", "calls") in edge_keys
        assert ("node2", "node3", "inherits") in edge_keys
    
    def test_remove_isolated_nodes(self):
        """测试移除孤立节点"""
        from src.codenexus.models.core import GraphNode, GraphEdge
        
        # 创建节点，其中一个是孤立的
        nodes = [
            GraphNode(id="node1", label="Connected1"),
            GraphNode(id="node2", label="Connected2"),
            GraphNode(id="node3", label="Isolated")
        ]
        
        # 创建边，只连接前两个节点
        edges = [
            GraphEdge(id="edge1", source_id="node1", target_id="node2", type="calls")
        ]
        
        # 移除孤立节点
        connected_nodes = self.builder._remove_isolated_nodes(nodes, edges, remove_isolated=True)
        
        # 验证结果
        assert len(connected_nodes) == 2
        
        # 验证保留的节点
        node_ids = [node.id for node in connected_nodes]
        assert "node1" in node_ids
        assert "node2" in node_ids
        assert "node3" not in node_ids
    
    def test_get_node_by_element_id(self):
        """测试根据元素ID获取节点"""
        # 创建元素和节点
        element = CodeElement(id="test_element", name="TestClass", type=ElementType.CLASS)
        nodes = self.builder.create_nodes([element])
        
        # 根据元素ID获取节点
        found_node = self.builder.get_node_by_element_id("test_element")
        
        # 验证结果
        assert found_node is not None
        assert found_node.properties["element_id"] == "test_element"
        assert found_node.label == "TestClass"
        
        # 测试不存在的元素ID
        not_found = self.builder.get_node_by_element_id("nonexistent")
        assert not_found is None
    
    def test_get_connected_nodes(self):
        """测试获取连接的节点"""
        from src.codenexus.models.core import GraphEdge
        
        # 创建边
        edges = [
            GraphEdge(id="edge1", source_id="node1", target_id="node2", type="calls"),
            GraphEdge(id="edge2", source_id="node1", target_id="node3", type="depends"),
            GraphEdge(id="edge3", source_id="node4", target_id="node1", type="inherits")
        ]
        
        # 获取node1的连接节点
        connected = self.builder.get_connected_nodes("node1", edges)
        
        # 验证结果
        assert len(connected) == 3
        assert "node2" in connected
        assert "node3" in connected
        assert "node4" in connected
    
    def test_calculate_node_metrics(self):
        """测试计算节点指标"""
        from src.codenexus.models.core import GraphEdge
        
        # 创建边
        edges = [
            GraphEdge(id="edge1", source_id="node1", target_id="node2", type="calls"),
            GraphEdge(id="edge2", source_id="node1", target_id="node3", type="depends"),
            GraphEdge(id="edge3", source_id="node4", target_id="node1", type="inherits"),
            GraphEdge(id="edge4", source_id="node5", target_id="node1", type="calls")
        ]
        
        # 计算node1的指标
        metrics = self.builder.calculate_node_metrics("node1", edges)
        
        # 验证结果
        assert metrics["out_degree"] == 2  # node1 -> node2, node1 -> node3
        assert metrics["in_degree"] == 2   # node4 -> node1, node5 -> node1
        assert metrics["total_degree"] == 4
    
    def test_optimize_graph(self):
        """测试图优化"""
        # 创建包含重复和孤立节点的图
        from src.codenexus.models.core import CodeGraph, GraphNode, GraphEdge, GraphMetadata
        
        nodes = [
            GraphNode(
                id="node1",
                label="Class1",
                properties={"name": "Class1", "type": "class", "file_path": "test.py"}
            ),
            GraphNode(
                id="node2",
                label="Class1",  # 重复
                properties={"name": "Class1", "type": "class", "file_path": "test.py"}
            ),
            GraphNode(
                id="node3",
                label="Class2",
                properties={"name": "Class2", "type": "class", "file_path": "test.py"}
            ),
            GraphNode(
                id="node4",
                label="Isolated",  # 孤立节点
                properties={"name": "Isolated", "type": "class", "file_path": "test.py"}
            )
        ]
        
        edges = [
            GraphEdge(id="edge1", source_id="node1", target_id="node3", type="calls"),
            GraphEdge(id="edge2", source_id="node1", target_id="node3", type="calls")  # 重复
        ]
        
        metadata = GraphMetadata(node_count=len(nodes), edge_count=len(edges))
        graph = CodeGraph(nodes=nodes, edges=edges, metadata=metadata)
        
        # 优化图
        optimized_graph = self.builder.optimize_graph(graph)
        
        # 验证优化结果
        assert len(optimized_graph.nodes) < len(nodes)  # 应该移除重复和孤立节点
        assert len(optimized_graph.edges) < len(edges)  # 应该移除重复边
        assert optimized_graph.metadata.node_count == len(optimized_graph.nodes)
        assert optimized_graph.metadata.edge_count == len(optimized_graph.edges)
    
    def test_build_graph_with_multiple_files(self):
        """测试构建多文件项目的图谱"""
        # 创建多个文件的解析结果
        parse_results = []
        
        # 文件1: models.py
        models_elements = [
            CodeElement(
                id="user_class",
                name="User",
                type=ElementType.CLASS,
                file_path="models.py",
                line_number=1
            ),
            CodeElement(
                id="user_init",
                name="__init__",
                type=ElementType.METHOD,
                file_path="models.py",
                line_number=5
            )
        ]
        
        # 文件2: services.py
        services_elements = [
            CodeElement(
                id="user_service",
                name="UserService",
                type=ElementType.CLASS,
                file_path="services.py",
                line_number=1
            ),
            CodeElement(
                id="create_user",
                name="create_user",
                type=ElementType.METHOD,
                file_path="services.py",
                line_number=10
            )
        ]
        
        # 跨文件关系
        relationships = [
            Relationship(
                source_id="create_user",
                target_id="user_class",
                type=RelationType.DEPENDS,
                context="UserService.create_user depends on User class"
            )
        ]
        
        parse_results.append(ParseResult(
            file_path="models.py",
            elements=models_elements,
            relationships=[]
        ))
        
        parse_results.append(ParseResult(
            file_path="services.py",
            elements=services_elements,
            relationships=relationships
        ))
        
        # 构建图谱
        graph = self.builder.build_graph(parse_results)
        
        # 验证多文件图谱
        assert len(graph.nodes) == 4
        assert len(graph.edges) == 1
        assert graph.metadata.file_count == 2
        
        # 验证跨文件关系
        edge = graph.edges[0]
        assert edge.type == "depends"
        
        # 验证文件路径信息
        file_paths = set()
        for node in graph.nodes:
            file_path = node.properties.get("file_path")
            if file_path:
                file_paths.add(file_path)
        
        assert "models.py" in file_paths
        assert "services.py" in file_paths
    
    def test_empty_parse_results(self):
        """测试空解析结果"""
        graph = self.builder.build_graph([])
        
        assert len(graph.nodes) == 0
        assert len(graph.edges) == 0
        assert graph.metadata.node_count == 0
        assert graph.metadata.edge_count == 0
        assert graph.metadata.file_count == 0
    
    def test_parse_results_with_no_relationships(self):
        """测试只有元素没有关系的解析结果"""
        elements = [
            CodeElement(name="Class1", type=ElementType.CLASS),
            CodeElement(name="Class2", type=ElementType.CLASS)
        ]
        
        parse_result = ParseResult(
            file_path="test.py",
            elements=elements,
            relationships=[]
        )
        
        graph = self.builder.build_graph([parse_result])
        
        assert len(graph.nodes) == 2
        assert len(graph.edges) == 0
        assert graph.metadata.node_count == 2
        assert graph.metadata.edge_count == 0