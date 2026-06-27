"""
跨文件关系分析器

专门用于分析跨文件的代码关系，如导入依赖、继承关系等。
"""

import os
from pathlib import Path
from typing import Dict, List, Set, Tuple

from ..models.core import CodeElement, ElementType, ParseResult, Relationship, RelationType
from ..utils.logger import parser_logger


class CrossFileAnalyzer:
    """跨文件关系分析器"""
    
    def __init__(self):
        """初始化分析器"""
        self.global_symbol_table: Dict[str, List[Tuple[CodeElement, str]]] = {}
        self.import_graph: Dict[str, Set[str]] = {}
        self.file_exports: Dict[str, Set[str]] = {}
    
    def analyze_project_relationships(
        self, 
        parse_results: Dict[str, ParseResult]
    ) -> List[Relationship]:
        """
        分析整个项目的跨文件关系
        
        Args:
            parse_results: 文件路径到解析结果的映射
            
        Returns:
            跨文件关系列表
        """
        parser_logger.info(f"开始分析 {len(parse_results)} 个文件的跨文件关系")
        
        # 构建全局符号表
        self._build_global_symbol_table(parse_results)
        
        # 分析导入关系
        self._analyze_import_relationships(parse_results)
        
        # 提取跨文件关系
        relationships = []
        relationships.extend(self._extract_import_dependencies(parse_results))
        relationships.extend(self._extract_inheritance_across_files(parse_results))
        relationships.extend(self._extract_usage_relationships(parse_results))
        
        parser_logger.info(f"提取到 {len(relationships)} 个跨文件关系")
        return relationships
    
    def _build_global_symbol_table(self, parse_results: Dict[str, ParseResult]) -> None:
        """构建全局符号表"""
        self.global_symbol_table.clear()
        
        for file_path, result in parse_results.items():
            for element in result.elements:
                symbol_name = element.name
                
                if symbol_name not in self.global_symbol_table:
                    self.global_symbol_table[symbol_name] = []
                
                self.global_symbol_table[symbol_name].append((element, file_path))
        
        parser_logger.info(f"构建全局符号表，包含 {len(self.global_symbol_table)} 个符号")
    
    def _analyze_import_relationships(self, parse_results: Dict[str, ParseResult]) -> None:
        """分析导入关系"""
        self.import_graph.clear()
        self.file_exports.clear()
        
        for file_path, result in parse_results.items():
            imports = set()
            exports = set()
            
            # 分析导入语句
            for relationship in result.relationships:
                if relationship.type == RelationType.IMPORTS:
                    imported_module = relationship.target_id
                    imports.add(imported_module)
            
            # 分析导出的符号（公共类、函数等）
            for element in result.elements:
                if self._is_exportable(element):
                    exports.add(element.name)
            
            self.import_graph[file_path] = imports
            self.file_exports[file_path] = exports
    
    def _is_exportable(self, element: CodeElement) -> bool:
        """判断元素是否可导出"""
        # 公共类、函数、变量可以被导出
        if element.type in [ElementType.CLASS, ElementType.FUNCTION]:
            return element.visibility == "public" or not element.name.startswith("_")
        
        return False
    
    def _extract_import_dependencies(self, parse_results: Dict[str, ParseResult]) -> List[Relationship]:
        """提取导入依赖关系"""
        relationships = []
        
        for file_path, result in parse_results.items():
            for relationship in result.relationships:
                if relationship.type == RelationType.IMPORTS:
                    # 尝试解析导入的模块路径
                    imported_module = relationship.target_id
                    target_file = self._resolve_import_path(imported_module, file_path, parse_results)
                    
                    if target_file:
                        # 创建文件级别的依赖关系
                        file_dependency = Relationship(
                            source_id=file_path,
                            target_id=target_file,
                            type=RelationType.DEPENDS,
                            line_number=relationship.line_number,
                            context=f"File {file_path} imports from {target_file}",
                            metadata={
                                "dependency_type": "import",
                                "imported_module": imported_module,
                                "source_file": file_path,
                                "target_file": target_file
                            }
                        )
                        relationships.append(file_dependency)
        
        return relationships
    
    def _extract_inheritance_across_files(self, parse_results: Dict[str, ParseResult]) -> List[Relationship]:
        """提取跨文件继承关系"""
        relationships = []
        
        for file_path, result in parse_results.items():
            for element in result.elements:
                if element.type == ElementType.CLASS:
                    # 查找可能的跨文件父类
                    parent_classes = self._find_potential_parent_classes(element, file_path, parse_results)
                    
                    for parent_element, parent_file in parent_classes:
                        if parent_file != file_path:  # 跨文件继承
                            inheritance_rel = Relationship(
                                source_id=element.id,
                                target_id=parent_element.id,
                                type=RelationType.INHERITS,
                                line_number=element.line_number,
                                context=f"Class {element.name} inherits from {parent_element.name} (cross-file)",
                                metadata={
                                    "child_class": element.name,
                                    "parent_class": parent_element.name,
                                    "child_file": file_path,
                                    "parent_file": parent_file,
                                    "cross_file": True
                                }
                            )
                            relationships.append(inheritance_rel)
        
        return relationships
    
    def _extract_usage_relationships(self, parse_results: Dict[str, ParseResult]) -> List[Relationship]:
        """提取跨文件使用关系"""
        relationships = []
        
        for file_path, result in parse_results.items():
            # 分析文件中使用的外部符号
            used_symbols = self._extract_used_symbols(result)
            
            for symbol_name in used_symbols:
                # 查找符号定义
                if symbol_name in self.global_symbol_table:
                    definitions = self.global_symbol_table[symbol_name]
                    
                    for definition_element, definition_file in definitions:
                        if definition_file != file_path:  # 跨文件使用
                            usage_rel = Relationship(
                                source_id=file_path,
                                target_id=definition_element.id,
                                type=RelationType.DEPENDS,
                                line_number=0,  # 需要更精确的行号
                                context=f"File {file_path} uses {symbol_name} from {definition_file}",
                                metadata={
                                    "dependency_type": "usage",
                                    "symbol_name": symbol_name,
                                    "source_file": file_path,
                                    "target_file": definition_file,
                                    "cross_file": True
                                }
                            )
                            relationships.append(usage_rel)
        
        return relationships
    
    def _resolve_import_path(
        self, 
        import_name: str, 
        current_file: str, 
        parse_results: Dict[str, ParseResult]
    ) -> str:
        """解析导入路径到实际文件路径"""
        current_dir = Path(current_file).parent
        
        # 尝试不同的解析策略
        candidates = []
        
        # 1. 相对导入
        if import_name.startswith('.'):
            # 处理相对导入
            relative_path = import_name.lstrip('.')
            candidates.append(current_dir / f"{relative_path}.py")
        else:
            # 2. 绝对导入
            candidates.append(current_dir / f"{import_name}.py")
            
            # 3. 包导入
            candidates.append(current_dir / import_name / "__init__.py")
            
            # 4. 同目录文件
            for file_path in parse_results.keys():
                file_name = Path(file_path).stem
                if file_name == import_name:
                    candidates.append(Path(file_path))
        
        # 查找存在的文件
        for candidate in candidates:
            candidate_str = str(candidate.resolve())
            if candidate_str in parse_results:
                return candidate_str
        
        return None
    
    def _find_potential_parent_classes(
        self, 
        class_element: CodeElement, 
        current_file: str, 
        parse_results: Dict[str, ParseResult]
    ) -> List[Tuple[CodeElement, str]]:
        """查找潜在的父类"""
        potential_parents = []
        
        # 从类的元数据中查找父类信息（需要解析器提供）
        # 这里简化实现，基于命名模式推测
        
        # 查找同名但在其他文件中的类（可能是父类）
        class_name = class_element.name
        
        # 查找可能的基类名称模式
        potential_base_names = [
            f"Base{class_name}",
            f"{class_name}Base",
            f"Abstract{class_name}",
            class_name.replace("Impl", ""),  # 实现类到接口
        ]
        
        for base_name in potential_base_names:
            if base_name in self.global_symbol_table:
                for element, file_path in self.global_symbol_table[base_name]:
                    if element.type == ElementType.CLASS and file_path != current_file:
                        potential_parents.append((element, file_path))
        
        return potential_parents
    
    def _extract_used_symbols(self, parse_result: ParseResult) -> Set[str]:
        """从解析结果中提取使用的符号"""
        used_symbols = set()
        
        # 从关系中提取被调用的函数
        for relationship in parse_result.relationships:
            if relationship.type == RelationType.CALLS:
                # 从元数据中提取被调用的函数名
                if "callee" in relationship.metadata:
                    used_symbols.add(relationship.metadata["callee"])
        
        # 从导入关系中提取导入的符号
        for relationship in parse_result.relationships:
            if relationship.type == RelationType.IMPORTS:
                if "imported_items" in relationship.metadata:
                    imported_items = relationship.metadata["imported_items"]
                    used_symbols.update(imported_items)
        
        return used_symbols
    
    def get_dependency_graph(self) -> Dict[str, Set[str]]:
        """获取文件依赖图"""
        return self.import_graph.copy()
    
    def get_file_exports(self) -> Dict[str, Set[str]]:
        """获取文件导出符号"""
        return self.file_exports.copy()
    
    def find_circular_dependencies(self) -> List[List[str]]:
        """查找循环依赖"""
        cycles = []
        visited = set()
        rec_stack = set()
        
        def dfs(file_path: str, path: List[str]) -> None:
            if file_path in rec_stack:
                # 找到循环
                cycle_start = path.index(file_path)
                cycle = path[cycle_start:] + [file_path]
                cycles.append(cycle)
                return
            
            if file_path in visited:
                return
            
            visited.add(file_path)
            rec_stack.add(file_path)
            path.append(file_path)
            
            # 访问依赖的文件
            if file_path in self.import_graph:
                for dependency in self.import_graph[file_path]:
                    dfs(dependency, path.copy())
            
            rec_stack.remove(file_path)
        
        # 对每个文件进行DFS
        for file_path in self.import_graph:
            if file_path not in visited:
                dfs(file_path, [])
        
        return cycles