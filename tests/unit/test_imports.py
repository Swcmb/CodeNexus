"""
测试模块导入

确保所有模块都能正确导入。
"""

import pytest


class TestImports:
    """测试模块导入"""
    
    def test_core_models_import(self):
        """测试核心模型导入"""
        from src.codenexus.models.core import (
            CodeElement,
            CodeGraph,
            ElementType,
            GraphEdge,
            GraphNode,
            Relationship,
            RelationType,
        )
        
        # 验证类型可以正常实例化
        element = CodeElement()
        assert element is not None
        
        graph = CodeGraph()
        assert graph is not None
    
    def test_interfaces_import(self):
        """测试接口导入"""
        from src.codenexus.interfaces import (
            CodeParserInterface,
            GraphBuilderInterface,
            GraphDatabaseInterface,
            AILayerInterface,
        )
        
        # 验证接口类存在
        assert CodeParserInterface is not None
        assert GraphBuilderInterface is not None
        assert GraphDatabaseInterface is not None
        assert AILayerInterface is not None
    
    def test_config_import(self):
        """测试配置导入"""
        from src.codenexus.config import Config, config
        
        assert Config is not None
        assert config is not None
        assert hasattr(config, 'database')
        assert hasattr(config, 'ai')
        assert hasattr(config, 'parser')
        assert hasattr(config, 'server')
    
    def test_exceptions_import(self):
        """测试异常导入"""
        from src.codenexus.exceptions import (
            codenexusError,
            ParseError,
            GraphBuildError,
            DatabaseError,
            AIServiceError,
        )
        
        # 验证异常继承关系
        assert issubclass(ParseError, codenexusError)
        assert issubclass(GraphBuildError, codenexusError)
        assert issubclass(DatabaseError, codenexusError)
        assert issubclass(AIServiceError, codenexusError)
    
    def test_logger_import(self):
        """测试日志导入"""
        from src.codenexus.utils.logger import (
            setup_logger,
            system_logger,
            parser_logger,
        )
        
        assert setup_logger is not None
        assert system_logger is not None
        assert parser_logger is not None
        
        # 测试创建新的日志记录器
        test_logger = setup_logger("test")
        assert test_logger.name == "test"