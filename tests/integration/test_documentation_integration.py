"""
文档生成器集成测试

测试DocumentationGenerator与其他组件的集成。
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.codenexus.ai import create_documentation_generator
from src.codenexus.ai.ai_layer import AILayer
from src.codenexus.config import Config
from src.codenexus.models.core import CodeElement, ElementType


class TestDocumentationIntegration:
    """文档生成器集成测试类"""
    
    @pytest.fixture
    def mock_config(self):
        """创建模拟配置"""
        config = Config()
        config.ai.api_key = "test-key"
        config.ai.api_base = "https://api.test.com/v1"
        config.ai.model_name = "test-model"
        return config
    
    @pytest.fixture
    def mock_ai_layer(self, mock_config):
        """创建模拟AI层"""
        ai_layer = MagicMock(spec=AILayer)
        ai_layer.generate_documentation = AsyncMock()
        return ai_layer
    
    def test_create_documentation_generator(self, mock_ai_layer):
        """测试创建文档生成器"""
        doc_generator = create_documentation_generator(mock_ai_layer)
        
        assert doc_generator is not None
        assert doc_generator.ai_layer == mock_ai_layer
    
    @pytest.mark.asyncio
    async def test_end_to_end_api_documentation(self, mock_ai_layer):
        """测试端到端API文档生成"""
        # 设置AI层返回值
        mock_ai_layer.generate_documentation.return_value = """
# calculate_sum 函数

## 概述
这个函数计算两个数字的和。

## 参数
- a (int): 第一个数字
- b (int): 第二个数字

## 返回值
- int: 两个数字的和

## 使用示例
result = calculate_sum(5, 3)
print(result)  # 输出: 8
"""
        
        # 创建文档生成器
        doc_generator = create_documentation_generator(mock_ai_layer)
        
        # 创建测试代码元素
        code_element = CodeElement(
            name="calculate_sum",
            type=ElementType.FUNCTION,
            file_path="math_utils.py",
            line_number=10,
            parameters=["a: int", "b: int"],
            return_type="int",
            docstring="计算两个数字的和"
        )
        
        # 生成文档
        result = await doc_generator.generate_api_documentation(code_element)
        
        # 验证结果
        assert "calculate_sum API文档" in result
        assert "math_utils.py" in result
        assert "def calculate_sum(a: int, b: int) -> int:" in result
        assert "计算两个数字的和" in result
        
        # 验证AI层被调用
        mock_ai_layer.generate_documentation.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_end_to_end_module_documentation(self, mock_ai_layer):
        """测试端到端模块文档生成"""
        # 设置AI层返回值
        mock_ai_layer.generate_documentation.return_value = """
# 数学工具模块

## 概述
这个模块提供基本的数学计算功能。

## 主要功能
- 基本算术运算
- 数学常量定义
- 工具函数

## 架构设计
模块采用函数式设计，提供纯函数接口。
"""
        
        # 创建文档生成器
        doc_generator = create_documentation_generator(mock_ai_layer)
        
        # 创建测试模块元素
        module_elements = [
            CodeElement(name="add", type=ElementType.FUNCTION, file_path="math_utils.py"),
            CodeElement(name="subtract", type=ElementType.FUNCTION, file_path="math_utils.py"),
            CodeElement(name="PI", type=ElementType.VARIABLE, file_path="math_utils.py")
        ]
        
        # 生成文档
        result = await doc_generator.generate_module_documentation(
            module_elements, "math_utils"
        )
        
        # 验证结果
        assert "math_utils 模块文档" in result
        assert "**元素数量**: 3" in result
        assert "数学工具模块" in result
        assert "API参考" in result
        assert "[add]" in result
        assert "[subtract]" in result
        
        # 验证AI层被调用
        mock_ai_layer.generate_documentation.assert_called_once()
    
    def test_html_conversion_integration(self, mock_ai_layer):
        """测试HTML转换集成"""
        doc_generator = create_documentation_generator(mock_ai_layer)
        
        # 测试Markdown内容
        markdown_content = """
# 测试文档

## 概述
这是一个测试文档。

## 代码示例
```python
def hello():
    print("Hello, World!")
```

## 表格
| 参数 | 类型 | 描述 |
|------|------|------|
| name | str  | 名称 |
"""
        
        # 转换为HTML
        html_result = doc_generator.convert_to_html(markdown_content)
        
        # 验证HTML结构
        assert "<!DOCTYPE html>" in html_result
        assert "<html lang=\"zh-CN\">" in html_result
        assert "<meta charset=\"UTF-8\">" in html_result
        assert "<title>代码文档</title>" in html_result
        assert "font-family:" in html_result  # CSS样式
        
        # 验证内容转换
        assert "测试文档" in html_result
        assert "概述" in html_result
        assert "代码示例" in html_result
        assert "表格" in html_result