"""
健康检查路由

提供系统健康状态检查的API端点。
"""

import time
from datetime import datetime
from typing import Dict

from fastapi import APIRouter, Depends
from ..models import HealthCheckResponse
from ..dependencies import get_database_status, get_ai_service_status
from ...utils.monitoring import health_checker, metrics_collector, alert_manager

router = APIRouter()

# 应用启动时间
_start_time = time.time()


@router.get("/health", response_model=HealthCheckResponse)
async def health_check(
    db_status: Dict[str, str] = Depends(get_database_status),
    ai_status: Dict[str, str] = Depends(get_ai_service_status)
):
    """
    系统健康检查
    
    检查各个服务组件的状态，包括数据库连接、AI服务等。
    """
    current_time = time.time()
    uptime = current_time - _start_time
    
    # 汇总服务状态
    services = {
        "database": db_status.get("status", "unknown"),
        "ai_service": ai_status.get("status", "unknown"),
        "parser": "healthy",  # 解析器是本地服务，通常是健康的
        "graph_builder": "healthy"  # 图构建器是本地服务
    }
    
    # 判断整体状态
    overall_status = "healthy"
    if any(status != "healthy" for status in services.values()):
        overall_status = "degraded"
    if all(status == "unhealthy" for status in services.values()):
        overall_status = "unhealthy"
    
    return HealthCheckResponse(
        status=overall_status,
        services=services,
        uptime=uptime
    )


@router.get("/health/detailed")
async def detailed_health_check():
    """
    详细健康检查
    
    提供更详细的系统状态信息，包括监控指标。
    """
    import sys
    
    current_time = time.time()
    uptime = current_time - _start_time
    
    # 获取健康检查结果
    health_status = health_checker.run_health_checks()
    
    # 获取最新的系统指标
    latest_metrics = metrics_collector.get_latest_metrics()
    metrics_data = None
    if latest_metrics:
        metrics_data = {
            "cpu_percent": latest_metrics.cpu_percent,
            "memory_percent": latest_metrics.memory_percent,
            "memory_used_mb": latest_metrics.memory_used_mb,
            "disk_usage_percent": latest_metrics.disk_usage_percent,
            "active_connections": latest_metrics.active_connections,
            "response_time_avg": latest_metrics.response_time_avg,
            "error_rate": latest_metrics.error_rate
        }
    
    return {
        "status": health_status["overall_status"],
        "timestamp": datetime.now(),
        "uptime": uptime,
        "version": "0.1.0",
        "python_version": sys.version,
        "system": {
            "platform": sys.platform,
            "python_executable": sys.executable
        },
        "health_checks": health_status["checks"],
        "metrics": metrics_data
    }


@router.get("/metrics")
async def get_metrics():
    """
    获取系统指标
    
    返回当前的系统性能指标。
    """
    latest_metrics = metrics_collector.get_latest_metrics()
    if not latest_metrics:
        return {"message": "暂无指标数据"}
    
    return {
        "timestamp": latest_metrics.timestamp.isoformat(),
        "cpu_percent": latest_metrics.cpu_percent,
        "memory_percent": latest_metrics.memory_percent,
        "memory_used_mb": latest_metrics.memory_used_mb,
        "memory_available_mb": latest_metrics.memory_available_mb,
        "disk_usage_percent": latest_metrics.disk_usage_percent,
        "disk_free_gb": latest_metrics.disk_free_gb,
        "active_connections": latest_metrics.active_connections,
        "response_time_avg": latest_metrics.response_time_avg,
        "error_rate": latest_metrics.error_rate
    }


@router.get("/metrics/history")
async def get_metrics_history(hours: int = 1):
    """
    获取指标历史数据
    
    Args:
        hours: 获取过去几小时的数据，默认1小时
    """
    if hours < 1 or hours > 24:
        hours = 1
    
    history = metrics_collector.get_metrics_history(hours)
    
    return {
        "period_hours": hours,
        "data_points": len(history),
        "metrics": [
            {
                "timestamp": metrics.timestamp.isoformat(),
                "cpu_percent": metrics.cpu_percent,
                "memory_percent": metrics.memory_percent,
                "disk_usage_percent": metrics.disk_usage_percent,
                "response_time_avg": metrics.response_time_avg,
                "error_rate": metrics.error_rate
            }
            for metrics in history
        ]
    }


@router.get("/alerts")
async def get_alerts():
    """
    获取告警信息
    
    返回当前的告警规则和状态。
    """
    return {
        "alert_rules": [
            {
                "name": rule.name,
                "metric": rule.metric,
                "operator": rule.operator,
                "threshold": rule.threshold,
                "severity": rule.severity,
                "enabled": rule.enabled,
                "trigger_count": rule.trigger_count,
                "last_triggered": rule.last_triggered.isoformat() if rule.last_triggered else None
            }
            for rule in alert_manager.alert_rules
        ],
        "active_alerts": {
            name: timestamp.isoformat()
            for name, timestamp in alert_manager.active_alerts.items()
        }
    }


@router.get("/ping")
async def ping():
    """
    简单的ping检查
    
    用于负载均衡器或监控系统的快速健康检查。
    """
    return {"message": "pong", "timestamp": datetime.now()}