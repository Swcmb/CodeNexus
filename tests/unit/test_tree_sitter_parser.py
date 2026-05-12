"""
Tree-sitter解析器的单元测试
"""

import pytest
from src.codenexus.models.core import ElementType, RelationType
from src.codenexus.parser.tree_sitter_parser import TreeSitterParser


class TestTreeSitterParser:
    """TreeSitterParser类的测试"""
    
    def setup_method(self):
        """测试前的设置"""
        self.parser = TreeSitterParser()
    
    def test_parser_initialization(self):
        """测试解析器初始化"""
        assert self.parser is not None
        assert len(self.parser.get_supported_languages()) > 0
        assert "python" in self.parser.get_supported_languages()
    
    def test_language_detection(self):
        """测试语言检测"""
        assert self.parser._detect_language("test.py") == "python"
        assert self.parser._detect_language("test.java") == "java"
        assert self.parser._detect_language("test.js") == "javascript"
        assert self.parser._detect_language("test.txt") is None
    
    def test_parse_simple_python_code(self, tmp_path):
        """测试解析简单的Python代码"""
        # 创建测试文件
        test_file = tmp_path / "test.py"
        test_file.write_text("""
class Calculator:
    def add(self, a, b):
        return a + b
    
    def multiply(self, a, b):
        return a * b

def main():
    calc = Calculator()
    result = calc.add(1, 2)
    print(result)
""")
        
        # 解析文件
        result = self.parser.parse_file(str(test_file))
        
        assert result.success is True
        assert result.parse_result is not None
        assert result.parse_result.language == "python"
        
        elements = result.parse_result.elements
        assert len(elements) > 0
        
        # 检查是否找到了类和方法
        class_elements = [e for e in elements if e.type == ElementType.CLASS]
        function_elements = [e for e in elements if e.type == ElementType.FUNCTION]
        
        assert len(class_elements) >= 1
        assert len(function_elements) >= 1
        
        # 检查类名
        calculator_class = next((e for e in class_elements if e.name == "Calculator"), None)
        assert calculator_class is not None
        assert calculator_class.line_number > 0
    
    def test_parse_simple_java_code(self, tmp_path):
        """测试解析简单的Java代码"""
        # 创建测试文件
        test_file = tmp_path / "Calculator.java"
        test_file.write_text("""
public class Calculator {
    public int add(int a, int b) {
        return a + b;
    }
    
    public int multiply(int a, int b) {
        return a * b;
    }
}
""")
        
        # 解析文件
        result = self.parser.parse_file(str(test_file))
        
        assert result.success is True
        assert result.parse_result is not None
        assert result.parse_result.language == "java"
        
        elements = result.parse_result.elements
        assert len(elements) > 0
        
        # 检查是否找到了类和方法
        class_elements = [e for e in elements if e.type == ElementType.CLASS]
        method_elements = [e for e in elements if e.type == ElementType.METHOD]
        
        assert len(class_elements) >= 1
        assert len(method_elements) >= 1
        
        # 检查类名和可见性
        calculator_class = next((e for e in class_elements if e.name == "Calculator"), None)
        assert calculator_class is not None
        assert calculator_class.visibility == "public"
    
    def test_parse_javascript_code(self, tmp_path):
        """测试解析简单的JavaScript代码"""
        # 创建测试文件
        test_file = tmp_path / "calculator.js"
        test_file.write_text("""
class Calculator {
    add(a, b) {
        return a + b;
    }
    
    multiply(a, b) {
        return a * b;
    }
}

function main() {
    const calc = new Calculator();
    const result = calc.add(1, 2);
    console.log(result);
}
""")
        
        # 解析文件
        result = self.parser.parse_file(str(test_file))
        
        assert result.success is True
        assert result.parse_result is not None
        assert result.parse_result.language == "javascript"
        
        elements = result.parse_result.elements
        assert len(elements) > 0
        
        # 检查是否找到了类和方法
        class_elements = [e for e in elements if e.type == ElementType.CLASS]
        function_elements = [e for e in elements if e.type == ElementType.FUNCTION]
        method_elements = [e for e in elements if e.type == ElementType.METHOD]
        
        assert len(class_elements) >= 1
        assert len(function_elements) + len(method_elements) >= 1
    
    def test_parse_nonexistent_file(self):
        """测试解析不存在的文件"""
        result = self.parser.parse_file("nonexistent.py")
        
        assert result.success is False
        assert result.error_message is not None
    
    def test_parse_unsupported_file(self, tmp_path):
        """测试解析不支持的文件类型"""
        # 创建不支持的文件类型
        test_file = tmp_path / "test.txt"
        test_file.write_text("This is a text file")
        
        result = self.parser.parse_file(str(test_file))
        
        assert result.success is False
        assert "不支持的文件类型" in result.error_message
    
    def test_extract_elements_with_complexity(self, tmp_path):
        """测试提取元素时的复杂度计算"""
        # 创建包含复杂逻辑的Python文件
        test_file = tmp_path / "complex.py"
        test_file.write_text("""
def complex_function(x):
    if x > 0:
        for i in range(x):
            if i % 2 == 0:
                try:
                    result = i * 2
                except ValueError:
                    result = 0
            else:
                result = i
        return result
    else:
        return 0
""")
        
        result = self.parser.parse_file(str(test_file))
        
        assert result.success is True
        elements = result.parse_result.elements
        
        # 找到复杂函数
        complex_func = next((e for e in elements if e.name == "complex_function"), None)
        assert complex_func is not None
        assert complex_func.complexity > 1  # 应该有较高的复杂度
    
    def test_parse_project_directory(self, temp_project_dir):
        """测试解析项目目录"""
        results = self.parser.parse_project(str(temp_project_dir))
        
        assert len(results) > 0
        
        # 检查是否解析了多个文件
        file_paths = [r.file_path for r in results]
        assert len(set(file_paths)) > 1  # 应该有多个不同的文件
        
        # 检查是否找到了预期的元素
        all_elements = []
        for result in results:
            all_elements.extend(result.elements)
        
        class_names = [e.name for e in all_elements if e.type == ElementType.CLASS]
        assert "Calculator" in class_names or "AdvancedCalculator" in class_names