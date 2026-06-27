"""
AI层工厂函数

提供创建和配置AI层实例的工厂方法。
"""

import logging
from typing import Optional

from ..config import Config
from .ai_layer import AILayer
from .documentation_generator import DocumentationGenerator


logger = logging.getLogger(__name__)


def create_ai_layer(config: Optional[Config] = None) -> AILayer:
    """创建AI层实例
    
    Args:
        config: 配置对象，如果为None则使用默认配置
        
    Returns:
        配置好的AILayer实例
    """
    if config is None:
        from ..config import config as default_config
        config = default_config
    
    logger.info(f"创建AI层实例，模型: {config.ai.model_name}")
    return AILayer(config)


async def create_and_initialize_ai_layer(config: Optional[Config] = None) -> AILayer:
    """创建并初始化AI层实例
    
    Args:
        config: 配置对象，如果为None则使用默认配置
        
    Returns:
        已初始化的AILayer实例
    """
    ai_layer = create_ai_layer(config)
    await ai_layer.initialize()
    return ai_layer


def create_documentation_generator(ai_layer: AILayer) -> DocumentationGenerator:
    """创建文档生成器实例
    
    Args:
        ai_layer: 已初始化的AI层实例
        
    Returns:
        配置好的DocumentationGenerator实例
    """
    logger.info("创建文档生成器实例")
    return DocumentationGenerator(ai_layer)


async def create_and_initialize_documentation_generator(
    config: Optional[Config] = None
) -> DocumentationGenerator:
    """创建并初始化文档生成器实例
    
    Args:
        config: 配置对象，如果为None则使用默认配置
        
    Returns:
        已初始化的DocumentationGenerator实例
    """
    ai_layer = await create_and_initialize_ai_layer(config)
    return create_documentation_generator(ai_layer)