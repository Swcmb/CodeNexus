"""
缓存服务实现

提供Redis缓存功能，用于缓存查询结果和提高系统性能。
Redis为可选依赖，未安装时缓存功能自动禁用。
"""

import json
import hashlib
import logging
from typing import Any, Dict, List, Optional, Union
from datetime import timedelta

# Redis 可选导入：未安装时缓存功能自动降级为禁用状态
try:
    import redis
    from redis.exceptions import RedisError
    REDIS_AVAILABLE = True
except ImportError:
    redis = None  # type: ignore[assignment]
    RedisError = Exception  # type: ignore[misc,assignment]
    REDIS_AVAILABLE = False

from ..exceptions import CacheServiceError


logger = logging.getLogger(__name__)


class CacheService:
    """缓存服务类
    
    使用Redis实现查询结果缓存，支持智能缓存策略。
    """
    
    def __init__(self, 
                 host: str = "localhost",
                 port: int = 6379,
                 db: int = 0,
                 password: Optional[str] = None,
                 default_ttl: int = 3600):
        """初始化缓存服务
        
        Args:
            host: Redis主机地址
            port: Redis端口
            db: Redis数据库编号
            password: Redis密码
            default_ttl: 默认缓存过期时间（秒）
        """
        self.default_ttl = default_ttl

        # 检查 Redis 是否可用
        if not REDIS_AVAILABLE:
            logger.warning("redis 库未安装，缓存功能将被禁用。可通过 pip install codenexus[cache] 安装")
            self.redis_client = None
            self._enabled = False
            return

        try:
            self.redis_client = redis.Redis(
                host=host,
                port=port,
                db=db,
                password=password,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            # 测试连接
            self.redis_client.ping()
            logger.info(f"Redis缓存服务初始化成功: {host}:{port}")
            self._enabled = True
        except RedisError as e:
            logger.warning(f"Redis连接失败，缓存功能将被禁用: {e}")
            self.redis_client = None
            self._enabled = False
    
    def is_enabled(self) -> bool:
        """检查缓存服务是否可用
        
        Returns:
            缓存服务是否启用
        """
        return self._enabled
    
    def get(self, key: str) -> Optional[Any]:
        """从缓存获取数据
        
        Args:
            key: 缓存键
            
        Returns:
            缓存的数据，如果不存在则返回None
        """
        if not self._enabled:
            return None
        
        try:
            value = self.redis_client.get(key)
            if value:
                logger.debug(f"缓存命中: {key}")
                return json.loads(value)
            logger.debug(f"缓存未命中: {key}")
            return None
        except (RedisError, json.JSONDecodeError) as e:
            logger.error(f"缓存读取失败: {e}")
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """设置缓存数据
        
        Args:
            key: 缓存键
            value: 要缓存的数据
            ttl: 过期时间（秒），None使用默认值
            
        Returns:
            是否设置成功
        """
        if not self._enabled:
            return False
        
        try:
            ttl = ttl or self.default_ttl
            serialized_value = json.dumps(value, ensure_ascii=False)
            self.redis_client.setex(key, ttl, serialized_value)
            logger.debug(f"缓存设置成功: {key}, TTL: {ttl}秒")
            return True
        except (RedisError, TypeError, json.JSONEncodeError) as e:
            logger.error(f"缓存设置失败: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """删除缓存数据
        
        Args:
            key: 缓存键
            
        Returns:
            是否删除成功
        """
        if not self._enabled:
            return False
        
        try:
            result = self.redis_client.delete(key)
            logger.debug(f"缓存删除: {key}, 结果: {result}")
            return result > 0
        except RedisError as e:
            logger.error(f"缓存删除失败: {e}")
            return False
    
    def delete_pattern(self, pattern: str) -> int:
        """删除匹配模式的所有缓存
        
        Args:
            pattern: 键模式（支持通配符*）
            
        Returns:
            删除的键数量
        """
        if not self._enabled:
            return 0
        
        try:
            keys = self.redis_client.keys(pattern)
            if keys:
                deleted = self.redis_client.delete(*keys)
                logger.info(f"批量删除缓存: {pattern}, 删除数量: {deleted}")
                return deleted
            return 0
        except RedisError as e:
            logger.error(f"批量删除缓存失败: {e}")
            return 0
    
    def exists(self, key: str) -> bool:
        """检查缓存键是否存在
        
        Args:
            key: 缓存键
            
        Returns:
            键是否存在
        """
        if not self._enabled:
            return False
        
        try:
            return self.redis_client.exists(key) > 0
        except RedisError as e:
            logger.error(f"缓存检查失败: {e}")
            return False
    
    def clear_all(self) -> bool:
        """清空所有缓存
        
        Returns:
            是否清空成功
        """
        if not self._enabled:
            return False
        
        try:
            self.redis_client.flushdb()
            logger.info("清空所有缓存")
            return True
        except RedisError as e:
            logger.error(f"清空缓存失败: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息
        
        Returns:
            缓存统计信息字典
        """
        if not self._enabled:
            return {"enabled": False}
        
        try:
            info = self.redis_client.info()
            return {
                "enabled": True,
                "used_memory": info.get("used_memory_human", "N/A"),
                "connected_clients": info.get("connected_clients", 0),
                "total_keys": self.redis_client.dbsize(),
                "hits": info.get("keyspace_hits", 0),
                "misses": info.get("keyspace_misses", 0),
                "hit_rate": self._calculate_hit_rate(
                    info.get("keyspace_hits", 0),
                    info.get("keyspace_misses", 0)
                )
            }
        except RedisError as e:
            logger.error(f"获取缓存统计失败: {e}")
            return {"enabled": True, "error": str(e)}
    
    def _calculate_hit_rate(self, hits: int, misses: int) -> float:
        """计算缓存命中率
        
        Args:
            hits: 命中次数
            misses: 未命中次数
            
        Returns:
            命中率（0-1）
        """
        total = hits + misses
        if total == 0:
            return 0.0
        return hits / total
    
    @staticmethod
    def generate_cache_key(prefix: str, *args, **kwargs) -> str:
        """生成缓存键
        
        Args:
            prefix: 键前缀
            *args: 位置参数
            **kwargs: 关键字参数
            
        Returns:
            生成的缓存键
        """
        # 将参数序列化为字符串
        key_parts = [prefix]
        
        for arg in args:
            if isinstance(arg, (list, dict)):
                key_parts.append(json.dumps(arg, sort_keys=True, ensure_ascii=False))
            else:
                key_parts.append(str(arg))
        
        for k, v in sorted(kwargs.items()):
            if isinstance(v, (list, dict)):
                key_parts.append(f"{k}={json.dumps(v, sort_keys=True, ensure_ascii=False)}")
            else:
                key_parts.append(f"{k}={v}")
        
        # 生成键的哈希值以避免键过长
        key_string = ":".join(key_parts)
        key_hash = hashlib.md5(key_string.encode()).hexdigest()
        
        return f"{prefix}:{key_hash}"


class SmartCacheStrategy:
    """智能缓存策略
    
    根据查询类型和数据特征自动调整缓存策略。
    """
    
    # 不同查询类型的默认TTL（秒）
    TTL_CONFIG = {
        "graph_query": 1800,      # 图查询：30分钟
        "impact_analysis": 900,    # 影响分析：15分钟
        "qa_answer": 3600,         # 问答结果：1小时
        "documentation": 7200,     # 文档生成：2小时
        "risk_detection": 1800,    # 风险检测：30分钟
        "path_query": 1800,        # 路径查询：30分钟
        "neighbor_query": 600,     # 邻居查询：10分钟
    }
    
    def __init__(self, cache_service: CacheService):
        """初始化智能缓存策略
        
        Args:
            cache_service: 缓存服务实例
        """
        self.cache_service = cache_service
    
    def get_ttl(self, query_type: str, result_size: int = 0) -> int:
        """获取查询类型的TTL
        
        Args:
            query_type: 查询类型
            result_size: 结果大小（用于动态调整）
            
        Returns:
            TTL（秒）
        """
        base_ttl = self.TTL_CONFIG.get(query_type, 1800)
        
        # 根据结果大小调整TTL
        # 结果越大，缓存时间越长（因为计算成本更高）
        if result_size > 1000:
            return int(base_ttl * 1.5)
        elif result_size > 100:
            return int(base_ttl * 1.2)
        
        return base_ttl
    
    def should_cache(self, query_type: str, result: Any) -> bool:
        """判断是否应该缓存结果
        
        Args:
            query_type: 查询类型
            result: 查询结果
            
        Returns:
            是否应该缓存
        """
        # 空结果不缓存
        if not result:
            return False
        
        # 错误结果不缓存
        if isinstance(result, dict) and result.get("error"):
            return False
        
        # 非常小的结果可能不值得缓存
        if isinstance(result, (list, dict)):
            try:
                result_str = json.dumps(result, default=str)
                if len(result_str) < 50:  # 小于50字节
                    return False
            except (TypeError, ValueError):
                # 如果无法序列化，仍然缓存（可能是复杂对象）
                pass
        
        return True
    
    def invalidate_related_cache(self, graph_id: str, changed_node_ids: List[str]):
        """使相关缓存失效
        
        当代码发生变更时，清除相关的缓存。
        
        Args:
            graph_id: 图谱ID
            changed_node_ids: 变更的节点ID列表
        """
        if not self.cache_service.is_enabled():
            return
        
        # 清除图查询缓存
        self.cache_service.delete_pattern(f"graph_query:{graph_id}:*")
        
        # 清除影响分析缓存
        self.cache_service.delete_pattern(f"impact_analysis:{graph_id}:*")
        
        # 清除涉及变更节点的路径查询缓存
        for node_id in changed_node_ids:
            self.cache_service.delete_pattern(f"path_query:{graph_id}:*{node_id}*")
            self.cache_service.delete_pattern(f"neighbor_query:{graph_id}:{node_id}:*")
        
        logger.info(f"已清除图谱 {graph_id} 的相关缓存")
