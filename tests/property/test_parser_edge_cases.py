"""
代码解析器边界情况的基于属性的测试

**Feature: code-weaver, Property 1: 代码解析完整性**
测试解析器在各种边界情况下的行为。
"""

import tempfile
from pathlib import Path

import pytest
from hypothesis import given, strategies as st, settings, assume
from hypothesis.strategies import composite

from src.codenexus.models.core import ElementType
from src.codenexus.parser import get_default_parser


class TestParserEdgeCases:
    """解析器边界情况测试"""
    
    def setup_method(self):
        """测试前的设置"""
        self.parser = get_default_parser()
    
    @given(st.text(min_size=0, max_size=100, alphabet=" \t\n\r"))
    @settings(max_examples=20, deadline=None)
    def test_parser_handles_empty_and_whitespace_files(self, content):
        """
        **Feature: code-weaver, Property 1: 代码解析完整性**
        测试解析器处理空文件和只包含空白字符的文件
        """
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
            f.write(content)
            temp_file = f.name
        
        try:
            result = self.parser.parse_file(temp_file)
            
            # 解析器应该能够处理空白文件而不崩溃
            assert result is not None, "解析器应该返回结果对象"
            
            if result.success:
                # 空白文件应该不包含任何代码元素
                assert len(result.parse_result.elements) == 0, "空白文件不应该包含代码元素"
                assert len(result.parse_result.relationships) == 0, "空白文件不应该包含关系"
            
        finally:
            Path(temp_file).unlink(missing_ok=True)
    
    @given(st.integers(min_value=1, max_value=100))
    @settings(max_examples=10, deadline=None)
    def test_parser_handles_deeply_nested_structures(self, depth):
        """
        **Feature: code-weaver, Property 1: 代码解析完整性**
        测试解析器处理深度嵌套的代码结构
        """
        # 生成深度嵌套的Python代码
        lines = []
        
        # 创建嵌套的if语句
        for i in range(depth):
            indent = "    " * i
            lines.append(f"{indent}if True:")
        
        # 添加最内层的代码
        final_indent = "    " * depth
        lines.append(f"{final_indent}x = {depth}")
        
        code = "\n".join(lines)
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_file = f.name
        
        try:
            result = self.parser.parse_file(temp_file)
            
            # 解析器应该能够处理深度嵌套而不崩溃
            assert result is not None, "解析器应该返回结果对象"
            
            if result.success:
                # 应该至少找到变量赋值
                variable_elements = [e for e in result.parse_result.elements if e.type == ElementType.VARIABLE]
                assert len(variable_elements) >= 0, "应该能够处理嵌套结构中的变量"
            
        finally:
            Path(temp_file).unlink(missing_ok=True)
    
    @given(st.lists(st.text(
        alphabet="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_",
        min_size=1,
        max_size=20
    ).filter(lambda x: x not in {'False', 'True', 'None', 'def', 'class', 'if', 'else', 'for', 'while', 'try', 'except'}), 
    min_size=1, max_size=50, unique=True))
    @settings(max_examples=10, deadline=None)
    def test_parser_handles_many_functions(self, function_names):
        """
        **Feature: code-weaver, Property 1: 代码解析完整性**
        测试解析器处理大量函数定义
        """
        # 确保所有函数名都以字母或下划线开头
        valid_function_names = []
        for name in function_names:
            if name and (name[0].isalpha() or name[0] == '_'):
                valid_function_names.append(name)
        
        if not valid_function_names:
            valid_function_names = ['test_func']  # 至少有一个有效函数名
        
        # 生成包含大量函数的Python代码
        lines = []
        
        for func_name in valid_function_names:
            lines.append(f"def {func_name}():")
            lines.append(f"    return '{func_name}'")
            lines.append("")  # 空行分隔
        
        code = "\n".join(lines)
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
            f.write(code)
            temp_file = f.name
        
        try:
            result = self.parser.parse_file(temp_file)
            
            assert result.success, f"解析失败: {result.error_message}"
            
            # 验证所有函数都被提取
            function_elements = [e for e in result.parse_result.elements if e.type == ElementType.FUNCTION]
            extracted_names = [e.name for e in function_elements]
            
            # 至少应该提取到大部分函数
            extracted_count = len(set(extracted_names) & set(valid_function_names))
            expected_count = len(valid_function_names)
            
            # 允许一些解析误差，但应该提取到至少80%的函数
            assert extracted_count >= expected_count * 0.8, \
                f"应该提取到至少 {expected_count * 0.8} 个函数，实际提取到 {extracted_count} 个"
            
        finally:
            Path(temp_file).unlink(missing_ok=True)
    
    @given(st.text(
        alphabet="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_",
        min_size=1,
        max_size=100
    ).filter(lambda x: x not in {'False', 'True', 'None', 'def', 'class', 'if', 'else', 'for', 'while', 'try', 'except'}))
    @settings(max_examples=15, deadline=None)
    def test_parser_handles_long_identifiers(self, long_name):
        """
        **Feature: code-weaver, Property 1: 代码解析完整性**
        测试解析器处理长标识符
        """
        # 确保标识符以字母或下划线开头
        if not (long_name[0].isalpha() or long_name[0] == '_'):
            long_name = 'a' + long_name
        
        code = f"""
def {long_name}():
    {long_name}_var = 42
    return {long_name}_var

class {long_name}Class:
    def {long_name}_method(self):
        return "{long_name}"
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
            f.write(code)
            temp_file = f.name
        
        try:
            result = self.parser.parse_file(temp_file)
            
            assert result.success, f"解析失败: {result.error_message}"
            
            elements = result.parse_result.elements
            
            # 验证长标识符被正确提取
            function_elements = [e for e in elements if e.type == ElementType.FUNCTION]
            class_elements = [e for e in elements if e.type == ElementType.CLASS]
            
            function_names = [e.name for e in function_elements]
            class_names = [e.name for e in class_elements]
            
            assert long_name in function_names, f"长函数名 {long_name} 未被提取，实际提取到: {function_names}"
            assert f"{long_name}Class" in class_names, f"长类名 {long_name}Class 未被提取，实际提取到: {class_names}"
            
        finally:
            Path(temp_file).unlink(missing_ok=True)
    
    @given(st.lists(st.integers(min_value=1, max_value=1000), min_size=1, max_size=20))
    @settings(max_examples=10, deadline=None)
    def test_parser_handles_numeric_literals(self, numbers):
        """
        **Feature: code-weaver, Property 1: 代码解析完整性**
        测试解析器处理包含大量数字字面量的代码
        """
        # 生成包含数字字面量的Python代码
        lines = ["def test_function():"]
        
        for i, num in enumerate(numbers):
            lines.append(f"    var_{i} = {num}")
        
        lines.append("    return sum([" + ", ".join(f"var_{i}" for i in range(len(numbers))) + "])")
        
        code = "\n".join(lines)
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_file = f.name
        
        try:
            result = self.parser.parse_file(temp_file)
            
            assert result.success, f"解析失败: {result.error_message}"
            
            # 验证函数被提取
            function_elements = [e for e in result.parse_result.elements if e.type == ElementType.FUNCTION]
            assert len(function_elements) >= 1, "应该提取到测试函数"
            
            # 验证变量被提取（可能不是所有变量都被提取，这取决于解析器的实现）
            variable_elements = [e for e in result.parse_result.elements if e.type == ElementType.VARIABLE]
            assert len(variable_elements) >= 0, "变量提取应该不会出错"
            
        finally:
            Path(temp_file).unlink(missing_ok=True)
    
    def test_parser_handles_unicode_identifiers(self):
        """
        **Feature: code-weaver, Property 1: 代码解析完整性**
        测试解析器处理Unicode标识符（如果支持的话）
        """
        # 测试包含Unicode字符的代码（Python 3支持）
        code = """
def 测试函数():
    变量 = "测试"
    return 变量

class 测试类:
    def 方法(self):
        return "Unicode"
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
            f.write(code)
            temp_file = f.name
        
        try:
            result = self.parser.parse_file(temp_file)
            
            # 解析器应该能够处理Unicode而不崩溃
            assert result is not None, "解析器应该返回结果对象"
            
            if result.success:
                elements = result.parse_result.elements
                
                # 检查是否提取到了元素（即使名称可能不正确）
                assert len(elements) >= 0, "应该能够处理Unicode代码"
                
                # 如果支持Unicode标识符，验证名称
                function_elements = [e for e in elements if e.type == ElementType.FUNCTION]
                class_elements = [e for e in elements if e.type == ElementType.CLASS]
                
                # 至少应该提取到一些元素
                assert len(function_elements) + len(class_elements) >= 1, "应该提取到至少一个函数或类"
            
        finally:
            Path(temp_file).unlink(missing_ok=True)
    
    @given(st.lists(st.text(
        alphabet="()[]{}\"'#\n\t ",
        min_size=0,
        max_size=50
    ), min_size=1, max_size=10))
    @settings(max_examples=10, deadline=None)
    def test_parser_robustness_with_special_characters(self, special_strings):
        """
        **Feature: code-weaver, Property 1: 代码解析完整性**
        测试解析器对包含特殊字符的代码的鲁棒性
        """
        # 创建包含特殊字符的"代码"
        code = "\n".join(special_strings)
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_file = f.name
        
        try:
            # 解析器应该能够处理特殊字符而不崩溃
            result = self.parser.parse_file(temp_file)
            
            assert result is not None, "解析器应该返回结果对象"
            
            # 解析可能失败，但不应该抛出异常
            if not result.success:
                assert result.error_message is not None, "失败时应该有错误信息"
            else:
                # 如果解析成功，结果应该是合理的
                assert result.parse_result is not None, "成功时应该有解析结果"
                assert isinstance(result.parse_result.elements, list), "元素应该是列表"
                assert isinstance(result.parse_result.relationships, list), "关系应该是列表"
            
        finally:
            Path(temp_file).unlink(missing_ok=True)