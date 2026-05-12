"""
大模型智能层模块

提供智能分析和生成能力。
"""

from .ai_layer import AILayer
from .documentation_generator import DocumentationGenerator
from .factory import (
    create_ai_layer,
    create_and_initialize_ai_layer,
    create_documentation_generator,
    create_and_initialize_documentation_generator,
)
from .utils import (
    build_code_context,
    clean_json_response,
    extract_code_snippets,
    format_ai_error,
    parse_ai_response,
    truncate_text,
    validate_ai_config,
)

__all__ = [
    "AILayer",
    "DocumentationGenerator",
    "create_ai_layer",
    "create_and_initialize_ai_layer",
    "create_documentation_generator",
    "create_and_initialize_documentation_generator",
    "build_code_context",
    "clean_json_response",
    "extract_code_snippets",
    "format_ai_error",
    "parse_ai_response",
    "truncate_text",
    "validate_ai_config",
]