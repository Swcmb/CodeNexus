"""
解析器工厂

提供统一的解析器创建和管理接口。
"""

from typing import Dict, Optional, Type

from ..exceptions import ConfigurationError
from ..interfaces import CodeParserInterface
from ..utils.logger import parser_logger
from .tree_sitter_parser import TreeSitterParser


class ParserFactory:
    """解析器工厂类"""
    
    _parsers: Dict[str, Type[CodeParserInterface]] = {
        "tree_sitter": TreeSitterParser,
    }
    
    _instances: Dict[str, CodeParserInterface] = {}
    
    @classmethod
    def register_parser(cls, name: str, parser_class: Type[CodeParserInterface]) -> None:
        """注册新的解析器类型"""
        cls._parsers[name] = parser_class
        parser_logger.info(f"已注册解析器: {name}")
    
    @classmethod
    def create_parser(cls, parser_type: str = "tree_sitter") -> CodeParserInterface:
        """创建解析器实例"""
        if parser_type not in cls._parsers:
            available_parsers = list(cls._parsers.keys())
            raise ConfigurationError(
                f"不支持的解析器类型: {parser_type}. "
                f"可用的解析器: {available_parsers}"
            )
        
        # 使用单例模式，避免重复初始化
        if parser_type not in cls._instances:
            parser_class = cls._parsers[parser_type]
            cls._instances[parser_type] = parser_class()
            parser_logger.info(f"创建解析器实例: {parser_type}")
        
        return cls._instances[parser_type]
    
    @classmethod
    def get_available_parsers(cls) -> list[str]:
        """获取可用的解析器类型列表"""
        return list(cls._parsers.keys())
    
    @classmethod
    def clear_instances(cls) -> None:
        """清除所有解析器实例（主要用于测试）"""
        cls._instances.clear()
        parser_logger.info("已清除所有解析器实例")


# 便捷函数
def get_default_parser() -> CodeParserInterface:
    """获取默认解析器"""
    return ParserFactory.create_parser("tree_sitter")


def get_parser(parser_type: str) -> CodeParserInterface:
    """获取指定类型的解析器"""
    return ParserFactory.create_parser(parser_type)