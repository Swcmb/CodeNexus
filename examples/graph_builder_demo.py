#!/usr/bin/env python3
"""
图构建器演示程序

展示如何使用GraphBuilder将代码解析结果转换为知识图谱。
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.codenexus.models.core import (
    CodeElement, ElementType, Relationship, RelationType, ParseResult
)
from src.codenexus.graph.graph_builder import GraphBuilder


def create_sample_parse_results():
    """创建示例解析结果"""
    
    # 模拟解析结果1: animal.py
    animal_elements = [
        CodeElement(
            id="animal_class",
            name="Animal",
            type=ElementType.CLASS,
            file_path="animal.py",
            line_number=1,
            complexity=3,
            docstring="基础动物类"
        ),
        CodeElement(
            id="animal_speak",
            name="speak",
            type=ElementType.METHOD,
            file_path="animal.py",
            line_number=5,
            complexity=1,
            parameters=["self"],
            docstring="动物发声方法"
        ),
        CodeElement(
            id="animal_move",
            name="move",
            type=ElementType.METHOD,
            file_path="animal.py",
            line_number=10,
            complexity=2,
            parameters=["self", "distance"],
            return_type="bool"
        )
    ]
    
    # 模拟解析结果2: dog.py
    dog_elements = [
        CodeElement(
            id="dog_class",
            name="Dog",
            type=ElementType.CLASS,
            file_path="dog.py",
            line_number=1,
            complexity=5,
            docstring="狗类，继承自Animal"
        ),
        CodeElement(
            id="dog_init",
            name="__init__",
            type=ElementType.METHOD,
            file_path="dog.py",
            line_number=5,
            complexity=2,
            parameters=["self", "name", "breed"]
        ),
        CodeElement(
            id="dog_speak",
            name="speak",
            type=ElementType.METHOD,
            file_path="dog.py",
            line_number=10,
            complexity=1,
            parameters=["self"],
            return_type="str"
        ),
        CodeElement(
            id="dog_fetch",
            name="fetch",
            type=ElementType.METHOD,
            file_path="dog.py",
            line_number=15,
            complexity=3,
            parameters=["self", "item"],
            return_type="bool"
        )
    ]
    
    # 模拟解析结果3: pet_owner.py
    owner_elements = [
        CodeElement(
            id="owner_class",
            name="PetOwner",
            type=ElementType.CLASS,
            file_path="pet_owner.py",
            line_number=1,
            complexity=4,
            docstring="宠物主人类"
        ),
        CodeElement(
            id="owner_init",
            name="__init__",
            type=ElementType.METHOD,
            file_path="pet_owner.py",
            line_number=5,
            complexity=1,
            parameters=["self", "name"]
        ),
        CodeElement(
            id="owner_adopt",
            name="adopt_pet",
            type=ElementType.METHOD,
            file_path="pet_owner.py",
            line_number=10,
            complexity=2,
            parameters=["self", "pet"],
            return_type="bool"
        )
    ]
    
    # 创建关系
    relationships = [
        # Dog继承Animal
        Relationship(
            source_id="dog_class",
            target_id="animal_class",
            type=RelationType.INHERITS,
            line_number=1,
            context="class Dog(Animal):",
            metadata={"inheritance_type": "class"}
        ),
        # Dog.speak重写Animal.speak
        Relationship(
            source_id="dog_speak",
            target_id="animal_speak",
            type=RelationType.CALLS,
            line_number=10,
            context="Override parent method",
            metadata={"override": True}
        ),
        # PetOwner依赖Dog
        Relationship(
            source_id="owner_adopt",
            target_id="dog_class",
            type=RelationType.DEPENDS,
            line_number=12,
            context="pet: Dog parameter",
            metadata={"dependency_type": "parameter"}
        ),
        # PetOwner.adopt_pet调用Dog.speak
        Relationship(
            source_id="owner_adopt",
            target_id="dog_speak",
            type=RelationType.CALLS,
            line_number=15,
            context="pet.speak() call",
            metadata={"call_count": 1}
        )
    ]
    
    # 创建解析结果
    parse_results = [
        ParseResult(
            file_path="animal.py",
            language="Python",
            elements=animal_elements,
            relationships=[],
            parse_time=0.05
        ),
        ParseResult(
            file_path="dog.py",
            language="Python",
            elements=dog_elements,
            relationships=relationships[:2],  # 继承和重写关系
            parse_time=0.08
        ),
        ParseResult(
            file_path="pet_owner.py",
            language="Python",
            elements=owner_elements,
            relationships=relationships[2:],  # 依赖和调用关系
            parse_time=0.06
        )
    ]
    
    return parse_results


def demonstrate_graph_building():
    """演示图构建过程"""
    print("=" * 60)
    print("codenexus 图构建器演示")
    print("=" * 60)
    
    # 创建图构建器
    builder = GraphBuilder()
    print(f"[OK] 创建图构建器实例")
    
    # 创建示例解析结果
    parse_results = create_sample_parse_results()
    print(f"[OK] 创建了 {len(parse_results)} 个解析结果")
    
    # 统计元素和关系
    total_elements = sum(len(result.elements) for result in parse_results)
    total_relationships = sum(len(result.relationships) for result in parse_results)
    print(f"  - 总元素数: {total_elements}")
    print(f"  - 总关系数: {total_relationships}")
    
    print("\n" + "-" * 40)
    print("开始构建知识图谱...")
    print("-" * 40)
    
    # 构建图谱
    graph = builder.build_graph(parse_results)
    
    print(f"\n[OK] 图谱构建完成!")
    print(f"  - 节点数: {len(graph.nodes)}")
    print(f"  - 边数: {len(graph.edges)}")
    print(f"  - 文件数: {graph.metadata.file_count}")
    print(f"  - 支持语言: {', '.join(graph.metadata.languages)}")
    
    return graph


def analyze_graph_structure(graph):
    """分析图结构"""
    print("\n" + "-" * 40)
    print("图结构分析")
    print("-" * 40)
    
    # 节点类型统计
    print("\n节点类型分布:")
    for node_type, count in graph.metadata.node_types.items():
        print(f"  - {node_type}: {count} 个")
    
    # 边类型统计
    print("\n关系类型分布:")
    for edge_type, count in graph.metadata.edge_types.items():
        print(f"  - {edge_type}: {count} 条")
    
    # 分析节点详情
    print("\n节点详情:")
    for i, node in enumerate(graph.nodes[:5]):  # 只显示前5个节点
        print(f"  {i+1}. {node.label} ({node.type})")
        print(f"     文件: {node.properties.get('file_path', 'N/A')}")
        print(f"     行号: {node.properties.get('line_number', 'N/A')}")
        print(f"     复杂度: {node.properties.get('complexity', 'N/A')}")
        if node.properties.get('docstring'):
            print(f"     文档: {node.properties['docstring']}")
        print()
    
    # 分析关系详情
    print("关系详情:")
    for i, edge in enumerate(graph.edges):
        source_node = graph.get_node_by_id(edge.source_id)
        target_node = graph.get_node_by_id(edge.target_id)
        
        source_name = source_node.label if source_node else "Unknown"
        target_name = target_node.label if target_node else "Unknown"
        
        print(f"  {i+1}. {source_name} --[{edge.type}]--> {target_name}")
        print(f"     上下文: {edge.properties.get('context', 'N/A')}")
        print(f"     强度: {edge.properties.get('strength', 'N/A'):.2f}")
        print()


def demonstrate_graph_queries(graph, builder):
    """演示图查询功能"""
    print("-" * 40)
    print("图查询演示")
    print("-" * 40)
    
    # 查找特定节点
    print("\n1. 查找Dog类节点:")
    dog_nodes = [node for node in graph.nodes if node.label == "Dog"]
    if dog_nodes:
        dog_node = dog_nodes[0]
        print(f"   找到节点: {dog_node.label} (ID: {dog_node.id})")
        
        # 查找连接的节点
        connected = builder.get_connected_nodes(dog_node.id, graph.edges)
        print(f"   连接的节点数: {len(connected)}")
        
        # 计算节点指标
        metrics = builder.calculate_node_metrics(dog_node.id, graph.edges)
        print(f"   入度: {metrics['in_degree']}")
        print(f"   出度: {metrics['out_degree']}")
        print(f"   总度数: {metrics['total_degree']}")
    
    # 查找继承关系
    print("\n2. 查找继承关系:")
    inheritance_edges = [edge for edge in graph.edges if edge.type == "inherits"]
    for edge in inheritance_edges:
        source_node = graph.get_node_by_id(edge.source_id)
        target_node = graph.get_node_by_id(edge.target_id)
        
        if source_node and target_node:
            print(f"   {source_node.label} 继承自 {target_node.label}")
    
    # 查找高复杂度节点
    print("\n3. 查找高复杂度节点 (复杂度 >= 3):")
    high_complexity_nodes = [
        node for node in graph.nodes 
        if node.properties.get('complexity', 0) >= 3
    ]
    for node in high_complexity_nodes:
        complexity = node.properties.get('complexity', 0)
        print(f"   {node.label}: 复杂度 {complexity}")


def main():
    """主函数"""
    try:
        # 演示图构建
        graph = demonstrate_graph_building()
        
        # 分析图结构
        analyze_graph_structure(graph)
        
        # 演示图查询
        builder = GraphBuilder()
        demonstrate_graph_queries(graph, builder)
        
        print("\n" + "=" * 60)
        print("演示完成! 图构建器功能正常运行。")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n[ERROR] 演示过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())