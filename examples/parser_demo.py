"""
Tree-sitter解析器演示

展示如何使用codenexus的解析器功能。
"""

import sys
from pathlib import Path

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from codenexus.parser import get_default_parser
from codenexus.models.core import ElementType


def demo_parse_file():
    """演示解析单个文件"""
    print("=== 解析单个文件演示 ===")
    
    # 创建示例Python文件
    sample_code = '''
class Calculator:
    """一个简单的计算器类"""
    
    def __init__(self):
        self.history = []
    
    def add(self, a, b):
        """加法运算"""
        result = a + b
        self.history.append(f"{a} + {b} = {result}")
        return result
    
    def multiply(self, a, b):
        """乘法运算"""
        result = a * b
        self.history.append(f"{a} * {b} = {result}")
        return result

def main():
    calc = Calculator()
    result1 = calc.add(5, 3)
    result2 = calc.multiply(4, 6)
    print(f"Results: {result1}, {result2}")

if __name__ == "__main__":
    main()
'''
    
    # 保存到临时文件
    temp_file = Path("temp_calculator.py")
    temp_file.write_text(sample_code)
    
    try:
        # 获取解析器
        parser = get_default_parser()
        
        # 解析文件
        result = parser.parse_file(str(temp_file))
        
        if result.success:
            print(f"[OK] 成功解析文件: {result.parse_result.file_path}")
            print(f"[INFO] 语言: {result.parse_result.language}")
            print(f"[INFO] 解析时间: {result.parse_result.parse_time:.3f}秒")
            print(f"[INFO] 找到 {len(result.parse_result.elements)} 个代码元素")
            print(f"[INFO] 找到 {len(result.parse_result.relationships)} 个关系")
            
            print("\n[INFO] 代码元素详情:")
            for element in result.parse_result.elements:
                print(f"  - {element.type.value}: {element.name} "
                      f"(行 {element.line_number}-{element.end_line_number}, "
                      f"复杂度: {element.complexity})")
                if element.docstring:
                    print(f"    📖 文档: {element.docstring}")
                if element.parameters:
                    print(f"    [INFO] 参数: {', '.join(element.parameters)}")
            
            print("\n[INFO] 关系详情:")
            for relationship in result.parse_result.relationships:
                print(f"  - {relationship.type.value}: "
                      f"{relationship.source_id} -> {relationship.target_id}")
        else:
            print(f"[ERROR] 解析失败: {result.error_message}")
    
    finally:
        # 清理临时文件
        if temp_file.exists():
            temp_file.unlink()


def demo_supported_languages():
    """演示支持的语言"""
    print("\n=== 支持的编程语言 ===")
    
    parser = get_default_parser()
    languages = parser.get_supported_languages()
    
    print(f"[INFO] 支持 {len(languages)} 种编程语言:")
    for lang in languages:
        print(f"  - {lang}")


def demo_parse_multiple_languages():
    """演示解析多种语言"""
    print("\n=== 多语言解析演示 ===")
    
    # 示例代码
    samples = {
        "python": '''
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)
''',
        "java": '''
public class Fibonacci {
    public static int fibonacci(int n) {
        if (n <= 1) {
            return n;
        }
        return fibonacci(n-1) + fibonacci(n-2);
    }
}
''',
        "javascript": '''
function fibonacci(n) {
    if (n <= 1) {
        return n;
    }
    return fibonacci(n-1) + fibonacci(n-2);
}
'''
    }
    
    parser = get_default_parser()
    
    for language, code in samples.items():
        print(f"\n[INFO] 解析 {language.upper()} 代码:")
        
        # 创建临时文件
        extensions = {"python": ".py", "java": ".java", "javascript": ".js"}
        temp_file = Path(f"temp_fibonacci{extensions[language]}")
        temp_file.write_text(code)
        
        try:
            result = parser.parse_file(str(temp_file))
            
            if result.success:
                elements = result.parse_result.elements
                functions = [e for e in elements if e.type in [ElementType.FUNCTION, ElementType.METHOD]]
                classes = [e for e in elements if e.type == ElementType.CLASS]
                
                print(f"  [OK] 找到 {len(functions)} 个函数/方法, {len(classes)} 个类")
                
                for func in functions:
                    print(f"    [INFO] 函数: {func.name} (复杂度: {func.complexity})")
                
                for cls in classes:
                    print(f"    [INFO] 类: {cls.name}")
            else:
                print(f"  [ERROR] 解析失败: {result.error_message}")
        
        finally:
            if temp_file.exists():
                temp_file.unlink()


if __name__ == "__main__":
    print("[DEMO] codenexus 解析器演示")
    print("=" * 50)
    
    try:
        demo_supported_languages()
        demo_parse_file()
        demo_parse_multiple_languages()
        
        print("\n[SUCCESS] 演示完成！")
        
    except Exception as e:
        print(f"[ERROR] 演示过程中出现错误: {e}")
        import traceback
        traceback.print_exc()