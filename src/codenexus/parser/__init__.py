"""
代码解析引擎模块

负责解析源代码并提取语法和语义信息。
"""

from .cross_file_analyzer import CrossFileAnalyzer
from .parser_factory import ParserFactory, get_default_parser, get_parser
from .relationship_extractor import RelationshipExtractor
from .tree_sitter_parser import TreeSitterParser

__all__ = [
    "TreeSitterParser",
    "RelationshipExtractor",
    "CrossFileAnalyzer",
    "ParserFactory", 
    "get_default_parser",
    "get_parser",
]