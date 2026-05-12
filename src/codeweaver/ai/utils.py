"""
AI层实用工具

提供AI层相关的辅助功能。
"""

import json
import re
from typing import Any, Dict, List, Optional, Union


def clean_json_response(response: str) -> str:
    """清理AI模型返回的JSON响应
    
    Args:
        response: 原始响应文本
        
    Returns:
        清理后的JSON字符串
    """
    # 移除markdown代码块标记
    response = re.sub(r'```json\s*', '', response)
    response = re.sub(r'```\s*$', '', response)
    
    # 移除多余的空白字符
    response = response.strip()
    
    # 尝试提取JSON部分
    json_match = re.search(r'\{.*\}', response, re.DOTALL)
    if json_match:
        response = json_match.group(0)
    
    return response


def parse_ai_response(response: str, expected_format: str = "json") -> Union[Dict[str, Any], List[str], str]:
    """解析AI模型响应
    
    Args:
        response: AI模型响应文本
        expected_format: 期望的格式 ("json", "list", "text")
        
    Returns:
        解析后的数据
    """
    if expected_format == "json":
        try:
            cleaned = clean_json_response(response)
            return json.loads(cleaned)
        except json.JSONDecodeError:
            # 如果JSON解析失败，返回包含原始文本的字典
            return {"raw_response": response}
    
    elif expected_format == "list":
        # 将响应分割为列表
        lines = [
            line.strip().lstrip("- ").lstrip("* ").lstrip("• ")
            for line in response.split("\n")
            if line.strip() and not line.strip().startswith("#")
        ]
        return [line for line in lines if line]
    
    else:  # text format
        return response.strip()


def build_code_context(
    code_elements: List[Any],
    max_elements: int = 10,
    include_metadata: bool = True
) -> str:
    """构建代码上下文字符串
    
    Args:
        code_elements: 代码元素列表
        max_elements: 最大包含元素数量
        include_metadata: 是否包含元数据
        
    Returns:
        格式化的代码上下文字符串
    """
    if not code_elements:
        return "无相关代码元素"
    
    context_parts = ["代码元素信息："]
    
    for i, element in enumerate(code_elements[:max_elements]):
        if hasattr(element, 'name') and hasattr(element, 'type'):
            context_parts.append(f"{i+1}. {element.name} ({element.type})")
            
            if hasattr(element, 'file_path'):
                context_parts.append(f"   文件: {element.file_path}")
            
            if hasattr(element, 'line_number'):
                context_parts.append(f"   行号: {element.line_number}")
            
            if include_metadata and hasattr(element, 'metadata') and element.metadata:
                context_parts.append(f"   元数据: {json.dumps(element.metadata, ensure_ascii=False)}")
            
            context_parts.append("")  # 空行分隔
    
    if len(code_elements) > max_elements:
        context_parts.append(f"... 还有 {len(code_elements) - max_elements} 个元素")
    
    return "\n".join(context_parts)


def truncate_text(text: str, max_length: int = 4000, suffix: str = "...") -> str:
    """截断文本到指定长度
    
    Args:
        text: 原始文本
        max_length: 最大长度
        suffix: 截断后缀
        
    Returns:
        截断后的文本
    """
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix


def extract_code_snippets(text: str) -> List[str]:
    """从文本中提取代码片段
    
    Args:
        text: 包含代码的文本
        
    Returns:
        代码片段列表
    """
    # 匹配代码块
    code_blocks = re.findall(r'```[\w]*\n(.*?)\n```', text, re.DOTALL)
    
    # 匹配行内代码
    inline_code = re.findall(r'`([^`]+)`', text)
    
    return code_blocks + inline_code


def format_ai_error(error: Exception, context: Optional[str] = None) -> str:
    """格式化AI错误信息
    
    Args:
        error: 异常对象
        context: 错误上下文
        
    Returns:
        格式化的错误信息
    """
    error_parts = [f"AI操作失败: {str(error)}"]
    
    if context:
        error_parts.append(f"上下文: {context}")
    
    if hasattr(error, '__cause__') and error.__cause__:
        error_parts.append(f"原因: {str(error.__cause__)}")
    
    return " | ".join(error_parts)


def validate_ai_config(config: Dict[str, Any]) -> List[str]:
    """验证AI配置
    
    Args:
        config: AI配置字典
        
    Returns:
        验证错误列表，空列表表示验证通过
    """
    errors = []
    
    # 检查必需字段
    required_fields = ["model_name", "api_key"]
    for field in required_fields:
        if not config.get(field):
            errors.append(f"缺少必需配置: {field}")
    
    # 检查数值范围
    if "max_tokens" in config:
        max_tokens = config["max_tokens"]
        if not isinstance(max_tokens, int) or max_tokens <= 0:
            errors.append("max_tokens必须是正整数")
    
    if "temperature" in config:
        temperature = config["temperature"]
        if not isinstance(temperature, (int, float)) or not (0 <= temperature <= 2):
            errors.append("temperature必须在0-2之间")
    
    if "timeout" in config:
        timeout = config["timeout"]
        if not isinstance(timeout, int) or timeout <= 0:
            errors.append("timeout必须是正整数")
    
    return errors