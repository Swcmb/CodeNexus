"""
缓存管理器

统一管理系统中的各种缓存，提供缓存预热、失效和监控功能。
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

from .cache_service import CacheService, SmartCacheStrategy
from ..models.core import CodeGraph


logger = logging.getLogger(__name__)


class CacheManager:
    """缓存管理器
    
    负责协调和管理系统中的所有缓存操作。
    """
    
    def __init__(self, cache_service: CacheService):
        """初始化缓存管理器
        
        Args:
            cache_service: 缓存服务实例
        """
        self.cache_service = cache_service
        self.cache_strategy = SmartCacheStrategy(cache_service)
        self._cache_stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "deletes": 0,
            "last_reset": datetime.now()
        }
    
    async def warm_up_cache(self, graph: CodeGraph, common_queries: Optional[List[Dict]] = None):
        """预热缓存
        
        预先计算和缓存常用的查询结果。
        
        Args:
            graph: 代码知识图谱
            common_queries: 常用查询列表
        """
        if not self.cache_service.is_enabled():
            logger.info("缓存服务未启用，跳过缓存预热")
            return
        
        logger.info("开始缓存预热")
        
        try:
            # 预热图统计信息
            await self._warm_up_graph_stats(graph)
            
            # 预热常用查询
            if common_queries:
                await self._warm_up_common_queries(graph, common_queries)
            
            # 预热热点节点的邻居信息
            await self._warm_up_hot_nodes(graph)
            
            logger.info("缓存预热完成")
            
        except Exception as e:
            logger.error(f"缓存预热失败: {e}")
    
    async def _warm_up_graph_stats(self, graph: CodeGraph):
        """预热图统计信息"""
        stats = {
            "total_nodes": len(graph.nodes),
            "total_edges": len(graph.edges),
            "node_types": {},
            "edge_types": {},
            "complexity_stats": {
                "min": float('inf'),
                "max": 0,
                "avg": 0,
                "total": 0
            }
        }
        
        total_complexity = 0
        
        # 统计节点信息
        for node in graph.nodes:
            node_type = node.type
            stats["node_types"][node_type] = stats["node_types"].get(node_type, 0) + 1
            
            # 统计复杂度
            element = node.get_property("element")
            if element and hasattr(element, 'complexity'):
                complexity = element.complexity
                stats["complexity_stats"]["min"] = min(stats["complexity_stats"]["min"], complexity)
                stats["complexity_stats"]["max"] = max(stats["complexity_stats"]["max"], complexity)
                total_complexity += complexity
        
        # 统计边信息
        for edge in graph.edges:
            edge_type = edge.type
            stats["edge_types"][edge_type] = stats["edge_types"].get(edge_type, 0) + 1
        
        # 计算平均复杂度
        if graph.nodes:
            stats["complexity_stats"]["avg"] = total_complexity / len(graph.nodes)
            stats["complexity_stats"]["total"] = total_complexity
            if stats["complexity_stats"]["min"] == float('inf'):
                stats["complexity_stats"]["min"] = 0
        
        # 缓存统计信息
        cache_key = CacheService.generate_cache_key("graph_stats", getattr(graph, 'id', 'default'))
        self.cache_service.set(cache_key, stats, 7200)  # 2小时TTL
        
        logger.debug("图统计信息已缓存")
    
    async def _warm_up_common_queries(self, graph: CodeGraph, common_queries: List[Dict]):
        """预热常用查询"""
        for query in common_queries:
            try:
                query_type = query.get("type")
                params = query.get("params", {})
                
                if query_type == "node_search":
                    # 预热节点搜索
                    await self._warm_up_node_search(graph, params)
                elif query_type == "path_query":
                    # 预热路径查询
                    await self._warm_up_path_query(graph, params)
                elif query_type == "impact_analysis":
                    # 预热影响分析
                    await self._warm_up_impact_analysis(graph, params)
                
            except Exception as e:
                logger.warning(f"预热查询失败: {query}, 错误: {e}")
    
    async def _warm_up_node_search(self, graph: CodeGraph, params: Dict):
        """预热节点搜索"""
        search_terms = params.get("terms", [])
        
        for term in search_terms:
            matching_nodes = []
            for node in graph.nodes:
                element = node.get_property("element")
                if element and term.lower() in element.name.lower():
                    matching_nodes.append({
                        "id": node.id,
                        "name": element.name,
                        "type": element.type,
                        "file_path": element.file_path,
                        "line_number": element.line_number
                    })
            
            cache_key = CacheService.generate_cache_key("node_search", term)
            self.cache_service.set(cache_key, matching_nodes, 1800)  # 30分钟TTL
    
    async def _warm_up_path_query(self, graph: CodeGraph, params: Dict):
        """预热路径查询"""
        # 这里可以预热一些常用的路径查询
        # 例如：主要类之间的依赖路径
        pass
    
    async def _warm_up_impact_analysis(self, graph: CodeGraph, params: Dict):
        """预热影响分析"""
        # 这里可以预热一些核心节点的影响分析
        # 例如：主要接口或基类的影响分析
        pass
    
    async def _warm_up_hot_nodes(self, graph: CodeGraph):
        """预热热点节点的邻居信息"""
        # 找出度数最高的节点（热点节点）
        node_degrees = {}
        
        for edge in graph.edges:
            node_degrees[edge.source_id] = node_degrees.get(edge.source_id, 0) + 1
            node_degrees[edge.target_id] = node_degrees.get(edge.target_id, 0) + 1
        
        # 选择度数最高的前10个节点
        hot_nodes = sorted(node_degrees.items(), key=lambda x: x[1], reverse=True)[:10]
        
        for node_id, degree in hot_nodes:
            # 预热邻居信息
            neighbors = []
            for edge in graph.edges:
                if edge.source_id == node_id:
                    neighbors.append({
                        "id": edge.target_id,
                        "type": edge.type,
                        "direction": "out"
                    })
                elif edge.target_id == node_id:
                    neighbors.append({
                        "id": edge.source_id,
                        "type": edge.type,
                        "direction": "in"
                    })
            
            cache_key = CacheService.generate_cache_key("node_neighbors", node_id)
            self.cache_service.set(cache_key, neighbors, 1800)  # 30分钟TTL
        
        logger.debug(f"已预热 {len(hot_nodes)} 个热点节点的邻居信息")
    
    def invalidate_graph_cache(self, graph_id: str, changed_node_ids: Optional[List[str]] = None):
        """使图相关缓存失效
        
        Args:
            graph_id: 图谱ID
            changed_node_ids: 变更的节点ID列表
        """
        if not self.cache_service.is_enabled():
            return
        
        logger.info(f"使图谱 {graph_id} 的缓存失效")
        
        # 使用智能缓存策略清除相关缓存
        self.cache_strategy.invalidate_related_cache(graph_id, changed_node_ids or [])
        
        # 清除图统计信息缓存
        stats_key = CacheService.generate_cache_key("graph_stats", graph_id)
        self.cache_service.delete(stats_key)
        
        # 如果有具体的变更节点，清除相关的节点缓存
        if changed_node_ids:
            for node_id in changed_node_ids:
                neighbor_key = CacheService.generate_cache_key("node_neighbors", node_id)
                self.cache_service.delete(neighbor_key)
        
        self._cache_stats["deletes"] += 1
    
    def get_cache_statistics(self) -> Dict[str, Any]:
        """获取缓存统计信息
        
        Returns:
            缓存统计信息
        """
        redis_stats = self.cache_service.get_stats()
        
        # 合并本地统计和Redis统计
        combined_stats = {
            **redis_stats,
            "local_stats": self._cache_stats,
            "uptime": (datetime.now() - self._cache_stats["last_reset"]).total_seconds()
        }
        
        return combined_stats
    
    def reset_statistics(self):
        """重置统计信息"""
        self._cache_stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "deletes": 0,
            "last_reset": datetime.now()
        }
        logger.info("缓存统计信息已重置")
    
    async def cleanup_expired_cache(self):
        """清理过期缓存
        
        定期清理任务，移除过期的缓存条目。
        """
        if not self.cache_service.is_enabled():
            return
        
        try:
            # Redis会自动处理过期键，这里主要是记录日志
            stats = self.cache_service.get_stats()
            logger.info(f"缓存清理完成，当前键数量: {stats.get('total_keys', 0)}")
            
        except Exception as e:
            logger.error(f"缓存清理失败: {e}")
    
    async def monitor_cache_health(self) -> Dict[str, Any]:
        """监控缓存健康状态
        
        Returns:
            缓存健康状态报告
        """
        if not self.cache_service.is_enabled():
            return {"status": "disabled", "message": "缓存服务未启用"}
        
        try:
            stats = self.cache_service.get_stats()
            
            # 计算健康指标
            hit_rate = stats.get("hit_rate", 0)
            memory_usage = stats.get("used_memory", "0B")
            total_keys = stats.get("total_keys", 0)
            
            # 判断健康状态
            if hit_rate >= 0.8:
                status = "excellent"
            elif hit_rate >= 0.6:
                status = "good"
            elif hit_rate >= 0.4:
                status = "fair"
            else:
                status = "poor"
            
            return {
                "status": status,
                "hit_rate": hit_rate,
                "memory_usage": memory_usage,
                "total_keys": total_keys,
                "recommendations": self._get_cache_recommendations(hit_rate, total_keys)
            }
            
        except Exception as e:
            logger.error(f"缓存健康监控失败: {e}")
            return {"status": "error", "message": str(e)}
    
    def _get_cache_recommendations(self, hit_rate: float, total_keys: int) -> List[str]:
        """获取缓存优化建议
        
        Args:
            hit_rate: 命中率
            total_keys: 总键数
            
        Returns:
            优化建议列表
        """
        recommendations = []
        
        if hit_rate < 0.5:
            recommendations.append("命中率较低，建议检查缓存策略和TTL设置")
        
        if total_keys > 100000:
            recommendations.append("缓存键数量较多，建议定期清理过期数据")
        
        if total_keys < 100:
            recommendations.append("缓存键数量较少，可以考虑增加预热策略")
        
        return recommendations