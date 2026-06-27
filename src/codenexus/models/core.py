"""
核心数据模型

定义codenexus系统的核心数据结构和类型。
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set
from uuid import uuid4


class ElementType(Enum):
    """代码元素类型枚举"""
    CLASS = "class"
    METHOD = "method"
    FUNCTION = "function"
    VARIABLE = "variable"
    FIELD = "field"
    INTERFACE = "interface"
    MODULE = "module"
    NAMESPACE = "namespace"
    PACKAGE = "package"
    ENUM = "enum"
    STRUCT = "struct"


class RelationType(Enum):
    """关系类型枚举"""
    INHERITS = "inherits"
    IMPLEMENTS = "implements"
    CALLS = "calls"
    DEPENDS = "depends"
    COMPOSES = "composes"
    AGGREGATES = "aggregates"
    ACCESSES = "accesses"
    DEFINES = "defines"
    IMPORTS = "imports"
    EXTENDS = "extends"


@dataclass
class CodeElement:
    """代码元素数据模型"""
    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    type: ElementType = ElementType.CLASS
    file_path: str = ""
    line_number: int = 0
    end_line_number: int = 0
    complexity: int = 0
    visibility: str = "public"  # public, private, protected, internal
    is_abstract: bool = False
    is_static: bool = False
    parameters: List[str] = field(default_factory=list)
    return_type: Optional[str] = None
    docstring: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self) -> None:
        """后初始化处理"""
        if self.end_line_number == 0:
            self.end_line_number = self.line_number


@dataclass
class Relationship:
    """关系数据模型"""
    id: str = field(default_factory=lambda: str(uuid4()))
    source_id: str = ""
    target_id: str = ""
    type: RelationType = RelationType.CALLS
    strength: float = 1.0  # 关系强度 0-1
    line_number: int = 0
    context: Optional[str] = None  # 关系上下文信息
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GraphNode:
    """图节点数据模型"""
    id: str = field(default_factory=lambda: str(uuid4()))
    label: str = ""
    type: str = ""
    properties: Dict[str, Any] = field(default_factory=dict)
    
    def get_property(self, key: str, default: Any = None) -> Any:
        """获取节点属性"""
        return self.properties.get(key, default)
    
    def set_property(self, key: str, value: Any) -> None:
        """设置节点属性"""
        self.properties[key] = value
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "id": self.id,
            "label": self.label,
            "type": self.type,
            "properties": self.properties
        }


@dataclass
class GraphEdge:
    """图边数据模型"""
    id: str = field(default_factory=lambda: str(uuid4()))
    source_id: str = ""
    target_id: str = ""
    type: str = ""
    properties: Dict[str, Any] = field(default_factory=dict)
    
    def get_property(self, key: str, default: Any = None) -> Any:
        """获取边属性"""
        return self.properties.get(key, default)
    
    def set_property(self, key: str, value: Any) -> None:
        """设置边属性"""
        self.properties[key] = value
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "id": self.id,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "type": self.type,
            "properties": self.properties
        }


@dataclass
class GraphMetadata:
    """图元数据"""
    node_count: int = 0
    edge_count: int = 0
    file_count: int = 0
    languages: List[str] = field(default_factory=list)
    node_types: Dict[str, int] = field(default_factory=dict)
    edge_types: Dict[str, int] = field(default_factory=dict)
    creation_time: Optional[str] = None
    version: str = "1.0"
    
    def __post_init__(self) -> None:
        """后初始化处理"""
        if self.creation_time is None:
            from datetime import datetime
            self.creation_time = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "node_count": self.node_count,
            "edge_count": self.edge_count,
            "file_count": self.file_count,
            "languages": self.languages,
            "node_types": self.node_types,
            "edge_types": self.edge_types,
            "creation_time": self.creation_time,
            "version": self.version
        }


@dataclass
class CodeGraph:
    """代码知识图谱数据模型"""
    id: str = field(default_factory=lambda: str(uuid4()))
    nodes: List[GraphNode] = field(default_factory=list)
    edges: List[GraphEdge] = field(default_factory=list)
    metadata: GraphMetadata = field(default_factory=GraphMetadata)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "id": self.id,
            "nodes": [node.__dict__ for node in self.nodes],
            "edges": [edge.__dict__ for edge in self.edges],
            "metadata": self.metadata.__dict__
        }
    
    def add_node(self, node: GraphNode) -> None:
        """添加节点"""
        self.nodes.append(node)
        self.metadata.node_count = len(self.nodes)
    
    def add_edge(self, edge: GraphEdge) -> None:
        """添加边"""
        self.edges.append(edge)
        self.metadata.edge_count = len(self.edges)
    
    def get_node_by_id(self, node_id: str) -> Optional[GraphNode]:
        """根据ID获取节点"""
        for node in self.nodes:
            if node.id == node_id:
                return node
        return None
    
    def get_edge_by_id(self, edge_id: str) -> Optional[GraphEdge]:
        """根据ID获取边"""
        for edge in self.edges:
            if edge.id == edge_id:
                return edge
        return None
    
    def get_edges_by_source(self, source_id: str) -> List[GraphEdge]:
        """获取指定源节点的所有出边"""
        return [edge for edge in self.edges if edge.source_id == source_id]
    
    def get_edges_by_target(self, target_id: str) -> List[GraphEdge]:
        """获取指定目标节点的所有入边"""
        return [edge for edge in self.edges if edge.target_id == target_id]
    
    def remove_node(self, node_id: str) -> None:
        """移除节点及其相关边

        从 nodes 列表中删除指定节点，并清除所有与该节点关联的边。
        """
        # 检查节点是否存在
        target_node = self.get_node_by_id(node_id)
        if target_node is None:
            return

        # 收集与该节点关联的所有边ID（出边 + 入边）
        related_edge_ids = {
            edge.id
            for edge in self.edges
            if edge.source_id == node_id or edge.target_id == node_id
        }

        # 移除关联边（基于列表推导过滤）
        self.edges = [
            edge for edge in self.edges if edge.id not in related_edge_ids
        ]

        # 移除节点（基于列表推导过滤）
        self.nodes = [
            node for node in self.nodes if node.id != node_id
        ]

        # 同步元数据计数
        self.metadata.node_count = len(self.nodes)
        self.metadata.edge_count = len(self.edges)

    def remove_edge(self, edge_id: str) -> None:
        """移除边

        从 edges 列表中删除指定边，无需修改节点属性。
        """
        # 检查边是否存在
        target_edge = self.get_edge_by_id(edge_id)
        if target_edge is None:
            return

        # 基于列表推导过滤移除该边
        self.edges = [
            edge for edge in self.edges if edge.id != edge_id
        ]

        # 同步元数据计数
        self.metadata.edge_count = len(self.edges)

    def get_neighbors(self, node_id: str, direction: str = "both") -> List[str]:
        """获取邻居节点ID列表

        Args:
            node_id: 目标节点ID
            direction: 方向，"outgoing"（出边邻居）、"incoming"（入边邻居）、"both"（双向）

        Returns:
            去重后的邻居节点ID列表
        """
        # 检查节点是否存在
        target_node = self.get_node_by_id(node_id)
        if target_node is None:
            return []

        neighbors: Set[str] = set()

        if direction in ("both", "outgoing"):
            # 出边：当前节点作为 source，邻居为 target
            neighbors.update(
                edge.target_id
                for edge in self.edges
                if edge.source_id == node_id
            )

        if direction in ("both", "incoming"):
            # 入边：当前节点作为 target，邻居为 source
            neighbors.update(
                edge.source_id
                for edge in self.edges
                if edge.target_id == node_id
            )

        return list(neighbors)


@dataclass
class ParseResult:
    """解析结果数据模型"""
    file_path: str = ""
    language: str = ""
    elements: List[CodeElement] = field(default_factory=list)
    relationships: List[Relationship] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    parse_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        def serialize_element(elem: CodeElement) -> Dict[str, Any]:
            data = elem.__dict__.copy()
            if 'type' in data and hasattr(data['type'], 'value'):
                data['type'] = data['type'].value
            return data

        def serialize_relationship(rel: Relationship) -> Dict[str, Any]:
            data = rel.__dict__.copy()
            if 'type' in data and hasattr(data['type'], 'value'):
                data['type'] = data['type'].value
            return data
        
        return {
            "file_path": self.file_path,
            "language": self.language,
            "elements": [serialize_element(elem) for elem in self.elements],
            "relationships": [serialize_relationship(rel) for rel in self.relationships],
            "errors": self.errors,
            "warnings": self.warnings,
            "parse_time": self.parse_time,
            "metadata": self.metadata
        }


@dataclass
class FileParseResult:
    """单文件解析结果"""
    file_path: str = ""
    success: bool = True
    parse_result: Optional[ParseResult] = None
    error_message: Optional[str] = None
    parse_time: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "file_path": self.file_path,
            "success": self.success,
            "parse_result": self.parse_result.to_dict() if self.parse_result else None,
            "error_message": self.error_message,
            "parse_time": self.parse_time
        }