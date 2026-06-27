"""
pytest配置文件

定义全局的测试配置和fixture。
所有fixture使用 codeweaver 模块路径，且字段与实际数据模型一致。
"""

import pytest
from hypothesis import settings

# 配置Hypothesis测试策略
settings.register_profile("default", max_examples=100, deadline=None)
settings.load_profile("default")


@pytest.fixture
def sample_code_element():
    """示例代码元素fixture"""
    from src.codenexus.models.core import CodeElement, ElementType

    return CodeElement(
        name="TestClass",
        type=ElementType.CLASS,
        file_path="test.py",
        line_number=1,
        end_line_number=10,
        complexity=5,
        visibility="public",
        docstring="A test class for demonstration"
    )


@pytest.fixture
def sample_relationship():
    """示例关系fixture"""
    from src.codenexus.models.core import Relationship, RelationType

    return Relationship(
        source_id="class1",
        target_id="class2",
        type=RelationType.INHERITS,
        strength=1.0,
        line_number=5,
        context="class inheritance"
    )


@pytest.fixture
def sample_code_graph():
    """示例代码图fixture"""
    from src.codenexus.models.core import (
        CodeGraph, GraphNode, GraphEdge, GraphMetadata,
        CodeElement, Relationship, ElementType, RelationType
    )

    # 创建两个代码元素（仅用于关联数据，不直接挂在节点上）
    element1 = CodeElement(
        id="elem1",
        name="ClassA",
        type=ElementType.CLASS,
        file_path="a.py",
        line_number=1
    )
    element2 = CodeElement(
        id="elem2",
        name="ClassB",
        type=ElementType.CLASS,
        file_path="b.py",
        line_number=1
    )

    # GraphNode 字段: id, label, type, properties
    node1 = GraphNode(
        id="node1",
        label="ClassA",
        type="class",
        properties={"file_path": "a.py", "element_id": element1.id}
    )
    node2 = GraphNode(
        id="node2",
        label="ClassB",
        type="class",
        properties={"file_path": "b.py", "element_id": element2.id}
    )

    # GraphEdge 字段: id, source_id, target_id, type, properties
    edge = GraphEdge(
        id="edge1",
        source_id="node1",
        target_id="node2",
        type="inherits",
        properties={"relationship_id": "rel1", "strength": 1.0}
    )

    # 创建图并添加节点和边
    graph = CodeGraph()
    graph.add_node(node1)
    graph.add_node(node2)
    graph.add_edge(edge)

    # GraphMetadata 字段: node_count, edge_count, file_count, languages, ...
    # add_node/add_edge 已自动更新 node_count 和 edge_count
    graph.metadata.languages = ["python"]
    graph.metadata.file_count = 2

    return graph


@pytest.fixture
def temp_project_dir(tmp_path):
    """临时项目目录fixture"""
    # 创建示例Python文件
    (tmp_path / "main.py").write_text("""
class Calculator:
    def add(self, a, b):
        return a + b

    def multiply(self, a, b):
        return a * b

def main():
    calc = Calculator()
    result = calc.add(1, 2)
    print(result)
""")

    (tmp_path / "utils.py").write_text("""
from main import Calculator

class AdvancedCalculator(Calculator):
    def power(self, base, exp):
        return base ** exp

    def factorial(self, n):
        if n <= 1:
            return 1
        return n * self.factorial(n - 1)
""")

    return tmp_path
