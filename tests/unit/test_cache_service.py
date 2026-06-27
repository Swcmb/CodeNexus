"""
缓存服务测试
"""

import json
import pytest
from unittest.mock import Mock, patch

# Redis 可选导入，与 cache_service.py 保持一致
try:
    import redis as _redis_module
    REDIS_AVAILABLE = True
except ImportError:
    _redis_module = None  # type: ignore[assignment]
    REDIS_AVAILABLE = False

from src.codenexus.services.cache_service import CacheService, SmartCacheStrategy


class TestCacheService:
    """缓存服务测试类"""

    @pytest.mark.skipif(not REDIS_AVAILABLE, reason="redis 未安装")
    def test_cache_service_disabled_when_redis_unavailable(self):
        """测试Redis不可用时缓存服务被禁用"""
        with patch('redis.Redis') as mock_redis:
            mock_redis.return_value.ping.side_effect = _redis_module.RedisError("Connection failed")
            
            cache_service = CacheService()
            
            assert not cache_service.is_enabled()
            assert cache_service.get("test_key") is None
            assert not cache_service.set("test_key", "test_value")
    
    @pytest.mark.skipif(not REDIS_AVAILABLE, reason="redis 未安装")
    def test_cache_service_basic_operations(self):
        """测试缓存服务基本操作"""
        with patch('redis.Redis') as mock_redis:
            mock_client = Mock()
            mock_redis.return_value = mock_client
            mock_client.ping.return_value = True
            
            cache_service = CacheService()
            
            # 测试设置缓存
            mock_client.setex.return_value = True
            result = cache_service.set("test_key", {"data": "test"})
            assert result is True
            
            # 验证调用参数
            mock_client.setex.assert_called_once()
            args = mock_client.setex.call_args[0]
            assert args[0] == "test_key"
            assert args[1] == 3600  # 默认TTL
            assert json.loads(args[2]) == {"data": "test"}
    
    @pytest.mark.skipif(not REDIS_AVAILABLE, reason="redis 未安装")
    def test_cache_service_get_operations(self):
        """测试缓存获取操作"""
        with patch('redis.Redis') as mock_redis:
            mock_client = Mock()
            mock_redis.return_value = mock_client
            mock_client.ping.return_value = True
            
            cache_service = CacheService()
            
            # 测试缓存命中
            mock_client.get.return_value = json.dumps({"data": "test"})
            result = cache_service.get("test_key")
            assert result == {"data": "test"}
            
            # 测试缓存未命中
            mock_client.get.return_value = None
            result = cache_service.get("missing_key")
            assert result is None
    
    def test_cache_key_generation(self):
        """测试缓存键生成"""
        key1 = CacheService.generate_cache_key("prefix", "arg1", "arg2", param1="value1")
        key2 = CacheService.generate_cache_key("prefix", "arg1", "arg2", param1="value1")
        key3 = CacheService.generate_cache_key("prefix", "arg1", "arg3", param1="value1")
        
        # 相同参数应该生成相同的键
        assert key1 == key2
        
        # 不同参数应该生成不同的键
        assert key1 != key3
        
        # 键应该包含前缀
        assert key1.startswith("prefix:")


class TestSmartCacheStrategy:
    """智能缓存策略测试类"""
    
    def test_ttl_configuration(self):
        """测试TTL配置"""
        mock_cache_service = Mock()
        strategy = SmartCacheStrategy(mock_cache_service)
        
        # 测试不同查询类型的TTL
        assert strategy.get_ttl("graph_query") == 1800
        assert strategy.get_ttl("qa_answer") == 3600
        assert strategy.get_ttl("unknown_type") == 1800  # 默认值
    
    def test_ttl_adjustment_by_result_size(self):
        """测试根据结果大小调整TTL"""
        mock_cache_service = Mock()
        strategy = SmartCacheStrategy(mock_cache_service)
        
        base_ttl = strategy.get_ttl("graph_query")
        
        # 大结果应该有更长的TTL
        large_result_ttl = strategy.get_ttl("graph_query", result_size=2000)
        assert large_result_ttl > base_ttl
        
        # 中等结果应该有稍长的TTL
        medium_result_ttl = strategy.get_ttl("graph_query", result_size=500)
        assert medium_result_ttl > base_ttl
        assert medium_result_ttl < large_result_ttl
    
    def test_should_cache_logic(self):
        """测试缓存判断逻辑"""
        mock_cache_service = Mock()
        strategy = SmartCacheStrategy(mock_cache_service)
        
        # 正常结果应该缓存（足够大的数据）
        large_data = {"data": "test" * 20}  # 确保超过50字节
        assert strategy.should_cache("graph_query", large_data)
        
        # 空结果不应该缓存
        assert not strategy.should_cache("graph_query", None)
        assert not strategy.should_cache("graph_query", [])
        assert not strategy.should_cache("graph_query", {})
        
        # 错误结果不应该缓存
        assert not strategy.should_cache("graph_query", {"error": "something went wrong"})
        
        # 过小的结果不应该缓存
        small_result = {"x": "y"}  # 很小的JSON
        assert not strategy.should_cache("graph_query", small_result)
    
    def test_invalidate_related_cache(self):
        """测试相关缓存失效"""
        mock_cache_service = Mock()
        mock_cache_service.is_enabled.return_value = True
        
        strategy = SmartCacheStrategy(mock_cache_service)
        
        graph_id = "test_graph"
        changed_nodes = ["node1", "node2"]
        
        strategy.invalidate_related_cache(graph_id, changed_nodes)
        
        # 验证删除模式调用
        expected_calls = [
            f"graph_query:{graph_id}:*",
            f"impact_analysis:{graph_id}:*",
        ]
        
        # 验证至少调用了基本的删除模式
        assert mock_cache_service.delete_pattern.call_count >= len(expected_calls)


if __name__ == "__main__":
    pytest.main([__file__])