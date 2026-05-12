#!/usr/bin/env python3
"""
AI层演示脚本

演示如何使用codenexus的AI智能层功能。
"""

import asyncio
import os
from typing import Dict, Any

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.codenexus.ai import create_and_initialize_ai_layer
from src.codenexus.config import Config, AIConfig
from src.codenexus.models.core import CodeElement, ElementType


async def demo_ai_layer():
    """演示AI层的基本功能"""
    print("=== codenexus AI层演示 ===\n")
    
    # 配置AI层（需要设置真实的API密钥）
    config = Config()
    config.ai = AIConfig(
        model_name="deepseek-coder",
        api_key=os.getenv("DEEPSEEK_API_KEY", "demo-key"),  # 从环境变量获取
        api_base="https://api.deepseek.com/v1",
        max_tokens=2000,
        temperature=0.1,
        timeout=30
    )
    
    # 检查是否有真实的API密钥
    if config.ai.api_key == "demo-key":
        print("⚠️  警告: 未设置真实的API密钥，将跳过实际的AI调用演示")
        print("请设置环境变量 DEEPSEEK_API_KEY 来体验完整功能\n")
        demo_without_api()
        return
    
    try:
        # 创建并初始化AI层
        print("1. 初始化AI层...")
        ai_layer = await create_and_initialize_ai_layer(config)
        print("✅ AI层初始化成功\n")
        
        # 创建示例代码元素
        sample_function = CodeElement(
            id="func_001",
            name="calculate_fibonacci",
            type=ElementType.FUNCTION,
            file_path="/src/math_utils.py",
            line_number=15,
            complexity=8,
            metadata={
                "parameters": ["n: int"],
                "returns": "int",
                "description": "计算斐波那契数列的第n项",
                "docstring": "使用递归方法计算斐波那契数列"
            }
        )
        
        # 演示文档生成
        print("2. 演示文档生成...")
        doc_context = {
            "code_element": sample_function,
            "related_elements": [],
            "graph_context": {
                "module": "math_utils",
                "dependencies": ["typing"],
                "usage_count": 15
            }
        }
        
        documentation = await ai_layer.generate_documentation(doc_context)
        print("生成的文档:")
        print("-" * 50)
        print(documentation)
        print("-" * 50)
        print()
        
        # 演示问答功能
        print("3. 演示问答功能...")
        question = "这个函数的时间复杂度是多少？"
        qa_context = {
            "relevant_elements": [sample_function],
            "call_chain": ["main", "process_data", "calculate_fibonacci"],
            "graph_info": {"complexity": 8, "recursive": True}
        }
        
        answer = await ai_layer.answer_question(question, qa_context)
        print(f"问题: {question}")
        print(f"回答: {answer}")
        print()
        
        # 演示代码质量分析
        print("4. 演示代码质量分析...")
        quality_analysis = await ai_layer.analyze_code_quality(sample_function)
        print("质量分析结果:")
        print(f"- 总体评分: {quality_analysis.get('score', 'N/A')}")
        print(f"- 发现的问题: {len(quality_analysis.get('issues', []))}")
        print(f"- 改进建议: {len(quality_analysis.get('suggestions', []))}")
        print()
        
        # 演示改进建议
        print("5. 演示改进建议...")
        issues = [
            {"type": "performance", "description": "递归实现可能导致栈溢出"},
            {"type": "efficiency", "description": "重复计算相同的子问题"}
        ]
        
        suggestions = await ai_layer.suggest_improvements(issues)
        print("改进建议:")
        for i, suggestion in enumerate(suggestions, 1):
            print(f"{i}. {suggestion}")
        print()
        
        # 清理资源
        await ai_layer.cleanup()
        print("✅ AI层演示完成")
        
    except Exception as e:
        print(f"❌ 演示过程中出现错误: {e}")


def demo_without_api():
    """在没有API密钥时的演示"""
    print("=== 离线演示模式 ===\n")
    
    # 演示配置创建
    print("1. 创建AI配置...")
    config = Config()
    print(f"默认模型: {config.ai.model_name}")
    print(f"最大tokens: {config.ai.max_tokens}")
    print(f"温度参数: {config.ai.temperature}")
    print()
    
    # 演示代码元素创建
    print("2. 创建代码元素...")
    sample_function = CodeElement(
        name="example_function",
        type=ElementType.FUNCTION,
        file_path="/src/example.py",
        line_number=10,
        complexity=5
    )
    print(f"函数名: {sample_function.name}")
    print(f"类型: {sample_function.type.value}")
    print(f"复杂度: {sample_function.complexity}")
    print()
    
    # 演示提示词构建（不实际调用AI）
    print("3. 演示提示词构建...")
    from src.codenexus.ai.ai_layer import AILayer
    
    ai_layer = AILayer(config)
    prompt = ai_layer._build_documentation_prompt(
        sample_function, [], {"module": "example"}
    )
    print("生成的文档提示词:")
    print("-" * 30)
    print(prompt[:200] + "..." if len(prompt) > 200 else prompt)
    print("-" * 30)
    print()
    
    print("✅ 离线演示完成")
    print("\n💡 提示: 设置环境变量 DEEPSEEK_API_KEY 来体验完整的AI功能")


def main():
    """主函数"""
    try:
        asyncio.run(demo_ai_layer())
    except KeyboardInterrupt:
        print("\n👋 演示被用户中断")
    except Exception as e:
        print(f"❌ 演示失败: {e}")


if __name__ == "__main__":
    main()