"""
文档生成完整性的属性测试

**Feature: code-weaver, Property 5: 文档生成完整性**
*对于任意* 代码元素或模块，生成的文档应该包含所有必需的信息（签名、参数、返回值、职责、依赖关系），
并且格式应该符合Markdown标准且可正确转换为HTML
**验证需求: 需求 4.1, 4.2, 4.3, 4.4**
"""

import asyncio
import re
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Set
from unittest.mock import AsyncMock, MagicMock

import pytest
from hypothesis import given, strategies as st, settings, assume
from hypothesis.strategies import composite
import markdown

from src.codenexus.models.core import (
    CodeElement, ElementType, CodeGraph, GraphNode, GraphEdge, GraphMetadata
)
from src.codenexus.ai.documentation_generator import DocumentationGenerator
from src.codenexus.ai.ai_layer import AILayer
from src.codenexus.config import Config


# 模拟AI层，用于测试
class MockAILayer:
    """模拟AI层，返回可预测的文档内容"""
    
    def __init__(self):
        self.call_count = 0
        self.last_context = None
    
    async def generate_documentation(self, context: Dict) -> str:
        """生成模拟文档"""
        self.call_count += 1
        self.last_context = context
        
        code_element = context.get("code_element")
        doc_type = context.get("documentation_type", "api")
        
        if doc_type == "api" and code_element:
            return self._generate_api_doc(code_element, context)
        elif doc_type == "module":
            return self._generate_module_doc(context)
        elif doc_type == "class":
            return self._generate_class_doc(context)
        else:
            return "# 默认文档\n\n这是一个默认的文档内容。"
    
    def _generate_api_doc(self, code_element: CodeElement, context: Dict) -> str:
        """生成API文档"""
        doc_parts = [
            f"# {code_element.name} API文档",
            "",
            "## 概述",
            f"这是 {code_element.name} 的API文档。",
            "",
            "## 函数签名",
            f"```python",
            f"def {code_element.name}():",
            f"    pass",
            f"```",
            "",
            "## 参数",
            "- 无参数",
            "",
            "## 返回值",
            "- 返回类型: None",
            "- 描述: 无返回值",
            "",
            "## 使用示例",
            "```python",
            f"result = {code_element.name}()",
            "```",
            "",
            "## 注意事项",
            "- 这是一个示例函数",
            "- 请根据实际需求使用"
        ]
        
        # 如果有相关元素，添加依赖关系
        related_elements = context.get("related_elements", [])
        if related_elements:
            doc_parts.extend([
                "",
                "## 依赖关系",
                "相关代码元素："
            ])
            for elem in related_elements:
                doc_parts.append(f"- {elem.name} ({elem.type})")
        
        return "\n".join(doc_parts)
    
    def _generate_module_doc(self, context: Dict) -> str:
        """生成模块文档"""
        module_name = context.get("module_name", "未知模块")
        module_elements = context.get("module_elements", [])
        
        doc_parts = [
            f"# {module_name} 模块文档",
            "",
            "## 概述",
            f"{module_name} 模块提供了核心功能。",
            "",
            "## 主要功能",
            "- 功能1: 基础操作",
            "- 功能2: 高级操作",
            "",
            "## 架构设计",
            "模块采用分层架构设计。",
            "",
            "## 使用指南",
            "```python",
            f"import {module_name}",
            "```",
            "",
            "## API参考"
        ]
        
        # 添加类和函数列表
        classes = [e for e in module_elements if e.type == ElementType.CLASS]
        functions = [e for e in module_elements if e.type in [ElementType.FUNCTION, ElementType.METHOD]]
        
        if classes:
            doc_parts.extend([
                "",
                "### 类"
            ])
            for cls in classes:
                doc_parts.append(f"- [{cls.name}](#{cls.name.lower()}): {cls.name}类")
        
        if functions:
            doc_parts.extend([
                "",
                "### 函数"
            ])
            for func in functions:
                doc_parts.append(f"- [{func.name}](#{func.name.lower()}): {func.name}函数")
        
        return "\n".join(doc_parts)
    
    def _generate_class_doc(self, context: Dict) -> str:
        """生成类文档"""
        class_element = context.get("code_element")
        methods = context.get("methods", [])
        fields = context.get("fields", [])
        
        doc_parts = [
            f"# {class_element.name} 类文档",
            "",
            "## 概述",
            f"{class_element.name} 是一个重要的类。",
            "",
            "## 构造函数",
            f"```python",
            f"def __init__(self):",
            f"    pass",
            f"```",
            "",
            "## 方法"
        ]
        
        # 添加方法列表
        for method in methods:
            doc_parts.extend([
                f"### {method.name}",
                f"{method.name}方法的描述。",
                ""
            ])
        
        # 添加属性列表
        if fields:
            doc_parts.extend([
                "## 属性"
            ])
            for field in fields:
                doc_parts.append(f"- **{field.name}**: {field.name}属性")
        
        doc_parts.extend([
            "",
            "## 使用示例",
            "```python",
            f"obj = {class_element.name}()",
            "```"
        ])
        
        return "\n".join(doc_parts)


# 测试数据生成策略
@composite
def code_element_strategy(draw):
    """生成代码元素的策略"""
    element_types = [ElementType.CLASS, ElementType.METHOD, ElementType.FUNCTION, ElementType.VARIABLE]
    element_type = draw(st.sampled_from(element_types))
    
    # 简化名称生成，避免过度过滤
    name = draw(st.text(
        alphabet='abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_',
        min_size=1,
        max_size=15
    ).filter(lambda x: x and x[0].isalpha()))
    
    # 简化文件路径生成
    file_path = draw(st.sampled_from([
        "src/main.py", "src/utils.py", "src/models.py", "tests/test_main.py",
        "lib/core.py", "app/views.py", "common/helpers.py"
    ]))
    
    line_number = draw(st.integers(min_value=1, max_value=100))
    
    # 生成参数列表（对于方法和函数）
    parameters = []
    if element_type in [ElementType.METHOD, ElementType.FUNCTION]:
        param_count = draw(st.integers(min_value=0, max_value=3))
        for i in range(param_count):
            param_name = f"param_{i}"
            parameters.append(param_name)
    
    return CodeElement(
        id=f"{name}_{line_number}",
        name=name,
        type=element_type,
        file_path=file_path,
        line_number=line_number,
        parameters=parameters,
        return_type=draw(st.one_of(st.none(), st.sampled_from(["str", "int", "bool", "None"]))),
        docstring=draw(st.one_of(st.none(), st.just("Sample docstring for testing"))),
        visibility=draw(st.sampled_from(["public", "private", "protected"])),
        complexity=draw(st.integers(min_value=1, max_value=10)),
        metadata={}
    )


@composite
def module_elements_strategy(draw):
    """生成模块元素列表的策略"""
    element_count = draw(st.integers(min_value=1, max_value=5))
    elements = []
    
    for i in range(element_count):
        element = draw(code_element_strategy())
        elements.append(element)
    
    return elements


@composite
def code_graph_strategy(draw):
    """生成代码图谱的策略"""
    node_count = draw(st.integers(min_value=1, max_value=5))
    nodes = []
    
    for i in range(node_count):
        node_id = f"node_{i}"
        node = GraphNode(
            id=node_id,
            label=draw(st.text(min_size=1, max_size=20)),
            properties={
                "file_path": draw(st.text(min_size=5, max_size=30)),
                "type": draw(st.sampled_from(["class", "method", "function"]))
            }
        )
        nodes.append(node)
    
    # 生成边
    edges = []
    if len(nodes) > 1:
        edge_count = draw(st.integers(min_value=0, max_value=min(3, len(nodes) - 1)))
        for i in range(edge_count):
            source = draw(st.sampled_from(nodes))
            target = draw(st.sampled_from([n for n in nodes if n.id != source.id]))
            edge = GraphEdge(
                id=f"edge_{i}",
                source_id=source.id,
                target_id=target.id,
                type="calls",
                properties={}
            )
            edges.append(edge)
    
    return CodeGraph(
        nodes=nodes,
        edges=edges,
        metadata=GraphMetadata(
            created_at="2024-01-01T00:00:00Z",
            version="1.0.0",
            node_count=len(nodes),
            edge_count=len(edges)
        )
    )


class TestDocumentationProperties:
    """文档生成完整性属性测试类"""
    
    def setup_method(self):
        """设置测试环境"""
        self.mock_ai_layer = MockAILayer()
        self.doc_generator = DocumentationGenerator(self.mock_ai_layer)
    
    @given(code_element_strategy())
    @settings(max_examples=100, deadline=None)
    def test_api_documentation_completeness(self, code_element):
        """
        **Feature: code-weaver, Property 5: 文档生成完整性**
        测试API文档生成的完整性
        """
        # 运行异步测试
        async def run_test():
            # 生成API文档
            documentation = await self.doc_generator.generate_api_documentation(
                code_element=code_element,
                related_elements=[],
                graph_context={}
            )
            
            # 验证文档不为空
            assert documentation.strip(), "生成的文档不能为空"
            
            # 验证文档包含必要的章节
            required_sections = ["概述", "参数", "返回值", "使用示例", "注意事项"]
            for section in required_sections:
                assert f"## {section}" in documentation or f"# {section}" in documentation, \
                    f"文档缺少必需的章节: {section}"
            
            # 验证文档包含代码元素名称
            assert code_element.name in documentation, "文档应该包含代码元素名称"
            
            # 验证文档包含代码块（如果是方法或函数）
            if code_element.type in [ElementType.METHOD, ElementType.FUNCTION]:
                assert "```python" in documentation, "API文档应该包含代码示例"
                assert "```" in documentation, "代码块应该正确闭合"
            
            # 验证Markdown格式正确性
            try:
                html_content = self.doc_generator.convert_to_html(documentation)
                assert html_content.strip(), "HTML转换结果不能为空"
                assert "<html" in html_content, "应该生成完整的HTML文档"
                assert "</html>" in html_content, "HTML文档应该正确闭合"
            except Exception as e:
                pytest.fail(f"Markdown转HTML转换失败: {e}")
            
            # 验证文档结构合理
            lines = documentation.split('\n')
            non_empty_lines = [line for line in lines if line.strip()]
            assert len(non_empty_lines) >= 5, "文档应该有足够的内容"
            
            # 验证标题层级合理
            title_pattern = re.compile(r'^#+\s+')
            titles = [line for line in lines if title_pattern.match(line)]
            assert len(titles) >= 3, "文档应该有合理的标题结构"
        
        # 运行异步测试
        asyncio.run(run_test())
    
    @given(module_elements_strategy())
    @settings(max_examples=50, deadline=None)
    def test_module_documentation_completeness(self, module_elements):
        """
        **Feature: code-weaver, Property 5: 文档生成完整性**
        测试模块文档生成的完整性
        """
        assume(len(module_elements) > 0)
        
        async def run_test():
            module_name = "test_module"
            
            # 生成模块文档
            documentation = await self.doc_generator.generate_module_documentation(
                module_elements=module_elements,
                module_name=module_name,
                graph=None
            )
            
            # 验证文档不为空
            assert documentation.strip(), "生成的模块文档不能为空"
            
            # 验证文档包含模块名称
            assert module_name in documentation, "文档应该包含模块名称"
            
            # 验证文档包含必要的章节
            required_sections = ["概述", "主要功能", "架构设计", "使用指南", "API参考"]
            for section in required_sections:
                assert f"## {section}" in documentation or f"# {section}" in documentation, \
                    f"模块文档缺少必需的章节: {section}"
            
            # 验证API参考章节包含元素信息
            classes = [e for e in module_elements if e.type == ElementType.CLASS]
            functions = [e for e in module_elements if e.type in [ElementType.FUNCTION, ElementType.METHOD]]
            
            if classes:
                assert "### 类" in documentation, "应该包含类的章节"
                for cls in classes:
                    assert cls.name in documentation, f"应该包含类 {cls.name}"
            
            if functions:
                assert "### 函数" in documentation, "应该包含函数的章节"
                for func in functions:
                    assert func.name in documentation, f"应该包含函数 {func.name}"
            
            # 验证Markdown格式正确性
            try:
                html_content = self.doc_generator.convert_to_html(documentation)
                assert html_content.strip(), "HTML转换结果不能为空"
                assert "<html" in html_content, "应该生成完整的HTML文档"
            except Exception as e:
                pytest.fail(f"Markdown转HTML转换失败: {e}")
        
        asyncio.run(run_test())
    
    @given(code_element_strategy(), module_elements_strategy())
    @settings(max_examples=50, deadline=None)
    def test_class_documentation_completeness(self, class_element, related_elements):
        """
        **Feature: code-weaver, Property 5: 文档生成完整性**
        测试类文档生成的完整性
        """
        assume(class_element.type == ElementType.CLASS)
        
        # 分离方法和字段
        methods = [e for e in related_elements if e.type in [ElementType.METHOD, ElementType.FUNCTION]]
        fields = [e for e in related_elements if e.type == ElementType.VARIABLE]
        
        async def run_test():
            # 生成类文档
            documentation = await self.doc_generator.generate_class_documentation(
                class_element=class_element,
                methods=methods,
                fields=fields,
                graph_context={}
            )
            
            # 验证文档不为空
            assert documentation.strip(), "生成的类文档不能为空"
            
            # 验证文档包含类名称
            assert class_element.name in documentation, "文档应该包含类名称"
            
            # 验证文档包含必要的章节
            required_sections = ["概述", "构造函数", "方法", "使用示例"]
            for section in required_sections:
                assert f"## {section}" in documentation or f"# {section}" in documentation, \
                    f"类文档缺少必需的章节: {section}"
            
            # 验证方法信息
            if methods:
                for method in methods:
                    assert method.name in documentation, f"应该包含方法 {method.name}"
            
            # 验证字段信息
            if fields:
                assert "## 属性" in documentation, "应该包含属性章节"
                for field in fields:
                    assert field.name in documentation, f"应该包含字段 {field.name}"
            
            # 验证Markdown格式正确性
            try:
                html_content = self.doc_generator.convert_to_html(documentation)
                assert html_content.strip(), "HTML转换结果不能为空"
            except Exception as e:
                pytest.fail(f"Markdown转HTML转换失败: {e}")
        
        asyncio.run(run_test())
    
    @given(code_element_strategy())
    @settings(max_examples=50, deadline=None)
    def test_documentation_markdown_validity(self, code_element):
        """
        **Feature: code-weaver, Property 5: 文档生成完整性**
        测试生成文档的Markdown格式有效性
        """
        async def run_test():
            # 生成文档
            documentation = await self.doc_generator.generate_api_documentation(
                code_element=code_element
            )
            
            # 验证Markdown语法正确性
            md_processor = markdown.Markdown(extensions=['codehilite', 'toc', 'tables'])
            
            try:
                html_result = md_processor.convert(documentation)
                assert html_result.strip(), "Markdown转换结果不能为空"
            except Exception as e:
                pytest.fail(f"Markdown语法无效: {e}")
            
            # 验证代码块格式
            code_blocks = re.findall(r'```[\s\S]*?```', documentation)
            for block in code_blocks:
                assert block.count('```') == 2, "代码块应该正确闭合"
            
            # 验证链接格式
            links = re.findall(r'\[([^\]]+)\]\(([^)]+)\)', documentation)
            for link_text, link_url in links:
                assert link_text.strip(), "链接文本不能为空"
                assert link_url.strip(), "链接URL不能为空"
            
            # 验证标题层级
            titles = re.findall(r'^(#+)\s+(.+)$', documentation, re.MULTILINE)
            for level, title in titles:
                assert 1 <= len(level) <= 6, "标题层级应该在1-6之间"
                assert title.strip(), "标题内容不能为空"
        
        asyncio.run(run_test())
    
    @given(code_element_strategy())
    @settings(max_examples=30, deadline=None)
    def test_html_conversion_completeness(self, code_element):
        """
        **Feature: code-weaver, Property 5: 文档生成完整性**
        测试HTML转换的完整性
        """
        async def run_test():
            # 生成文档
            documentation = await self.doc_generator.generate_api_documentation(
                code_element=code_element
            )
            
            # 转换为HTML
            html_content = self.doc_generator.convert_to_html(documentation)
            
            # 验证HTML结构完整性
            assert "<!DOCTYPE html>" in html_content, "应该包含DOCTYPE声明"
            assert "<html" in html_content, "应该包含html标签"
            assert "</html>" in html_content, "应该正确闭合html标签"
            assert "<head>" in html_content, "应该包含head标签"
            assert "</head>" in html_content, "应该正确闭合head标签"
            assert "<body>" in html_content, "应该包含body标签"
            assert "</body>" in html_content, "应该正确闭合body标签"
            
            # 验证元数据
            assert '<meta charset="UTF-8">' in html_content, "应该包含字符编码声明"
            assert "<title>" in html_content, "应该包含标题标签"
            
            # 验证样式
            assert "<style>" in html_content, "应该包含样式定义"
            assert "</style>" in html_content, "样式标签应该正确闭合"
            
            # 验证内容转换
            assert code_element.name in html_content, "HTML应该包含原始内容"
            
            # 验证代码高亮
            if "```python" in documentation:
                # 应该有代码高亮相关的HTML标签
                assert any(tag in html_content for tag in ["<pre>", "<code>", "highlight"]), \
                    "应该包含代码高亮标签"
        
        asyncio.run(run_test())