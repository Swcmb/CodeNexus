#!/usr/bin/env python3
"""
文档生成器演示

展示如何使用DocumentationGenerator生成代码文档。
"""

import asyncio
import logging
import sys
from pathlib import Path

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from codenexus.ai import create_and_initialize_documentation_generator
from codenexus.config import Config
from codenexus.models.core import CodeElement, ElementType


# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def demo_api_documentation():
    """演示API文档生成"""
    print("=== API文档生成演示 ===")
    
    try:
        # 创建配置（使用模拟配置）
        config = Config()
        config.ai.api_key = "demo-key"
        config.ai.api_base = "https://api.deepseek.com/v1"
        config.ai.model_name = "deepseek-coder"
        
        # 创建文档生成器
        doc_generator = await create_and_initialize_documentation_generator(config)
        
        # 创建示例代码元素
        code_element = CodeElement(
            name="calculate_fibonacci",
            type=ElementType.FUNCTION,
            file_path="src/math_utils.py",
            line_number=15,
            parameters=["n: int"],
            return_type="int",
            docstring="计算斐波那契数列的第n项",
            complexity=3,
            metadata={
                "algorithm": "recursive",
                "time_complexity": "O(2^n)",
                "space_complexity": "O(n)"
            }
        )
        
        # 生成API文档
        print("正在生成API文档...")
        api_doc = await doc_generator.generate_api_documentation(
            code_element=code_element,
            related_elements=[],
            graph_context={
                "callers": ["main", "test_fibonacci"],
                "dependencies": ["math"]
            }
        )
        
        print("生成的API文档:")
        print("-" * 50)
        print(api_doc)
        print("-" * 50)
        
        # 转换为HTML
        print("\n正在转换为HTML...")
        html_doc = doc_generator.convert_to_html(api_doc)
        
        # 保存HTML文档
        output_path = Path("fibonacci_api_doc.html")
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_doc)
        
        print(f"HTML文档已保存到: {output_path}")
        
    except Exception as e:
        logger.error(f"API文档生成演示失败: {e}")
        print(f"演示失败: {e}")


async def demo_module_documentation():
    """演示模块文档生成"""
    print("\n=== 模块文档生成演示 ===")
    
    try:
        # 创建配置（使用模拟配置）
        config = Config()
        config.ai.api_key = "demo-key"
        config.ai.api_base = "https://api.deepseek.com/v1"
        config.ai.model_name = "deepseek-coder"
        
        # 创建文档生成器
        doc_generator = await create_and_initialize_documentation_generator(config)
        
        # 创建示例模块元素
        module_elements = [
            CodeElement(
                name="MathUtils",
                type=ElementType.CLASS,
                file_path="src/math_utils.py",
                line_number=1,
                docstring="数学工具类"
            ),
            CodeElement(
                name="calculate_fibonacci",
                type=ElementType.FUNCTION,
                file_path="src/math_utils.py",
                line_number=15,
                parameters=["n: int"],
                return_type="int",
                docstring="计算斐波那契数列"
            ),
            CodeElement(
                name="calculate_factorial",
                type=ElementType.FUNCTION,
                file_path="src/math_utils.py",
                line_number=25,
                parameters=["n: int"],
                return_type="int",
                docstring="计算阶乘"
            )
        ]
        
        # 生成模块文档
        print("正在生成模块文档...")
        module_doc = await doc_generator.generate_module_documentation(
            module_elements=module_elements,
            module_name="math_utils",
            graph=None
        )
        
        print("生成的模块文档:")
        print("-" * 50)
        print(module_doc)
        print("-" * 50)
        
    except Exception as e:
        logger.error(f"模块文档生成演示失败: {e}")
        print(f"演示失败: {e}")


async def demo_class_documentation():
    """演示类文档生成"""
    print("\n=== 类文档生成演示 ===")
    
    try:
        # 创建配置（使用模拟配置）
        config = Config()
        config.ai.api_key = "demo-key"
        config.ai.api_base = "https://api.deepseek.com/v1"
        config.ai.model_name = "deepseek-coder"
        
        # 创建文档生成器
        doc_generator = await create_and_initialize_documentation_generator(config)
        
        # 创建示例类元素
        class_element = CodeElement(
            name="Calculator",
            type=ElementType.CLASS,
            file_path="src/calculator.py",
            line_number=1,
            docstring="计算器类，提供基本数学运算功能"
        )
        
        # 创建方法列表
        methods = [
            CodeElement(
                name="__init__",
                type=ElementType.METHOD,
                file_path="src/calculator.py",
                line_number=5,
                parameters=["self"],
                docstring="初始化计算器"
            ),
            CodeElement(
                name="add",
                type=ElementType.METHOD,
                file_path="src/calculator.py",
                line_number=10,
                parameters=["self", "a: float", "b: float"],
                return_type="float",
                docstring="加法运算"
            ),
            CodeElement(
                name="multiply",
                type=ElementType.METHOD,
                file_path="src/calculator.py",
                line_number=15,
                parameters=["self", "a: float", "b: float"],
                return_type="float",
                docstring="乘法运算"
            )
        ]
        
        # 创建字段列表
        fields = [
            CodeElement(
                name="precision",
                type=ElementType.FIELD,
                file_path="src/calculator.py",
                line_number=3,
                docstring="计算精度"
            )
        ]
        
        # 生成类文档
        print("正在生成类文档...")
        class_doc = await doc_generator.generate_class_documentation(
            class_element=class_element,
            methods=methods,
            fields=fields,
            graph_context={
                "inheritance": [],
                "interfaces": [],
                "dependencies": ["math", "decimal"]
            }
        )
        
        print("生成的类文档:")
        print("-" * 50)
        print(class_doc)
        print("-" * 50)
        
    except Exception as e:
        logger.error(f"类文档生成演示失败: {e}")
        print(f"演示失败: {e}")


async def main():
    """主函数"""
    print("codenexus 文档生成器演示")
    print("=" * 50)
    
    # 注意：这个演示需要有效的AI API配置才能正常工作
    print("注意：此演示需要有效的AI API配置才能正常工作")
    print("当前使用的是模拟配置，实际调用会失败")
    print()
    
    try:
        await demo_api_documentation()
        await demo_module_documentation()
        await demo_class_documentation()
        
        print("\n演示完成！")
        
    except KeyboardInterrupt:
        print("\n演示被用户中断")
    except Exception as e:
        logger.error(f"演示过程中发生错误: {e}")
        print(f"演示失败: {e}")


if __name__ == "__main__":
    asyncio.run(main())