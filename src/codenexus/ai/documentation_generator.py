"""
智能文档生成器

基于代码上下文和知识图谱信息生成高质量的技术文档。
"""

import json
import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

import markdown
from markdown.extensions import codehilite, toc

from ..exceptions import AILayerError, DocumentationError
from ..models.core import CodeElement, CodeGraph, ElementType, GraphNode, Relationship
from .ai_layer import AILayer


logger = logging.getLogger(__name__)


class DocumentationGenerator:
    """智能文档生成器
    
    使用AI层和代码上下文信息生成结构化的技术文档。
    支持API文档、模块文档等多种文档类型的生成。
    """
    
    def __init__(self, ai_layer: AILayer):
        """初始化文档生成器
        
        Args:
            ai_layer: AI智能层实例
        """
        self.ai_layer = ai_layer
        self._markdown_processor = markdown.Markdown(
            extensions=['codehilite', 'toc', 'tables', 'fenced_code'],
            extension_configs={
                'codehilite': {
                    'css_class': 'highlight',
                    'use_pygments': True
                },
                'toc': {
                    'permalink': True
                }
            }
        )
    
    async def generate_api_documentation(
        self, 
        code_element: CodeElement,
        related_elements: Optional[List[CodeElement]] = None,
        graph_context: Optional[Dict[str, Any]] = None
    ) -> str:
        """生成API文档
        
        Args:
            code_element: 要生成文档的代码元素
            related_elements: 相关代码元素列表
            graph_context: 图谱上下文信息
            
        Returns:
            生成的Markdown格式API文档
            
        Raises:
            DocumentationError: 文档生成失败
        """
        try:
            logger.info(f"开始生成API文档: {code_element.name}")
            
            # 构建文档生成上下文
            context = self._build_api_context(
                code_element, related_elements or [], graph_context or {}
            )
            
            # 使用AI层生成文档
            raw_documentation = await self.ai_layer.generate_documentation(context)
            
            # 后处理和格式化
            formatted_doc = self._format_api_documentation(
                raw_documentation, code_element
            )
            
            logger.info(f"API文档生成完成: {code_element.name}")
            return formatted_doc
            
        except Exception as e:
            logger.error(f"API文档生成失败: {e}")
            raise DocumentationError(f"API文档生成失败: {e}")
    
    async def generate_module_documentation(
        self,
        module_elements: List[CodeElement],
        module_name: str,
        graph: Optional[CodeGraph] = None
    ) -> str:
        """生成模块文档
        
        Args:
            module_elements: 模块中的代码元素列表
            module_name: 模块名称
            graph: 代码知识图谱
            
        Returns:
            生成的Markdown格式模块文档
            
        Raises:
            DocumentationError: 文档生成失败
        """
        try:
            logger.info(f"开始生成模块文档: {module_name}")
            
            # 构建模块文档上下文
            context = self._build_module_context(
                module_elements, module_name, graph
            )
            
            # 使用AI层生成文档
            raw_documentation = await self.ai_layer.generate_documentation(context)
            
            # 后处理和格式化
            formatted_doc = self._format_module_documentation(
                raw_documentation, module_name, module_elements
            )
            
            logger.info(f"模块文档生成完成: {module_name}")
            return formatted_doc
            
        except Exception as e:
            logger.error(f"模块文档生成失败: {e}")
            raise DocumentationError(f"模块文档生成失败: {e}")
    
    async def generate_class_documentation(
        self,
        class_element: CodeElement,
        methods: List[CodeElement],
        fields: List[CodeElement],
        graph_context: Optional[Dict[str, Any]] = None
    ) -> str:
        """生成类文档
        
        Args:
            class_element: 类元素
            methods: 类方法列表
            fields: 类字段列表
            graph_context: 图谱上下文信息
            
        Returns:
            生成的Markdown格式类文档
        """
        try:
            logger.info(f"开始生成类文档: {class_element.name}")
            
            # 构建类文档上下文
            context = self._build_class_context(
                class_element, methods, fields, graph_context or {}
            )
            
            # 使用AI层生成文档
            raw_documentation = await self.ai_layer.generate_documentation(context)
            
            # 后处理和格式化
            formatted_doc = self._format_class_documentation(
                raw_documentation, class_element, methods, fields
            )
            
            logger.info(f"类文档生成完成: {class_element.name}")
            return formatted_doc
            
        except Exception as e:
            logger.error(f"类文档生成失败: {e}")
            raise DocumentationError(f"类文档生成失败: {e}")
    
    def convert_to_html(self, markdown_content: str) -> str:
        """将Markdown文档转换为HTML
        
        Args:
            markdown_content: Markdown格式的文档内容
            
        Returns:
            HTML格式的文档内容
        """
        try:
            html_content = self._markdown_processor.convert(markdown_content)
            
            # 添加基础HTML结构
            full_html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>代码文档</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }}
        .highlight {{ background-color: #f8f8f8; padding: 1em; border-radius: 4px; }}
        code {{ background-color: #f1f1f1; padding: 0.2em 0.4em; border-radius: 3px; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
    </style>
</head>
<body>
    {html_content}
</body>
</html>"""
            
            return full_html
            
        except Exception as e:
            logger.error(f"HTML转换失败: {e}")
            raise DocumentationError(f"HTML转换失败: {e}")
    
    def _build_api_context(
        self,
        code_element: CodeElement,
        related_elements: List[CodeElement],
        graph_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """构建API文档生成上下文"""
        context = {
            "code_element": code_element,
            "related_elements": related_elements,
            "graph_context": graph_context,
            "documentation_type": "api",
            "requirements": {
                "include_signature": True,
                "include_parameters": True,
                "include_return_value": True,
                "include_examples": True,
                "include_dependencies": True,
                "format": "markdown"
            }
        }
        
        # 添加特定于元素类型的要求
        if code_element.type in [ElementType.METHOD, ElementType.FUNCTION]:
            context["requirements"].update({
                "include_parameter_types": True,
                "include_return_type": True,
                "include_exceptions": True,
                "include_usage_examples": True
            })
        elif code_element.type == ElementType.CLASS:
            context["requirements"].update({
                "include_constructor": True,
                "include_methods_overview": True,
                "include_inheritance": True,
                "include_interfaces": True
            })
        
        return context
    
    def _build_module_context(
        self,
        module_elements: List[CodeElement],
        module_name: str,
        graph: Optional[CodeGraph]
    ) -> Dict[str, Any]:
        """构建模块文档生成上下文"""
        # 分析模块结构
        classes = [e for e in module_elements if e.type == ElementType.CLASS]
        functions = [e for e in module_elements if e.type in [ElementType.FUNCTION, ElementType.METHOD]]
        interfaces = [e for e in module_elements if e.type == ElementType.INTERFACE]
        
        # 分析依赖关系
        dependencies = self._analyze_module_dependencies(module_elements, graph)
        
        context = {
            "module_name": module_name,
            "module_elements": module_elements,
            "classes": classes,
            "functions": functions,
            "interfaces": interfaces,
            "dependencies": dependencies,
            "documentation_type": "module",
            "requirements": {
                "include_overview": True,
                "include_responsibilities": True,
                "include_dependencies": True,
                "include_main_functions": True,
                "include_architecture": True,
                "include_usage_guide": True,
                "format": "markdown"
            }
        }
        
        return context
    
    def _build_class_context(
        self,
        class_element: CodeElement,
        methods: List[CodeElement],
        fields: List[CodeElement],
        graph_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """构建类文档生成上下文"""
        # 分类方法
        constructors = [m for m in methods if m.name in ["__init__", "constructor"]]
        public_methods = [m for m in methods if m.visibility == "public" and m not in constructors]
        private_methods = [m for m in methods if m.visibility == "private"]
        
        context = {
            "code_element": class_element,
            "methods": methods,
            "fields": fields,
            "constructors": constructors,
            "public_methods": public_methods,
            "private_methods": private_methods,
            "graph_context": graph_context,
            "documentation_type": "class",
            "requirements": {
                "include_overview": True,
                "include_constructor": True,
                "include_methods": True,
                "include_fields": True,
                "include_inheritance": True,
                "include_examples": True,
                "format": "markdown"
            }
        }
        
        return context
    
    def _analyze_module_dependencies(
        self,
        module_elements: List[CodeElement],
        graph: Optional[CodeGraph]
    ) -> Dict[str, Any]:
        """分析模块依赖关系"""
        dependencies = {
            "internal": set(),
            "external": set(),
            "imports": [],
            "exports": []
        }
        
        if not graph:
            return dependencies
        
        # 从图谱中分析依赖关系
        element_ids = {e.id for e in module_elements}
        
        for edge in graph.edges:
            if edge.source_id in element_ids:
                # 找到目标节点
                target_node = graph.get_node_by_id(edge.target_id)
                if target_node:
                    target_file = target_node.get_property("file_path", "")
                    if target_file:
                        if any(e.file_path == target_file for e in module_elements):
                            dependencies["internal"].add(target_node.label)
                        else:
                            dependencies["external"].add(target_node.label)
        
        # 转换为列表以便JSON序列化
        dependencies["internal"] = list(dependencies["internal"])
        dependencies["external"] = list(dependencies["external"])
        
        return dependencies
    
    def _format_api_documentation(
        self,
        raw_documentation: str,
        code_element: CodeElement
    ) -> str:
        """格式化API文档"""
        # 添加文档头部信息
        header = f"""# {code_element.name} API文档

**类型**: {code_element.type.value}  
**文件**: {code_element.file_path}  
**行号**: {code_element.line_number}  
**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---

"""
        
        # 确保文档包含必要的章节
        formatted_doc = self._ensure_api_sections(raw_documentation, code_element)
        
        return header + formatted_doc
    
    def _format_module_documentation(
        self,
        raw_documentation: str,
        module_name: str,
        module_elements: List[CodeElement]
    ) -> str:
        """格式化模块文档"""
        # 添加文档头部信息
        header = f"""# {module_name} 模块文档

**元素数量**: {len(module_elements)}  
**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---

"""
        
        # 确保文档包含必要的章节
        formatted_doc = self._ensure_module_sections(raw_documentation, module_elements)
        
        return header + formatted_doc
    
    def _format_class_documentation(
        self,
        raw_documentation: str,
        class_element: CodeElement,
        methods: List[CodeElement],
        fields: List[CodeElement]
    ) -> str:
        """格式化类文档"""
        # 添加文档头部信息
        header = f"""# {class_element.name} 类文档

**文件**: {class_element.file_path}  
**行号**: {class_element.line_number}  
**方法数量**: {len(methods)}  
**字段数量**: {len(fields)}  
**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---

"""
        
        # 确保文档包含必要的章节
        formatted_doc = self._ensure_class_sections(raw_documentation, class_element, methods, fields)
        
        return header + formatted_doc
    
    def _ensure_api_sections(self, documentation: str, code_element: CodeElement) -> str:
        """确保API文档包含必要的章节"""
        required_sections = ["概述", "参数", "返回值", "使用示例", "注意事项"]
        
        # 检查现有章节
        existing_sections = re.findall(r'^#+\s+(.+)$', documentation, re.MULTILINE)
        
        # 添加缺失的章节
        missing_sections = [s for s in required_sections if not any(s in existing for existing in existing_sections)]
        
        if missing_sections:
            documentation += "\n\n"
            for section in missing_sections:
                documentation += f"\n## {section}\n\n待补充...\n"
        
        # 添加签名信息（如果是方法或函数）
        if code_element.type in [ElementType.METHOD, ElementType.FUNCTION]:
            signature = self._generate_signature(code_element)
            if signature and "```" not in documentation:
                documentation = f"## 函数签名\n\n```python\n{signature}\n```\n\n" + documentation
        
        return documentation
    
    def _ensure_module_sections(self, documentation: str, module_elements: List[CodeElement]) -> str:
        """确保模块文档包含必要的章节"""
        required_sections = ["概述", "主要功能", "架构设计", "使用指南", "API参考"]
        
        # 检查现有章节
        existing_sections = re.findall(r'^#+\s+(.+)$', documentation, re.MULTILINE)
        
        # 添加缺失的章节
        missing_sections = [s for s in required_sections if not any(s in existing for existing in existing_sections)]
        
        if missing_sections:
            documentation += "\n\n"
            for section in missing_sections:
                if section == "API参考":
                    documentation += f"\n## {section}\n\n"
                    # 添加API参考列表
                    classes = [e for e in module_elements if e.type == ElementType.CLASS]
                    functions = [e for e in module_elements if e.type in [ElementType.FUNCTION, ElementType.METHOD]]
                    
                    if classes:
                        documentation += "### 类\n\n"
                        for cls in classes:
                            documentation += f"- [{cls.name}](#{cls.name.lower()}): {cls.docstring or '待补充描述'}\n"
                    
                    if functions:
                        documentation += "\n### 函数\n\n"
                        for func in functions:
                            documentation += f"- [{func.name}](#{func.name.lower()}): {func.docstring or '待补充描述'}\n"
                else:
                    documentation += f"\n## {section}\n\n待补充...\n"
        
        return documentation
    
    def _ensure_class_sections(
        self,
        documentation: str,
        class_element: CodeElement,
        methods: List[CodeElement],
        fields: List[CodeElement]
    ) -> str:
        """确保类文档包含必要的章节"""
        required_sections = ["概述", "构造函数", "方法", "属性", "使用示例"]
        
        # 检查现有章节
        existing_sections = re.findall(r'^#+\s+(.+)$', documentation, re.MULTILINE)
        
        # 添加缺失的章节
        missing_sections = [s for s in required_sections if not any(s in existing for existing in existing_sections)]
        
        if missing_sections:
            documentation += "\n\n"
            for section in missing_sections:
                if section == "方法" and methods:
                    documentation += f"\n## {section}\n\n"
                    for method in methods:
                        documentation += f"### {method.name}\n\n{method.docstring or '待补充描述'}\n\n"
                elif section == "属性" and fields:
                    documentation += f"\n## {section}\n\n"
                    for field in fields:
                        documentation += f"- **{field.name}**: {field.docstring or '待补充描述'}\n"
                else:
                    documentation += f"\n## {section}\n\n待补充...\n"
        
        return documentation
    
    def _generate_signature(self, code_element: CodeElement) -> str:
        """生成函数或方法签名"""
        if code_element.type not in [ElementType.METHOD, ElementType.FUNCTION]:
            return ""
        
        # 构建参数列表
        params = ", ".join(code_element.parameters) if code_element.parameters else ""
        
        # 构建签名
        if code_element.return_type:
            signature = f"def {code_element.name}({params}) -> {code_element.return_type}:"
        else:
            signature = f"def {code_element.name}({params}):"
        
        return signature