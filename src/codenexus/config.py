"""
系统配置管理

管理codenexus系统的配置参数。
"""

import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class DatabaseConfig:
    """数据库配置"""
    # 使用内存数据库，无需外部配置
    storage_type: str = "memory"
    cache_enabled: bool = True


@dataclass
class AIConfig:
    """AI模型配置"""
    model_name: str = "deepseek-coder"
    api_key: Optional[str] = None
    api_base: Optional[str] = None
    max_tokens: int = 4000
    temperature: float = 0.1
    timeout: int = 30


@dataclass
class ParserConfig:
    """解析器配置"""
    supported_languages: Optional[List[str]] = field(default=None)
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    timeout: int = 60
    parallel_workers: int = 4

    def __post_init__(self) -> None:
        if self.supported_languages is None:
            self.supported_languages = ["python", "java", "javascript", "c_sharp"]


@dataclass
class ServerConfig:
    """服务器配置"""
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    reload: bool = False
    workers: int = 1
    # API相关配置
    enable_auth: bool = False
    allowed_origins: Optional[List[str]] = field(default=None)
    trusted_hosts: Optional[List[str]] = field(default=None)
    rate_limit_calls: int = 100
    rate_limit_period: int = 60

    def __post_init__(self) -> None:
        if self.allowed_origins is None:
            self.allowed_origins = ["*"] if self.debug else []
        if self.trusted_hosts is None:
            # 在调试模式下允许所有主机，包括测试主机
            self.trusted_hosts = ["*"] if self.debug else ["localhost", "127.0.0.1", "testserver"]


@dataclass
class Config:
    """主配置类"""
    database: Optional[DatabaseConfig] = None
    ai: Optional[AIConfig] = None
    parser: Optional[ParserConfig] = None
    server: Optional[ServerConfig] = None

    def __post_init__(self) -> None:
        if self.database is None:
            self.database = DatabaseConfig()
        if self.ai is None:
            self.ai = AIConfig()
        if self.parser is None:
            self.parser = ParserConfig()
        if self.server is None:
            self.server = ServerConfig()


def load_config_from_env() -> Config:
    """从环境变量加载配置"""
    config = Config()

    # 数据库配置（内存模式）
    config.database.storage_type = os.getenv("DB_STORAGE_TYPE", config.database.storage_type)
    config.database.cache_enabled = os.getenv("DB_CACHE_ENABLED", "true").lower() == "true"

    # AI配置
    config.ai.model_name = os.getenv("AI_MODEL_NAME", config.ai.model_name)
    config.ai.api_key = os.getenv("AI_API_KEY", config.ai.api_key)
    config.ai.api_base = os.getenv("AI_API_BASE", config.ai.api_base)
    config.ai.max_tokens = int(os.getenv("AI_MAX_TOKENS", str(config.ai.max_tokens)))
    config.ai.temperature = float(os.getenv("AI_TEMPERATURE", str(config.ai.temperature)))
    config.ai.timeout = int(os.getenv("AI_TIMEOUT", str(config.ai.timeout)))

    # 解析器配置
    config.parser.max_file_size = int(os.getenv("PARSER_MAX_FILE_SIZE", str(config.parser.max_file_size)))
    config.parser.timeout = int(os.getenv("PARSER_TIMEOUT", str(config.parser.timeout)))
    config.parser.parallel_workers = int(os.getenv("PARSER_WORKERS", str(config.parser.parallel_workers)))

    # 服务器配置
    config.server.host = os.getenv("SERVER_HOST", config.server.host)
    config.server.port = int(os.getenv("SERVER_PORT", str(config.server.port)))
    config.server.debug = os.getenv("SERVER_DEBUG", "false").lower() == "true"
    config.server.reload = os.getenv("SERVER_RELOAD", "false").lower() == "true"
    config.server.workers = int(os.getenv("SERVER_WORKERS", str(config.server.workers)))
    config.server.enable_auth = os.getenv("ENABLE_AUTH", "false").lower() == "true"

    # CORS配置
    allowed_origins = os.getenv("ALLOWED_ORIGINS")
    if allowed_origins:
        config.server.allowed_origins = [origin.strip() for origin in allowed_origins.split(",")]

    # 受信任主机配置
    trusted_hosts = os.getenv("TRUSTED_HOSTS")
    if trusted_hosts:
        config.server.trusted_hosts = [host.strip() for host in trusted_hosts.split(",")]

    # 速率限制配置
    config.server.rate_limit_calls = int(os.getenv("RATE_LIMIT_CALLS", str(config.server.rate_limit_calls)))
    config.server.rate_limit_period = int(os.getenv("RATE_LIMIT_PERIOD", str(config.server.rate_limit_period)))

    return config


# 全局配置实例
config = load_config_from_env()


def get_settings() -> Config:
    """获取配置实例"""
    return config
