"""
Tree-sitter解析器包装器

提供基于Tree-sitter的多语言代码解析功能。
"""

import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import tree_sitter_java as tsjava
import tree_sitter_javascript as tsjs
import tree_sitter_python as tspython
from tree_sitter import Language, Node, Parser, Tree

from ..exceptions import ParseError
from ..interfaces import CodeParserInterface
from ..models.core import (
    CodeElement,
    ElementType,
    FileParseResult,
    ParseResult,
    Relationship,
    RelationType,
)
from ..utils.logger import parser_logger
from ..utils.error_handler import error_handler, with_circuit_breaker
from .relationship_extractor import RelationshipExtractor


class TreeSitterParser(CodeParserInterface):
    """Tree-sitter解析器包装器"""
    
    def __init__(self):
        """初始化解析器"""
        self.parsers: Dict[str, Parser] = {}
        self.languages: Dict[str, Language] = {}
        self.relationship_extractor = RelationshipExtractor()
        self._setup_languages()
    
    def _setup_languages(self) -> None:
        """设置支持的编程语言"""
        try:
            # 设置Python语言
            python_lang = Language(tspython.language())
            python_parser = Parser(python_lang)
            self.languages["python"] = python_lang
            self.parsers["python"] = python_parser
            
            # 设置Java语言
            java_lang = Language(tsjava.language())
            java_parser = Parser(java_lang)
            self.languages["java"] = java_lang
            self.parsers["java"] = java_parser
            
            # 设置JavaScript语言
            js_lang = Language(tsjs.language())
            js_parser = Parser(js_lang)
            self.languages["javascript"] = js_lang
            self.parsers["javascript"] = js_parser
            
            parser_logger.info(f"已初始化 {len(self.parsers)} 种语言解析器")
            
        except Exception as e:
            parser_logger.error(f"初始化语言解析器失败: {e}")
            raise ParseError(f"Failed to initialize language parsers: {e}")
    
    def get_supported_languages(self) -> List[str]:
        """获取支持的编程语言列表"""
        return list(self.parsers.keys())
    
    def _detect_language(self, file_path: str) -> Optional[str]:
        """根据文件扩展名检测编程语言"""
        extension_map = {
            ".py": "python",
            ".java": "java",
            ".js": "javascript",
            ".jsx": "javascript",
            ".ts": "javascript",  # TypeScript使用JavaScript解析器
            ".tsx": "javascript",
        }
        
        file_ext = Path(file_path).suffix.lower()
        return extension_map.get(file_ext)
    
    @error_handler(component="parser", operation="parse_project")
    @with_circuit_breaker(failure_threshold=3, recovery_timeout=60, expected_exception=ParseError)
    def parse_project(self, project_path: str) -> List[ParseResult]:
        """解析整个项目"""
        parser_logger.info(f"开始解析项目: {project_path}")
        results = []
        
        try:
            project_dir = Path(project_path)
            if not project_dir.exists():
                raise ParseError(f"项目路径不存在: {project_path}")
            
            # 查找所有支持的源代码文件
            source_files = []
            for ext in [".py", ".java", ".js", ".jsx", ".ts", ".tsx"]:
                source_files.extend(project_dir.rglob(f"*{ext}"))
            
            parser_logger.info(f"找到 {len(source_files)} 个源代码文件")
            
            # 解析每个文件
            for file_path in source_files:
                try:
                    file_result = self.parse_file(str(file_path))
                    if file_result.success and file_result.parse_result:
                        results.append(file_result.parse_result)
                except Exception as e:
                    parser_logger.warning(f"解析文件失败 {file_path}: {e}")
                    continue
            
            parser_logger.info(f"成功解析 {len(results)} 个文件")
            return results
            
        except Exception as e:
            parser_logger.error(f"解析项目失败: {e}")
            raise ParseError(f"Failed to parse project: {e}")
    
    @error_handler(component="parser", operation="parse_file")
    def parse_file(self, file_path: str) -> FileParseResult:
        """解析单个文件"""
        start_time = time.time()
        
        try:
            # 检测语言
            language = self._detect_language(file_path)
            if not language:
                return FileParseResult(
                    file_path=file_path,
                    success=False,
                    error_message=f"不支持的文件类型: {file_path}",
                    parse_time=time.time() - start_time
                )
            
            # 读取文件内容
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    source_code = f.read()
            except UnicodeDecodeError:
                # 尝试其他编码
                with open(file_path, 'r', encoding='gbk') as f:
                    source_code = f.read()
            
            # 解析代码
            parser = self.parsers[language]
            tree = parser.parse(bytes(source_code, 'utf8'))
            
            # 提取代码元素和关系
            elements = self.extract_elements(tree.root_node)
            relationships = self.relationship_extractor.extract_relationships(
                tree.root_node, elements, file_path
            )
            
            # 更新元素的文件路径
            for element in elements:
                element.file_path = file_path
            
            # 更新关系的文件路径信息
            for relationship in relationships:
                relationship.metadata["file_path"] = file_path
            
            parse_result = ParseResult(
                file_path=file_path,
                language=language,
                elements=elements,
                relationships=relationships,
                parse_time=time.time() - start_time,
                metadata={"tree_size": self._count_nodes(tree.root_node)}
            )
            
            return FileParseResult(
                file_path=file_path,
                success=True,
                parse_result=parse_result,
                parse_time=time.time() - start_time
            )
            
        except Exception as e:
            parser_logger.error(f"解析文件失败 {file_path}: {e}")
            return FileParseResult(
                file_path=file_path,
                success=False,
                error_message=str(e),
                parse_time=time.time() - start_time
            )
    
    def extract_elements(self, ast: Node) -> List[CodeElement]:
        """从AST提取代码元素"""
        elements = []
        
        def traverse_node(node: Node, parent_element: Optional[CodeElement] = None):
            """遍历AST节点"""
            element = self._node_to_element(node, parent_element)
            if element:
                elements.append(element)
                
                # 递归处理子节点
                for child in node.children:
                    traverse_node(child, element)
            else:
                # 如果当前节点不是代码元素，继续遍历子节点
                for child in node.children:
                    traverse_node(child, parent_element)
        
        traverse_node(ast)
        return elements
    
    def extract_relationships(self, ast: Node, elements: List[CodeElement]) -> List[Relationship]:
        """从AST提取关系"""
        relationships = []
        element_map = {elem.id: elem for elem in elements}
        
        def traverse_for_relationships(node: Node):
            """遍历节点查找关系"""
            # 查找函数调用关系
            if node.type in ["call", "method_invocation", "call_expression"]:
                rel = self._extract_call_relationship(node, element_map)
                if rel:
                    relationships.append(rel)
            
            # 查找继承关系
            elif node.type in ["class_declaration", "class_definition"]:
                rels = self._extract_inheritance_relationships(node, element_map)
                relationships.extend(rels)
            
            # 查找导入关系
            elif node.type in ["import_statement", "import_declaration", "import_from_statement"]:
                rel = self._extract_import_relationship(node, element_map)
                if rel:
                    relationships.append(rel)
            
            # 递归处理子节点
            for child in node.children:
                traverse_for_relationships(child)
        
        traverse_for_relationships(ast)
        return relationships
    
    def _node_to_element(self, node: Node, parent: Optional[CodeElement] = None) -> Optional[CodeElement]:
        """将AST节点转换为代码元素"""
        element_type = self._get_element_type(node)
        if not element_type:
            return None
        
        name = self._extract_name(node)
        if not name:
            return None
        
        element = CodeElement(
            name=name,
            type=element_type,
            line_number=node.start_point[0] + 1,
            end_line_number=node.end_point[0] + 1,
            complexity=self._calculate_complexity(node),
            visibility=self._extract_visibility(node),
            is_abstract=self._is_abstract(node),
            is_static=self._is_static(node),
            parameters=self._extract_parameters(node),
            return_type=self._extract_return_type(node),
            docstring=self._extract_docstring(node),
            metadata={
                "node_type": node.type,
                "parent_id": parent.id if parent else None,
                "byte_range": (node.start_byte, node.end_byte),
            }
        )
        
        return element
    
    def _get_element_type(self, node: Node) -> Optional[ElementType]:
        """获取节点对应的元素类型"""
        type_mapping = {
            # Python
            "class_definition": ElementType.CLASS,
            "function_definition": ElementType.FUNCTION,
            "assignment": ElementType.VARIABLE,
            
            # Java
            "class_declaration": ElementType.CLASS,
            "interface_declaration": ElementType.INTERFACE,
            "method_declaration": ElementType.METHOD,
            "field_declaration": ElementType.FIELD,
            "enum_declaration": ElementType.ENUM,
            
            # JavaScript
            "class_declaration": ElementType.CLASS,
            "function_declaration": ElementType.FUNCTION,
            "method_definition": ElementType.METHOD,
            "variable_declaration": ElementType.VARIABLE,
        }
        
        return type_mapping.get(node.type)
    
    def _extract_name(self, node: Node) -> Optional[str]:
        """提取节点名称"""
        # 查找名称节点
        for child in node.children:
            if child.type in ["identifier", "name"]:
                return child.text.decode('utf8')
        
        # 对于某些特殊情况，直接从节点文本提取
        if node.type == "assignment":
            # Python赋值语句
            for child in node.children:
                if child.type == "identifier":
                    return child.text.decode('utf8')
        
        return None
    
    def _calculate_complexity(self, node: Node) -> int:
        """计算节点复杂度（简化版圈复杂度）"""
        complexity = 1  # 基础复杂度
        
        def count_complexity_nodes(n: Node):
            nonlocal complexity
            
            # 增加复杂度的节点类型
            complexity_nodes = {
                "if_statement", "elif_clause", "else_clause",
                "for_statement", "while_statement",
                "try_statement", "except_clause",
                "conditional_expression",
                "boolean_operator",
                "and", "or",
            }
            
            if n.type in complexity_nodes:
                complexity += 1
            
            for child in n.children:
                count_complexity_nodes(child)
        
        count_complexity_nodes(node)
        return complexity
    
    def _extract_visibility(self, node: Node) -> str:
        """提取可见性修饰符"""
        # 查找修饰符
        for child in node.children:
            if child.type == "modifiers":
                for modifier in child.children:
                    if modifier.text.decode('utf8') in ["private", "protected", "public"]:
                        return modifier.text.decode('utf8')
        
        # Python中以下划线开头的是私有的
        name = self._extract_name(node)
        if name and name.startswith("_"):
            return "private"
        
        return "public"
    
    def _is_abstract(self, node: Node) -> bool:
        """检查是否为抽象"""
        for child in node.children:
            if child.type == "modifiers":
                for modifier in child.children:
                    if modifier.text.decode('utf8') == "abstract":
                        return True
        return False
    
    def _is_static(self, node: Node) -> bool:
        """检查是否为静态"""
        for child in node.children:
            if child.type == "modifiers":
                for modifier in child.children:
                    if modifier.text.decode('utf8') == "static":
                        return True
        return False
    
    def _extract_parameters(self, node: Node) -> List[str]:
        """提取参数列表"""
        parameters = []
        
        for child in node.children:
            if child.type in ["parameters", "formal_parameters"]:
                for param in child.children:
                    if param.type in ["identifier", "parameter"]:
                        param_name = param.text.decode('utf8')
                        if param_name not in ["(", ")", ","]:
                            parameters.append(param_name)
        
        return parameters
    
    def _extract_return_type(self, node: Node) -> Optional[str]:
        """提取返回类型"""
        for child in node.children:
            if child.type in ["type", "return_type"]:
                return child.text.decode('utf8')
        return None
    
    def _extract_docstring(self, node: Node) -> Optional[str]:
        """提取文档字符串"""
        # 查找紧跟在定义后的字符串字面量
        for child in node.children:
            if child.type in ["string", "string_literal", "expression_statement"]:
                # 进一步检查是否为字符串
                for grandchild in child.children:
                    if grandchild.type in ["string", "string_literal"]:
                        text = grandchild.text.decode('utf8')
                        # 移除引号
                        if text.startswith('"""') or text.startswith("'''"):
                            return text[3:-3].strip()
                        elif text.startswith('"') or text.startswith("'"):
                            return text[1:-1].strip()
        return None
    
    def _extract_call_relationship(self, node: Node, element_map: Dict[str, CodeElement]) -> Optional[Relationship]:
        """提取函数调用关系"""
        # 这是一个简化的实现，实际需要更复杂的分析
        caller_name = None
        callee_name = None
        
        # 提取被调用的函数名
        for child in node.children:
            if child.type in ["identifier", "member_expression"]:
                callee_name = child.text.decode('utf8')
                break
        
        if not callee_name:
            return None
        
        # 查找调用者和被调用者
        caller_id = None
        callee_id = None
        
        for elem_id, element in element_map.items():
            if element.name == callee_name:
                callee_id = elem_id
                break
        
        if not callee_id:
            return None
        
        return Relationship(
            source_id=caller_id or "unknown",
            target_id=callee_id,
            type=RelationType.CALLS,
            line_number=node.start_point[0] + 1,
            context=f"Function call: {callee_name}",
            metadata={"call_type": "function_call"}
        )
    
    def _extract_inheritance_relationships(self, node: Node, element_map: Dict[str, CodeElement]) -> List[Relationship]:
        """提取继承关系"""
        relationships = []
        
        class_name = self._extract_name(node)
        if not class_name:
            return relationships
        
        # 查找类ID
        class_id = None
        for elem_id, element in element_map.items():
            if element.name == class_name and element.type == ElementType.CLASS:
                class_id = elem_id
                break
        
        if not class_id:
            return relationships
        
        # 查找继承的父类
        for child in node.children:
            if child.type in ["superclass", "argument_list", "superclasses"]:
                for grandchild in child.children:
                    if grandchild.type == "identifier":
                        parent_name = grandchild.text.decode('utf8')
                        
                        # 查找父类ID
                        parent_id = None
                        for elem_id, element in element_map.items():
                            if element.name == parent_name and element.type == ElementType.CLASS:
                                parent_id = elem_id
                                break
                        
                        if parent_id:
                            relationships.append(Relationship(
                                source_id=class_id,
                                target_id=parent_id,
                                type=RelationType.INHERITS,
                                line_number=node.start_point[0] + 1,
                                context=f"Class {class_name} inherits from {parent_name}",
                                metadata={"inheritance_type": "class_inheritance"}
                            ))
        
        return relationships
    
    def _extract_import_relationship(self, node: Node, element_map: Dict[str, CodeElement]) -> Optional[Relationship]:
        """提取导入关系"""
        # 简化的导入关系提取
        import_name = None
        
        for child in node.children:
            if child.type in ["identifier", "dotted_name"]:
                import_name = child.text.decode('utf8')
                break
        
        if not import_name:
            return None
        
        return Relationship(
            source_id="current_module",
            target_id=import_name,
            type=RelationType.IMPORTS,
            line_number=node.start_point[0] + 1,
            context=f"Import: {import_name}",
            metadata={"import_type": "module_import"}
        )
    
    def _count_nodes(self, node: Node) -> int:
        """计算AST节点数量"""
        count = 1
        for child in node.children:
            count += self._count_nodes(child)
        return count