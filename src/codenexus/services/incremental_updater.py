"""
增量图更新服务

实现图的增量更新逻辑，识别和更新受影响的节点。
"""

from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import time

from ..models.core import (
    CodeElement, Relationship, CodeGraph, GraphNode, GraphEdge, 
    ElementType, RelationType
)
from ..graph.graph_builder import GraphBuilder
from ..database.graph_database import GraphDatabase
from ..utils.logger import setup_logger
from .file_watcher import FileChange, ChangeType as FileChangeType


logger = setup_logger(__name__)


class UpdateType(Enum):
    """更新类型"""
    ADD_NODE = "add_node"
    UPDATE_NODE = "update_node"
    REMOVE_NODE = "remove_node"
    ADD_EDGE = "add_edge"
    UPDATE_EDGE = "update_edge"
    REMOVE_EDGE = "remove_edge"


@dataclass
class GraphUpdate:
    """图更新操作"""
    update_type: UpdateType
    node_id: Optional[str] = None
    edge_id: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    timestamp: float = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()


@dataclass
class UpdateResult:
    """更新结果"""
    success: bool
    updates_applied: List[GraphUpdate]
    affected_nodes: Set[str]
    affected_edges: Set[str]
    error_message: Optional[str] = None


class DependencyAnalyzer:
    """依赖分析器
    
    分析代码元素之间的依赖关系，用于确定增量更新的影响范围。
    """
    
    def __init__(self, graph_database: GraphDatabase):
        self.graph_database = graph_database
        self._dependency_cache: Dict[str, Set[str]] = {}
        
    def analyze_dependencies(self, element_id: str) -> Set[str]:
        """分析元素的依赖关系
        
        Args:
            element_id: 代码元素ID
            
        Returns:
            依赖该元素的所有元素ID集合
        """
        if element_id in self._dependency_cache:
            return self._dependency_cache[element_id]
        
        dependencies = set()
        
        try:
            with self.graph_database.session() as session:
                # 查找直接依赖
                direct_deps = session.run("""
                    MATCH (target {element_id: $element_id})<-[r]-(dependent)
                    WHERE r.type IN ['CALLS', 'USES', 'DEPENDS_ON', 'INHERITS']
                    RETURN dependent.element_id as dep_id
                """, element_id=element_id)
                
                for record in direct_deps:
                    dependencies.add(record["dep_id"])
                
                # 查找间接依赖（递归查询，限制深度）
                indirect_deps = session.run("""
                    MATCH (target {element_id: $element_id})<-[r*1..3]-(dependent)
                    WHERE ALL(rel in r WHERE rel.type IN ['CALLS', 'USES', 'DEPENDS_ON', 'INHERITS'])
                    RETURN DISTINCT dependent.element_id as dep_id
                """, element_id=element_id)
                
                for record in indirect_deps:
                    dependencies.add(record["dep_id"])
        
        except Exception as e:
            logger.error(f"分析依赖关系失败 {element_id}: {e}")
        
        # 缓存结果
        self._dependency_cache[element_id] = dependencies
        return dependencies
    
    def clear_cache(self, element_ids: Optional[Set[str]] = None) -> None:
        """清除依赖缓存
        
        Args:
            element_ids: 要清除的元素ID集合，如果为None则清除所有缓存
        """
        if element_ids is None:
            self._dependency_cache.clear()
        else:
            for element_id in element_ids:
                self._dependency_cache.pop(element_id, None)


class IncrementalGraphUpdater:
    """增量图更新器
    
    负责处理代码变更引起的图谱增量更新。
    """
    
    def __init__(self, graph_builder: GraphBuilder, graph_database: GraphDatabase):
        self.graph_builder = graph_builder
        self.graph_database = graph_database
        self.dependency_analyzer = DependencyAnalyzer(graph_database)
        self._file_to_elements: Dict[str, Set[str]] = {}  # 文件路径 -> 元素ID集合
        self._element_to_file: Dict[str, str] = {}  # 元素ID -> 文件路径
        
        logger.info("增量图更新器已初始化")
    
    def update_from_file_changes(
        self, 
        file_path: str, 
        elements: List[CodeElement], 
        relationships: List[Relationship]
    ) -> UpdateResult:
        """根据文件变更更新图谱
        
        Args:
            file_path: 变更的文件路径
            elements: 新的代码元素列表（空列表表示文件被删除）
            relationships: 新的关系列表
            
        Returns:
            更新结果
        """
        logger.info(f"开始处理文件变更: {file_path}")
        
        try:
            if not elements:
                # 文件被删除，移除相关元素
                return self._handle_file_deletion(file_path)
            else:
                # 文件被创建或修改，更新相关元素
                return self._handle_file_update(file_path, elements, relationships)
        
        except Exception as e:
            logger.error(f"处理文件变更失败 {file_path}: {e}")
            return UpdateResult(
                success=False,
                updates_applied=[],
                affected_nodes=set(),
                affected_edges=set(),
                error_message=str(e)
            )
    
    def _handle_file_deletion(self, file_path: str) -> UpdateResult:
        """处理文件删除"""
        logger.debug(f"处理文件删除: {file_path}")
        
        updates_applied = []
        affected_nodes = set()
        affected_edges = set()
        
        # 获取文件中的所有元素
        element_ids = self._file_to_elements.get(file_path, set())
        
        if not element_ids:
            logger.debug(f"文件 {file_path} 中没有找到元素")
            return UpdateResult(
                success=True,
                updates_applied=[],
                affected_nodes=set(),
                affected_edges=set()
            )
        
        # 分析依赖关系
        all_affected_elements = set(element_ids)
        for element_id in element_ids:
            dependencies = self.dependency_analyzer.analyze_dependencies(element_id)
            all_affected_elements.update(dependencies)
        
        # 删除节点和边
        with self.graph_database.session() as session:
            with session.begin_transaction() as tx:
                try:
                    # 删除相关的边
                    for element_id in element_ids:
                        edge_result = tx.run("""
                            MATCH (n {element_id: $element_id})-[r]-()
                            DELETE r
                            RETURN count(r) as deleted_edges
                        """, element_id=element_id)
                        
                        for record in edge_result:
                            deleted_count = record.get("deleted_edges", 0)
                            if deleted_count > 0:
                                updates_applied.append(GraphUpdate(
                                    update_type=UpdateType.REMOVE_EDGE,
                                    data={"element_id": element_id, "count": deleted_count}
                                ))
                    
                    # 删除节点
                    for element_id in element_ids:
                        node_result = tx.run("""
                            MATCH (n {element_id: $element_id})
                            DELETE n
                            RETURN n.id as node_id
                        """, element_id=element_id)
                        
                        for record in node_result:
                            node_id = record["node_id"]
                            affected_nodes.add(node_id)
                            updates_applied.append(GraphUpdate(
                                update_type=UpdateType.REMOVE_NODE,
                                node_id=node_id,
                                data={"element_id": element_id}
                            ))
                    
                    tx.commit()
                    
                except Exception as e:
                    tx.rollback()
                    raise e
        
        # 更新内部映射
        for element_id in element_ids:
            self._element_to_file.pop(element_id, None)
        self._file_to_elements.pop(file_path, None)
        
        # 清除依赖缓存
        self.dependency_analyzer.clear_cache(all_affected_elements)
        
        logger.info(f"文件删除处理完成: {file_path}, 影响 {len(affected_nodes)} 个节点")
        
        return UpdateResult(
            success=True,
            updates_applied=updates_applied,
            affected_nodes=affected_nodes,
            affected_edges=affected_edges
        )
    
    def _handle_file_update(
        self, 
        file_path: str, 
        elements: List[CodeElement], 
        relationships: List[Relationship]
    ) -> UpdateResult:
        """处理文件更新（创建或修改）"""
        logger.debug(f"处理文件更新: {file_path}")
        
        updates_applied = []
        affected_nodes = set()
        affected_edges = set()
        
        # 获取文件中原有的元素
        old_element_ids = self._file_to_elements.get(file_path, set())
        new_element_ids = {element.id for element in elements}
        
        # 分析变更
        added_elements = new_element_ids - old_element_ids
        removed_elements = old_element_ids - new_element_ids
        updated_elements = old_element_ids & new_element_ids
        
        logger.debug(f"元素变更统计 - 新增: {len(added_elements)}, 删除: {len(removed_elements)}, 更新: {len(updated_elements)}")
        
        # 处理删除的元素
        if removed_elements:
            for element_id in removed_elements:
                result = self._remove_element(element_id)
                updates_applied.extend(result.updates_applied)
                affected_nodes.update(result.affected_nodes)
                affected_edges.update(result.affected_edges)
        
        # 处理新增和更新的元素
        elements_to_process = [e for e in elements if e.id in added_elements or e.id in updated_elements]
        if elements_to_process:
            # 使用图构建器创建节点
            new_nodes = self.graph_builder.create_nodes(elements_to_process)
            
            # 存储或更新节点
            for node in new_nodes:
                element_id = None
                for element in elements_to_process:
                    if self.graph_builder.element_to_node.get(element.id) == node.id:
                        element_id = element.id
                        break
                
                if element_id in added_elements:
                    result = self._add_node(node, element_id)
                else:
                    result = self._update_node(node, element_id)
                
                updates_applied.extend(result.updates_applied)
                affected_nodes.update(result.affected_nodes)
        
        # 处理关系
        if relationships:
            new_edges = self.graph_builder.create_edges(relationships)
            for edge in new_edges:
                result = self._add_or_update_edge(edge)
                updates_applied.extend(result.updates_applied)
                affected_edges.update(result.affected_edges)
        
        # 更新内部映射
        self._file_to_elements[file_path] = new_element_ids
        for element in elements:
            self._element_to_file[element.id] = file_path
        
        # 清除相关的依赖缓存
        all_affected = new_element_ids | old_element_ids
        self.dependency_analyzer.clear_cache(all_affected)
        
        logger.info(f"文件更新处理完成: {file_path}, 影响 {len(affected_nodes)} 个节点, {len(affected_edges)} 条边")
        
        return UpdateResult(
            success=True,
            updates_applied=updates_applied,
            affected_nodes=affected_nodes,
            affected_edges=affected_edges
        )
    
    def _remove_element(self, element_id: str) -> UpdateResult:
        """移除单个元素"""
        updates_applied = []
        affected_nodes = set()
        affected_edges = set()
        
        with self.graph_database.session() as session:
            with session.begin_transaction() as tx:
                try:
                    # 删除相关边
                    edge_result = tx.run("""
                        MATCH (n {element_id: $element_id})-[r]-()
                        DELETE r
                        RETURN count(r) as deleted_edges
                    """, element_id=element_id)
                    
                    for record in edge_result:
                        deleted_count = record["deleted_edges"]
                        if deleted_count > 0:
                            updates_applied.append(GraphUpdate(
                                update_type=UpdateType.REMOVE_EDGE,
                                data={"element_id": element_id, "count": deleted_count}
                            ))
                    
                    # 删除节点
                    node_result = tx.run("""
                        MATCH (n {element_id: $element_id})
                        DELETE n
                        RETURN n.id as node_id
                    """, element_id=element_id)
                    
                    for record in node_result:
                        node_id = record["node_id"]
                        affected_nodes.add(node_id)
                        updates_applied.append(GraphUpdate(
                            update_type=UpdateType.REMOVE_NODE,
                            node_id=node_id,
                            data={"element_id": element_id}
                        ))
                    
                    tx.commit()
                    
                except Exception as e:
                    tx.rollback()
                    raise e
        
        return UpdateResult(
            success=True,
            updates_applied=updates_applied,
            affected_nodes=affected_nodes,
            affected_edges=affected_edges
        )
    
    def _add_node(self, node: GraphNode, element_id: str) -> UpdateResult:
        """添加新节点"""
        updates_applied = []
        affected_nodes = {node.id}
        
        with self.graph_database.session() as session:
            with session.begin_transaction() as tx:
                try:
                    # 创建节点
                    tx.run("""
                        CREATE (n:CodeElement {
                            id: $id,
                            element_id: $element_id,
                            name: $name,
                            type: $type,
                            file_path: $file_path,
                            line_number: $line_number,
                            properties: $properties
                        })
                    """, 
                    id=node.id,
                    element_id=element_id,
                    name=node.name,
                    type=node.type,
                    file_path=node.file_path,
                    line_number=node.line_number,
                    properties=node.properties
                    )
                    
                    updates_applied.append(GraphUpdate(
                        update_type=UpdateType.ADD_NODE,
                        node_id=node.id,
                        data={"element_id": element_id}
                    ))
                    
                    tx.commit()
                    
                except Exception as e:
                    tx.rollback()
                    raise e
        
        return UpdateResult(
            success=True,
            updates_applied=updates_applied,
            affected_nodes=affected_nodes,
            affected_edges=set()
        )
    
    def _update_node(self, node: GraphNode, element_id: str) -> UpdateResult:
        """更新现有节点"""
        updates_applied = []
        affected_nodes = {node.id}
        
        with self.graph_database.session() as session:
            with session.begin_transaction() as tx:
                try:
                    # 更新节点属性
                    tx.run("""
                        MATCH (n {element_id: $element_id})
                        SET n.name = $name,
                            n.type = $type,
                            n.file_path = $file_path,
                            n.line_number = $line_number,
                            n.properties = $properties
                    """,
                    element_id=element_id,
                    name=node.name,
                    type=node.type,
                    file_path=node.file_path,
                    line_number=node.line_number,
                    properties=node.properties
                    )
                    
                    updates_applied.append(GraphUpdate(
                        update_type=UpdateType.UPDATE_NODE,
                        node_id=node.id,
                        data={"element_id": element_id}
                    ))
                    
                    tx.commit()
                    
                except Exception as e:
                    tx.rollback()
                    raise e
        
        return UpdateResult(
            success=True,
            updates_applied=updates_applied,
            affected_nodes=affected_nodes,
            affected_edges=set()
        )
    
    def _add_or_update_edge(self, edge: GraphEdge) -> UpdateResult:
        """添加或更新边"""
        updates_applied = []
        affected_edges = {edge.id}
        
        with self.graph_database.session() as session:
            with session.begin_transaction() as tx:
                try:
                    # 检查边是否已存在
                    existing = tx.run("""
                        MATCH (source {element_id: $source_id})-[r {type: $type}]->(target {element_id: $target_id})
                        RETURN r.id as edge_id
                    """,
                    source_id=edge.source_id,
                    target_id=edge.target_id,
                    type=edge.type
                    )
                    
                    existing_edge = existing.single()
                    
                    if existing_edge:
                        # 更新现有边
                        tx.run("""
                            MATCH (source {element_id: $source_id})-[r {type: $type}]->(target {element_id: $target_id})
                            SET r.properties = $properties
                        """,
                        source_id=edge.source_id,
                        target_id=edge.target_id,
                        type=edge.type,
                        properties=edge.properties
                        )
                        
                        updates_applied.append(GraphUpdate(
                            update_type=UpdateType.UPDATE_EDGE,
                            edge_id=edge.id
                        ))
                    else:
                        # 创建新边
                        tx.run("""
                            MATCH (source {element_id: $source_id}), (target {element_id: $target_id})
                            CREATE (source)-[r:RELATIONSHIP {
                                id: $id,
                                type: $type,
                                properties: $properties
                            }]->(target)
                        """,
                        source_id=edge.source_id,
                        target_id=edge.target_id,
                        id=edge.id,
                        type=edge.type,
                        properties=edge.properties
                        )
                        
                        updates_applied.append(GraphUpdate(
                            update_type=UpdateType.ADD_EDGE,
                            edge_id=edge.id
                        ))
                    
                    tx.commit()
                    
                except Exception as e:
                    tx.rollback()
                    raise e
        
        return UpdateResult(
            success=True,
            updates_applied=updates_applied,
            affected_nodes=set(),
            affected_edges=affected_edges
        )
    
    def get_affected_elements(self, element_ids: Set[str]) -> Set[str]:
        """获取受影响的所有元素
        
        Args:
            element_ids: 直接变更的元素ID集合
            
        Returns:
            所有受影响的元素ID集合（包括依赖关系）
        """
        affected = set(element_ids)
        
        for element_id in element_ids:
            dependencies = self.dependency_analyzer.analyze_dependencies(element_id)
            affected.update(dependencies)
        
        return affected
    
    def rebuild_file_mappings(self) -> None:
        """重建文件到元素的映射关系"""
        logger.info("重建文件到元素的映射关系")
        
        self._file_to_elements.clear()
        self._element_to_file.clear()
        
        try:
            with self.graph_database.session() as session:
                result = session.run("""
                    MATCH (n:CodeElement)
                    RETURN n.element_id as element_id, n.file_path as file_path
                """)
                
                for record in result:
                    element_id = record["element_id"]
                    file_path = record["file_path"]
                    
                    if file_path:
                        self._element_to_file[element_id] = file_path
                        
                        if file_path not in self._file_to_elements:
                            self._file_to_elements[file_path] = set()
                        self._file_to_elements[file_path].add(element_id)
        
        except Exception as e:
            logger.error(f"重建文件映射失败: {e}")
        
        logger.info(f"重建完成，映射 {len(self._file_to_elements)} 个文件，{len(self._element_to_file)} 个元素")


def create_incremental_updater(
    graph_builder: GraphBuilder, 
    graph_database: GraphDatabase
) -> IncrementalGraphUpdater:
    """创建增量图更新器的便捷函数"""
    return IncrementalGraphUpdater(graph_builder, graph_database)