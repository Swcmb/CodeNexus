"""
关系提取器

专门用于从AST中提取代码元素之间的关系。
"""

import re
from typing import Dict, List, Optional, Set, Tuple

from tree_sitter import Node

from ..models.core import CodeElement, ElementType, Relationship, RelationType
from ..utils.logger import parser_logger


class RelationshipExtractor:
    """关系提取器类"""
    
    def __init__(self):
        """初始化关系提取器"""
        self.element_map: Dict[str, CodeElement] = {}
        self.file_imports: Dict[str, Set[str]] = {}
        self.current_file: Optional[str] = None
        self.current_class: Optional[str] = None
        self.current_function: Optional[str] = None
    
    def extract_relationships(
        self, 
        ast: Node, 
        elements: List[CodeElement], 
        file_path: str
    ) -> List[Relationship]:
        """
        从AST提取关系
        
        Args:
            ast: AST根节点
            elements: 代码元素列表
            file_path: 当前文件路径
            
        Returns:
            关系列表
        """
        self.current_file = file_path
        self.element_map = {elem.id: elem for elem in elements}
        
        # 创建名称到元素的映射，便于查找
        self.name_to_elements = {}
        for elem in elements:
            if elem.name not in self.name_to_elements:
                self.name_to_elements[elem.name] = []
            self.name_to_elements[elem.name].append(elem)
        
        relationships = []
        
        # 提取各种类型的关系
        relationships.extend(self._extract_inheritance_relationships(ast))
        relationships.extend(self._extract_call_relationships(ast))
        relationships.extend(self._extract_import_relationships(ast))
        relationships.extend(self._extract_dependency_relationships(ast))
        relationships.extend(self._extract_composition_relationships(ast))
        
        parser_logger.info(f"从 {file_path} 提取到 {len(relationships)} 个关系")
        return relationships
    
    def _extract_inheritance_relationships(self, node: Node) -> List[Relationship]:
        """提取继承关系"""
        relationships = []
        
        def traverse_for_inheritance(n: Node, parent_class: Optional[str] = None):
            if n.type in ["class_definition", "class_declaration"]:
                class_name = self._get_node_name(n)
                if class_name:
                    # 查找继承的父类
                    parent_classes = self._find_parent_classes(n)
                    for parent_class_name in parent_classes:
                        rel = self._create_inheritance_relationship(
                            class_name, parent_class_name, n
                        )
                        if rel:
                            relationships.append(rel)
                    
                    # 递归处理子节点，传递当前类名
                    for child in n.children:
                        traverse_for_inheritance(child, class_name)
            else:
                # 继续遍历子节点
                for child in n.children:
                    traverse_for_inheritance(child, parent_class)
        
        traverse_for_inheritance(node)
        return relationships
    
    def _extract_call_relationships(self, node: Node) -> List[Relationship]:
        """提取函数调用关系"""
        relationships = []
        
        def traverse_for_calls(n: Node, current_context: Optional[str] = None):
            # 更新当前上下文
            if n.type in ["function_definition", "method_declaration"]:
                func_name = self._get_node_name(n)
                if func_name:
                    current_context = func_name
            elif n.type in ["class_definition", "class_declaration"]:
                class_name = self._get_node_name(n)
                if class_name:
                    current_context = class_name
            
            # 查找函数调用
            if n.type in ["call", "method_invocation", "call_expression"]:
                rel = self._create_call_relationship(n, current_context)
                if rel:
                    relationships.append(rel)
            
            # 递归处理子节点
            for child in n.children:
                traverse_for_calls(child, current_context)
        
        traverse_for_calls(node)
        return relationships
    
    def _extract_import_relationships(self, node: Node) -> List[Relationship]:
        """提取导入关系"""
        relationships = []
        
        def traverse_for_imports(n: Node):
            if n.type in ["import_statement", "import_declaration", "import_from_statement"]:
                rel = self._create_import_relationship(n)
                if rel:
                    relationships.append(rel)
            
            # 递归处理子节点
            for child in n.children:
                traverse_for_imports(child)
        
        traverse_for_imports(node)
        return relationships
    
    def _extract_dependency_relationships(self, node: Node) -> List[Relationship]:
        """提取依赖关系（如类型注解、变量类型等）"""
        relationships = []
        
        def traverse_for_dependencies(n: Node):
            # 查找类型注解
            if n.type in ["type_annotation", "type"]:
                rel = self._create_dependency_relationship(n)
                if rel:
                    relationships.append(rel)
            
            # 查找变量声明中的类型
            elif n.type in ["variable_declaration", "field_declaration"]:
                rel = self._create_variable_dependency_relationship(n)
                if rel:
                    relationships.append(rel)
            
            # 递归处理子节点
            for child in n.children:
                traverse_for_dependencies(child)
        
        traverse_for_dependencies(node)
        return relationships
    
    def _extract_composition_relationships(self, node: Node) -> List[Relationship]:
        """提取组合关系（如类中的字段）"""
        relationships = []
        
        def traverse_for_composition(n: Node, current_class: Optional[str] = None):
            if n.type in ["class_definition", "class_declaration"]:
                class_name = self._get_node_name(n)
                if class_name:
                    current_class = class_name
            
            # 查找字段声明
            elif n.type in ["field_declaration", "assignment"] and current_class:
                rel = self._create_composition_relationship(n, current_class)
                if rel:
                    relationships.append(rel)
            
            # 递归处理子节点
            for child in n.children:
                traverse_for_composition(child, current_class)
        
        traverse_for_composition(node)
        return relationships
    
    def _find_parent_classes(self, class_node: Node) -> List[str]:
        """查找类的父类"""
        parent_classes = []
        
        for child in class_node.children:
            if child.type in ["superclass", "argument_list", "superclasses", "extends_clause"]:
                # 处理不同语言的继承语法
                parent_classes.extend(self._extract_class_names_from_node(child))
        
        return parent_classes
    
    def _extract_class_names_from_node(self, node: Node) -> List[str]:
        """从节点中提取类名"""
        class_names = []
        
        def extract_names(n: Node):
            if n.type == "identifier":
                class_names.append(n.text.decode('utf8'))
            elif n.type in ["dotted_name", "qualified_name"]:
                # 处理如 package.ClassName 的情况
                full_name = n.text.decode('utf8')
                # 取最后一部分作为类名
                class_names.append(full_name.split('.')[-1])
            else:
                for child in n.children:
                    extract_names(child)
        
        extract_names(node)
        return class_names
    
    def _get_node_name(self, node: Node) -> Optional[str]:
        """获取节点的名称"""
        for child in node.children:
            if child.type in ["identifier", "name"]:
                return child.text.decode('utf8')
        return None
    
    def _create_inheritance_relationship(
        self, 
        child_class: str, 
        parent_class: str, 
        node: Node
    ) -> Optional[Relationship]:
        """创建继承关系"""
        child_element = self._find_element_by_name(child_class, ElementType.CLASS)
        parent_element = self._find_element_by_name(parent_class, ElementType.CLASS)
        
        if child_element and parent_element:
            return Relationship(
                source_id=child_element.id,
                target_id=parent_element.id,
                type=RelationType.INHERITS,
                line_number=node.start_point[0] + 1,
                context=f"Class {child_class} inherits from {parent_class}",
                metadata={
                    "child_class": child_class,
                    "parent_class": parent_class,
                    "file_path": self.current_file
                }
            )
        
        return None
    
    def _create_call_relationship(
        self, 
        call_node: Node, 
        caller_context: Optional[str]
    ) -> Optional[Relationship]:
        """创建函数调用关系"""
        # 提取被调用的函数名
        callee_name = self._extract_function_name_from_call(call_node)
        if not callee_name:
            return None
        
        # 查找调用者
        caller_element = None
        if caller_context:
            caller_element = self._find_element_by_name(
                caller_context, 
                [ElementType.FUNCTION, ElementType.METHOD, ElementType.CLASS]
            )
        
        # 查找被调用者
        callee_element = self._find_element_by_name(
            callee_name, 
            [ElementType.FUNCTION, ElementType.METHOD]
        )
        
        if caller_element and callee_element:
            return Relationship(
                source_id=caller_element.id,
                target_id=callee_element.id,
                type=RelationType.CALLS,
                line_number=call_node.start_point[0] + 1,
                context=f"{caller_context} calls {callee_name}",
                metadata={
                    "caller": caller_context,
                    "callee": callee_name,
                    "call_type": self._determine_call_type(call_node),
                    "file_path": self.current_file
                }
            )
        
        return None
    
    def _create_import_relationship(self, import_node: Node) -> Optional[Relationship]:
        """创建导入关系"""
        import_info = self._extract_import_info(import_node)
        if not import_info:
            return None
        
        module_name, imported_items = import_info
        
        # 创建模块导入关系
        return Relationship(
            source_id="current_module",  # 当前模块
            target_id=module_name,
            type=RelationType.IMPORTS,
            line_number=import_node.start_point[0] + 1,
            context=f"Import {module_name}",
            metadata={
                "module": module_name,
                "imported_items": imported_items,
                "import_type": self._determine_import_type(import_node),
                "file_path": self.current_file
            }
        )
    
    def _create_dependency_relationship(self, type_node: Node) -> Optional[Relationship]:
        """创建依赖关系"""
        type_name = self._extract_type_name(type_node)
        if not type_name:
            return None
        
        # 查找使用该类型的元素和类型定义
        type_element = self._find_element_by_name(type_name, ElementType.CLASS)
        
        if type_element:
            return Relationship(
                source_id="current_context",  # 需要更精确的上下文
                target_id=type_element.id,
                type=RelationType.DEPENDS,
                line_number=type_node.start_point[0] + 1,
                context=f"Depends on type {type_name}",
                metadata={
                    "type_name": type_name,
                    "dependency_type": "type_annotation",
                    "file_path": self.current_file
                }
            )
        
        return None
    
    def _create_variable_dependency_relationship(self, var_node: Node) -> Optional[Relationship]:
        """创建变量依赖关系"""
        # 简化实现，主要用于演示
        return None
    
    def _create_composition_relationship(
        self, 
        field_node: Node, 
        class_name: str
    ) -> Optional[Relationship]:
        """创建组合关系"""
        field_type = self._extract_field_type(field_node)
        if not field_type:
            return None
        
        class_element = self._find_element_by_name(class_name, ElementType.CLASS)
        type_element = self._find_element_by_name(field_type, ElementType.CLASS)
        
        if class_element and type_element:
            return Relationship(
                source_id=class_element.id,
                target_id=type_element.id,
                type=RelationType.COMPOSES,
                line_number=field_node.start_point[0] + 1,
                context=f"Class {class_name} composes {field_type}",
                metadata={
                    "container_class": class_name,
                    "component_type": field_type,
                    "composition_type": "field",
                    "file_path": self.current_file
                }
            )
        
        return None
    
    def _extract_function_name_from_call(self, call_node: Node) -> Optional[str]:
        """从函数调用节点提取函数名"""
        for child in call_node.children:
            if child.type == "identifier":
                return child.text.decode('utf8')
            elif child.type in ["member_expression", "attribute"]:
                # 处理方法调用，如 obj.method()
                return self._extract_method_name(child)
        
        return None
    
    def _extract_method_name(self, member_node: Node) -> Optional[str]:
        """从成员表达式中提取方法名"""
        # 查找最后一个标识符作为方法名
        for child in reversed(member_node.children):
            if child.type == "identifier":
                return child.text.decode('utf8')
        
        return None
    
    def _extract_import_info(self, import_node: Node) -> Optional[Tuple[str, List[str]]]:
        """提取导入信息"""
        module_name = None
        imported_items = []
        
        for child in import_node.children:
            if child.type in ["dotted_name", "identifier"]:
                module_name = child.text.decode('utf8')
            elif child.type == "import_list":
                imported_items = self._extract_imported_items(child)
        
        if module_name:
            return module_name, imported_items
        
        return None
    
    def _extract_imported_items(self, import_list_node: Node) -> List[str]:
        """提取导入项列表"""
        items = []
        
        for child in import_list_node.children:
            if child.type == "identifier":
                items.append(child.text.decode('utf8'))
        
        return items
    
    def _extract_type_name(self, type_node: Node) -> Optional[str]:
        """提取类型名称"""
        for child in type_node.children:
            if child.type == "identifier":
                return child.text.decode('utf8')
        
        return None
    
    def _extract_field_type(self, field_node: Node) -> Optional[str]:
        """提取字段类型"""
        # 简化实现，查找类型注解或推断类型
        for child in field_node.children:
            if child.type in ["type_annotation", "type"]:
                return self._extract_type_name(child)
        
        return None
    
    def _determine_call_type(self, call_node: Node) -> str:
        """确定调用类型"""
        if call_node.type == "method_invocation":
            return "method_call"
        elif call_node.type == "call_expression":
            return "function_call"
        else:
            return "call"
    
    def _determine_import_type(self, import_node: Node) -> str:
        """确定导入类型"""
        if import_node.type == "import_from_statement":
            return "from_import"
        elif import_node.type == "import_statement":
            return "direct_import"
        else:
            return "import"
    
    def _find_element_by_name(
        self, 
        name: str, 
        element_types: Optional[List[ElementType]] = None
    ) -> Optional[CodeElement]:
        """根据名称查找代码元素"""
        if isinstance(element_types, ElementType):
            element_types = [element_types]
        
        if name in self.name_to_elements:
            candidates = self.name_to_elements[name]
            
            if element_types:
                # 过滤指定类型的元素
                filtered = [elem for elem in candidates if elem.type in element_types]
                if filtered:
                    return filtered[0]  # 返回第一个匹配的元素
            else:
                return candidates[0]  # 返回第一个元素
        
        return None
    
    def extract_cross_file_relationships(
        self, 
        all_elements: Dict[str, List[CodeElement]]
    ) -> List[Relationship]:
        """提取跨文件关系"""
        relationships = []
        
        # 构建全局名称映射
        global_name_map = {}
        for file_path, elements in all_elements.items():
            for element in elements:
                if element.name not in global_name_map:
                    global_name_map[element.name] = []
                global_name_map[element.name].append((element, file_path))
        
        # 分析跨文件引用
        for file_path, elements in all_elements.items():
            for element in elements:
                # 查找可能的跨文件引用
                cross_refs = self._find_cross_file_references(
                    element, global_name_map, file_path
                )
                relationships.extend(cross_refs)
        
        return relationships
    
    def _find_cross_file_references(
        self, 
        element: CodeElement, 
        global_name_map: Dict[str, List[Tuple[CodeElement, str]]], 
        current_file: str
    ) -> List[Relationship]:
        """查找跨文件引用"""
        relationships = []
        
        # 简化实现：基于名称匹配查找可能的跨文件引用
        # 实际实现需要更复杂的分析
        
        return relationships