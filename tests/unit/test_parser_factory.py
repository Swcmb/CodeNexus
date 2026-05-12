"""
解析器工厂的单元测试
"""

import pytest
from src.codenexus.exceptions import ConfigurationError
from src.codenexus.interfaces import CodeParserInterface
from src.codenexus.parser.parser_factory import ParserFactory, get_default_parser, get_parser
from src.codenexus.parser.tree_sitter_parser import TreeSitterParser


class TestParserFactory:
    """ParserFactory类的测试"""
    
    def setup_method(self):
        """测试前的设置"""
        # 清除实例以确保测试独立性
        ParserFactory.clear_instances()
    
    def test_get_available_parsers(self):
        """测试获取可用解析器列表"""
        parsers = ParserFactory.get_available_parsers()
        assert isinstance(parsers, list)
        assert "tree_sitter" in parsers
    
    def test_create_default_parser(self):
        """测试创建默认解析器"""
        parser = ParserFactory.create_parser()
        assert isinstance(parser, TreeSitterParser)
        assert isinstance(parser, CodeParserInterface)
    
    def test_create_tree_sitter_parser(self):
        """测试创建Tree-sitter解析器"""
        parser = ParserFactory.create_parser("tree_sitter")
        assert isinstance(parser, TreeSitterParser)
    
    def test_create_unsupported_parser(self):
        """测试创建不支持的解析器类型"""
        with pytest.raises(ConfigurationError) as exc_info:
            ParserFactory.create_parser("unsupported_parser")
        
        assert "不支持的解析器类型" in str(exc_info.value)
        assert "unsupported_parser" in str(exc_info.value)
    
    def test_singleton_behavior(self):
        """测试单例行为"""
        parser1 = ParserFactory.create_parser("tree_sitter")
        parser2 = ParserFactory.create_parser("tree_sitter")
        
        # 应该返回同一个实例
        assert parser1 is parser2
    
    def test_register_custom_parser(self):
        """测试注册自定义解析器"""
        
        class MockParser(CodeParserInterface):
            def parse_project(self, project_path: str):
                return []
            
            def parse_file(self, file_path: str):
                return None
            
            def extract_elements(self, ast):
                return []
            
            def extract_relationships(self, ast, elements):
                return []
            
            def get_supported_languages(self):
                return ["mock"]
        
        # 注册自定义解析器
        ParserFactory.register_parser("mock", MockParser)
        
        # 验证注册成功
        assert "mock" in ParserFactory.get_available_parsers()
        
        # 创建自定义解析器实例
        parser = ParserFactory.create_parser("mock")
        assert isinstance(parser, MockParser)
    
    def test_clear_instances(self):
        """测试清除实例"""
        # 创建一个实例
        parser1 = ParserFactory.create_parser("tree_sitter")
        
        # 清除实例
        ParserFactory.clear_instances()
        
        # 再次创建应该是新实例
        parser2 = ParserFactory.create_parser("tree_sitter")
        assert parser1 is not parser2
    
    def test_get_default_parser_function(self):
        """测试便捷函数get_default_parser"""
        parser = get_default_parser()
        assert isinstance(parser, TreeSitterParser)
    
    def test_get_parser_function(self):
        """测试便捷函数get_parser"""
        parser = get_parser("tree_sitter")
        assert isinstance(parser, TreeSitterParser)
        
        with pytest.raises(ConfigurationError):
            get_parser("nonexistent")