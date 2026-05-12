"""
文档生成器单元测试
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.codenexus.ai.documentation_generator import DocumentationGenerator
from src.codenexus.ai.ai_layer import AILayer
from src.codenexus.config import Config
from src.codenexus.exceptions import DocumentationError
from src.codenexus.models.core import CodeElement, ElementType


class TestDocumentationGenerator:
    """文档生成器测试类"""
    
    @pytest.fixture
    def mock_ai_layer(self):
        """创建模拟AI层"""
        ai_layer = MagicMock(spec=AILayer)
        ai_layer.generate_documentation = AsyncMock()
        return ai_layer
    
    @pytest.fixture
    def doc_generator(self, mock_ai_layer):
        """创建文档生成器实例"""
        with patch('src.codenexus.ai.documentation_generator.markdown.Markdown'):
            return DocumentationGenerator(mock_ai_layer)
    
    @pytest.fixture
    def sample_code_element(self):
        """创建示例代码元素"""
        return CodeElement(
            name="test_function",
            type=ElementType.FUNCTION,
            file_path="test.py",
            line_number=10,
            parameters=["param1: str", "param2: int"],
            return_type="bool",
            docstring="测试函数",
            complexity=2
        )
    
    @pytest.mark.asyncio
    async def test_generate_api_documentation_success(self, doc_generator, mock_ai_layer, sample_code_element):
        """测试成功生成API文档"""
        # 设置模拟返回值
        mock_ai_layer.generate_documentation.return_value = "# 测试函数\n\n这是一个测试函数。"
        
        # 调用方法
        result = await doc_generator.generate_api_documentation(sample_code_element)
        
        # 验证结果
        assert isinstance(result, str)
        assert "test_function API文档" in result
        assert "测试函数" in result
        assert "test.py" in result
        
        # 验证AI层被正确调用
        mock_ai_layer.generate_documentation.assert_called_once()
        call_args = mock_ai_layer.generate_documentation.call_args[0][0]
        assert call_args["code_element"] == sample_code_element
        assert call_args["documentation_type"] == "api"
    
    @pytest.mark.asyncio
    async def test_generate_api_documentation_with_related_elements(self, doc_generator, mock_ai_layer, sample_code_element):
        """测试生成包含相关元素的API文档"""
        # 创建相关元素
        related_element = CodeElement(
            name="helper_function",
            type=ElementType.FUNCTION,
            file_path="helper.py",
            line_number=5
        )
        
        # 设置模拟返回值
        mock_ai_layer.generate_documentation.return_value = "# 测试函数\n\n这是一个测试函数。"
        
        # 调用方法
        result = await doc_generator.generate_api_documentation(
            sample_code_element,
            related_elements=[related_element],
            graph_context={"dependencies": ["helper"]}
        )
        
        # 验证结果
        assert isinstance(result, str)
        assert "test_function API文档" in result
        
        # 验证AI层被正确调用
        call_args = mock_ai_layer.generate_documentation.call_args[0][0]
        assert len(call_args["related_elements"]) == 1
        assert call_args["related_elements"][0] == related_element
        assert call_args["graph_context"]["dependencies"] == ["helper"]
    
    @pytest.mark.asyncio
    async def test_generate_module_documentation_success(self, doc_generator, mock_ai_layer):
        """测试成功生成模块文档"""
        # 创建模块元素
        module_elements = [
            CodeElement(name="Class1", type=ElementType.CLASS, file_path="module.py"),
            CodeElement(name="function1", type=ElementType.FUNCTION, file_path="module.py"),
            CodeElement(name="function2", type=ElementType.FUNCTION, file_path="module.py")
        ]
        
        # 设置模拟返回值
        mock_ai_layer.generate_documentation.return_value = "# 测试模块\n\n这是一个测试模块。"
        
        # 调用方法
        result = await doc_generator.generate_module_documentation(
            module_elements=module_elements,
            module_name="test_module"
        )
        
        # 验证结果
        assert isinstance(result, str)
        assert "test_module 模块文档" in result
        assert "**元素数量**: 3" in result
        
        # 验证AI层被正确调用
        call_args = mock_ai_layer.generate_documentation.call_args[0][0]
        assert call_args["module_name"] == "test_module"
        assert len(call_args["module_elements"]) == 3
        assert call_args["documentation_type"] == "module"
    
    @pytest.mark.asyncio
    async def test_generate_class_documentation_success(self, doc_generator, mock_ai_layer):
        """测试成功生成类文档"""
        # 创建类元素
        class_element = CodeElement(
            name="TestClass",
            type=ElementType.CLASS,
            file_path="test_class.py",
            line_number=1
        )
        
        # 创建方法和字段
        methods = [
            CodeElement(name="__init__", type=ElementType.METHOD, file_path="test_class.py"),
            CodeElement(name="method1", type=ElementType.METHOD, file_path="test_class.py")
        ]
        fields = [
            CodeElement(name="field1", type=ElementType.FIELD, file_path="test_class.py")
        ]
        
        # 设置模拟返回值
        mock_ai_layer.generate_documentation.return_value = "# TestClass\n\n这是一个测试类。"
        
        # 调用方法
        result = await doc_generator.generate_class_documentation(
            class_element=class_element,
            methods=methods,
            fields=fields
        )
        
        # 验证结果
        assert isinstance(result, str)
        assert "TestClass 类文档" in result
        assert "**方法数量**: 2" in result
        assert "**字段数量**: 1" in result
        
        # 验证AI层被正确调用
        call_args = mock_ai_layer.generate_documentation.call_args[0][0]
        assert call_args["code_element"] == class_element
        assert len(call_args["methods"]) == 2
        assert len(call_args["fields"]) == 1
        assert call_args["documentation_type"] == "class"
    
    @pytest.mark.asyncio
    async def test_generate_documentation_ai_error(self, doc_generator, mock_ai_layer, sample_code_element):
        """测试AI层错误处理"""
        # 设置AI层抛出异常
        mock_ai_layer.generate_documentation.side_effect = Exception("AI服务不可用")
        
        # 验证异常被正确处理
        with pytest.raises(DocumentationError) as exc_info:
            await doc_generator.generate_api_documentation(sample_code_element)
        
        assert "API文档生成失败" in str(exc_info.value)
        assert "AI服务不可用" in str(exc_info.value)
    
    def test_convert_to_html_success(self, doc_generator):
        """测试Markdown转HTML成功"""
        # 模拟markdown处理器
        doc_generator._markdown_processor = MagicMock()
        doc_generator._markdown_processor.convert.return_value = "<h1>测试</h1>"
        
        # 调用方法
        result = doc_generator.convert_to_html("# 测试")
        
        # 验证结果
        assert isinstance(result, str)
        assert "<!DOCTYPE html>" in result
        assert "<h1>测试</h1>" in result
        assert 'charset="UTF-8"' in result
    
    def test_convert_to_html_error(self, doc_generator):
        """测试HTML转换错误处理"""
        # 模拟markdown处理器抛出异常
        doc_generator._markdown_processor = MagicMock()
        doc_generator._markdown_processor.convert.side_effect = Exception("转换失败")
        
        # 验证异常被正确处理
        with pytest.raises(DocumentationError) as exc_info:
            doc_generator.convert_to_html("# 测试")
        
        assert "HTML转换失败" in str(exc_info.value)
    
    def test_build_api_context(self, doc_generator, sample_code_element):
        """测试构建API上下文"""
        related_elements = [CodeElement(name="helper", type=ElementType.FUNCTION)]
        graph_context = {"dependencies": ["math"]}
        
        context = doc_generator._build_api_context(
            sample_code_element, related_elements, graph_context
        )
        
        # 验证上下文结构
        assert context["code_element"] == sample_code_element
        assert context["related_elements"] == related_elements
        assert context["graph_context"] == graph_context
        assert context["documentation_type"] == "api"
        assert context["requirements"]["include_signature"] is True
        assert context["requirements"]["include_parameters"] is True
        assert context["requirements"]["format"] == "markdown"
    
    def test_build_module_context(self, doc_generator):
        """测试构建模块上下文"""
        module_elements = [
            CodeElement(name="Class1", type=ElementType.CLASS),
            CodeElement(name="func1", type=ElementType.FUNCTION),
            CodeElement(name="Interface1", type=ElementType.INTERFACE)
        ]
        
        context = doc_generator._build_module_context(
            module_elements, "test_module", None
        )
        
        # 验证上下文结构
        assert context["module_name"] == "test_module"
        assert context["module_elements"] == module_elements
        assert len(context["classes"]) == 1
        assert len(context["functions"]) == 1
        assert len(context["interfaces"]) == 1
        assert context["documentation_type"] == "module"
        assert context["requirements"]["include_overview"] is True
    
    def test_generate_signature_function(self, doc_generator):
        """测试生成函数签名"""
        code_element = CodeElement(
            name="test_func",
            type=ElementType.FUNCTION,
            parameters=["a: int", "b: str"],
            return_type="bool"
        )
        
        signature = doc_generator._generate_signature(code_element)
        
        assert signature == "def test_func(a: int, b: str) -> bool:"
    
    def test_generate_signature_no_return_type(self, doc_generator):
        """测试生成无返回类型的函数签名"""
        code_element = CodeElement(
            name="test_func",
            type=ElementType.FUNCTION,
            parameters=["a: int"]
        )
        
        signature = doc_generator._generate_signature(code_element)
        
        assert signature == "def test_func(a: int):"
    
    def test_generate_signature_no_parameters(self, doc_generator):
        """测试生成无参数的函数签名"""
        code_element = CodeElement(
            name="test_func",
            type=ElementType.FUNCTION,
            return_type="None"
        )
        
        signature = doc_generator._generate_signature(code_element)
        
        assert signature == "def test_func() -> None:"
    
    def test_generate_signature_non_function(self, doc_generator):
        """测试非函数元素不生成签名"""
        code_element = CodeElement(
            name="TestClass",
            type=ElementType.CLASS
        )
        
        signature = doc_generator._generate_signature(code_element)
        
        assert signature == ""