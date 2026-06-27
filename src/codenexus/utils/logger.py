"""
日志配置

提供统一的日志配置和管理。
"""

import logging
import sys
from typing import Optional


def setup_logger(
    name: str,
    level: str = "INFO",
    format_string: Optional[str] = None,
    handler: Optional[logging.Handler] = None
) -> logging.Logger:
    """
    设置日志记录器
    
    Args:
        name: 日志记录器名称
        level: 日志级别
        format_string: 日志格式字符串
        handler: 自定义处理器
    
    Returns:
        配置好的日志记录器
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))
    
    # 避免重复添加处理器
    if logger.handlers:
        return logger
    
    # 默认格式
    if format_string is None:
        format_string = (
            "%(asctime)s - %(name)s - %(levelname)s - "
            "%(filename)s:%(lineno)d - %(message)s"
        )
    
    formatter = logging.Formatter(format_string)
    
    # 默认处理器
    if handler is None:
        handler = logging.StreamHandler(sys.stdout)
    
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    return logger


# 创建默认的系统日志记录器
system_logger = setup_logger("codenexus")
parser_logger = setup_logger("codenexus.parser")
graph_logger = setup_logger("codenexus.graph")
database_logger = setup_logger("codenexus.database")
ai_logger = setup_logger("codenexus.ai")
service_logger = setup_logger("codenexus.service")