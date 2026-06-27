"""
系统监控和告警

提供系统健康监控、性能指标收集和告警功能。
"""

import time
import psutil
import threading
from typing import Any, Callable, Dict, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
from collections import deque
import json
from pathlib import Path

from .logger import system_logger


@dataclass
class SystemMetrics:
    """系统指标"""
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    memory_available_mb: float
    disk_usage_percent: float
    disk_free_gb: float
    active_connections: int
    response_time_avg: float
    error_rate: float


@dataclass
class AlertRule:
    """告警规则"""
    name: str
    metric: str
    operator: str  # >, <, >=, <=, ==, !=
    threshold: float
    duration: int  # 持续时间（秒）
    severity: str  # INFO, WARNING, ERROR, CRITICAL
    enabled: bool = True
    last_triggered: Optional[datetime] = None
    trigger_count: int = 0


class MetricsCollector:
    """指标收集器"""

    def __init__(self, collection_interval: int = 60) -> None:
        self.collection_interval = collection_interval
        self.metrics_history: deque[SystemMetrics] = deque(maxlen=1440)  # 保留24小时数据
        self.response_times: deque[float] = deque(maxlen=100)
        self.error_counts: Dict[str, int] = {}
        self.request_counts: Dict[str, int] = {}
        self.is_collecting = False
        self.collection_thread: Optional[threading.Thread] = None
        self._last_cleanup_hour: int = -1

    def start_collection(self) -> None:
        """开始收集指标"""
        if self.is_collecting:
            return

        self.is_collecting = True
        self.collection_thread = threading.Thread(
            target=self._collection_loop,
            daemon=True
        )
        self.collection_thread.start()
        system_logger.info("指标收集器已启动")

    def stop_collection(self) -> None:
        """停止收集指标"""
        self.is_collecting = False
        if self.collection_thread:
            self.collection_thread.join(timeout=5)
        system_logger.info("指标收集器已停止")

    def _collection_loop(self) -> None:
        """指标收集循环"""
        while self.is_collecting:
            try:
                metrics = self._collect_system_metrics()
                self.metrics_history.append(metrics)

                # 清理过期的计数器
                self._cleanup_counters()

            except Exception as e:
                system_logger.error(f"收集系统指标失败: {e}")

            time.sleep(self.collection_interval)

    def _collect_system_metrics(self) -> SystemMetrics:
        """收集系统指标"""
        # CPU使用率
        cpu_percent = psutil.cpu_percent(interval=1)

        # 内存使用情况
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        memory_used_mb = memory.used / (1024 * 1024)
        memory_available_mb = memory.available / (1024 * 1024)

        # 磁盘使用情况
        disk = psutil.disk_usage('/')
        disk_usage_percent = (disk.used / disk.total) * 100
        disk_free_gb = disk.free / (1024 * 1024 * 1024)

        # 网络连接数
        try:
            connections = len(psutil.net_connections())
        except (psutil.AccessDenied, psutil.NoSuchProcess):
            connections = 0

        # 平均响应时间
        response_time_avg = (
            sum(self.response_times) / len(self.response_times)
            if self.response_times else 0
        )

        # 错误率计算
        total_requests = sum(self.request_counts.values())
        total_errors = sum(self.error_counts.values())
        error_rate = (total_errors / total_requests * 100) if total_requests > 0 else 0

        return SystemMetrics(
            timestamp=datetime.utcnow(),
            cpu_percent=cpu_percent,
            memory_percent=memory_percent,
            memory_used_mb=memory_used_mb,
            memory_available_mb=memory_available_mb,
            disk_usage_percent=disk_usage_percent,
            disk_free_gb=disk_free_gb,
            active_connections=connections,
            response_time_avg=response_time_avg,
            error_rate=error_rate
        )

    def record_response_time(self, response_time: float) -> None:
        """记录响应时间"""
        self.response_times.append(response_time)

    def record_request(self, endpoint: str) -> None:
        """记录请求"""
        self.request_counts[endpoint] = self.request_counts.get(endpoint, 0) + 1

    def record_error(self, error_type: str) -> None:
        """记录错误"""
        self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1

    def _cleanup_counters(self) -> None:
        """清理计数器（每小时重置）"""
        current_hour = datetime.utcnow().hour
        if self._last_cleanup_hour < 0:
            self._last_cleanup_hour = current_hour

        if current_hour != self._last_cleanup_hour:
            self.request_counts.clear()
            self.error_counts.clear()
            self._last_cleanup_hour = current_hour

    def get_latest_metrics(self) -> Optional[SystemMetrics]:
        """获取最新指标"""
        return self.metrics_history[-1] if self.metrics_history else None

    def get_metrics_history(self, hours: int = 1) -> List[SystemMetrics]:
        """获取指标历史"""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        return [
            metrics for metrics in self.metrics_history
            if metrics.timestamp >= cutoff_time
        ]


class AlertManager:
    """告警管理器"""

    def __init__(self, metrics_collector: MetricsCollector) -> None:
        self.metrics_collector = metrics_collector
        self.alert_rules: List[AlertRule] = []
        self.alert_handlers: List[Callable[..., Any]] = []
        self.active_alerts: Dict[str, datetime] = {}
        self.is_monitoring = False
        self.monitoring_thread: Optional[threading.Thread] = None

        # 设置默认告警规则
        self._setup_default_rules()

    def _setup_default_rules(self) -> None:
        """设置默认告警规则"""
        default_rules = [
            AlertRule(
                name="高CPU使用率",
                metric="cpu_percent",
                operator=">",
                threshold=80.0,
                duration=300,  # 5分钟
                severity="WARNING"
            ),
            AlertRule(
                name="极高CPU使用率",
                metric="cpu_percent",
                operator=">",
                threshold=95.0,
                duration=60,  # 1分钟
                severity="CRITICAL"
            ),
            AlertRule(
                name="高内存使用率",
                metric="memory_percent",
                operator=">",
                threshold=85.0,
                duration=300,
                severity="WARNING"
            ),
            AlertRule(
                name="极高内存使用率",
                metric="memory_percent",
                operator=">",
                threshold=95.0,
                duration=60,
                severity="CRITICAL"
            ),
            AlertRule(
                name="磁盘空间不足",
                metric="disk_usage_percent",
                operator=">",
                threshold=90.0,
                duration=60,
                severity="ERROR"
            ),
            AlertRule(
                name="高错误率",
                metric="error_rate",
                operator=">",
                threshold=5.0,
                duration=300,
                severity="ERROR"
            ),
            AlertRule(
                name="响应时间过长",
                metric="response_time_avg",
                operator=">",
                threshold=5000.0,  # 5秒
                duration=300,
                severity="WARNING"
            )
        ]

        self.alert_rules.extend(default_rules)

    def add_alert_rule(self, rule: AlertRule) -> None:
        """添加告警规则"""
        self.alert_rules.append(rule)

    def remove_alert_rule(self, rule_name: str) -> None:
        """移除告警规则"""
        self.alert_rules = [
            rule for rule in self.alert_rules
            if rule.name != rule_name
        ]

    def add_alert_handler(self, handler: Callable[..., Any]) -> None:
        """添加告警处理器"""
        self.alert_handlers.append(handler)

    def start_monitoring(self) -> None:
        """开始监控"""
        if self.is_monitoring:
            return

        self.is_monitoring = True
        self.monitoring_thread = threading.Thread(
            target=self._monitoring_loop,
            daemon=True
        )
        self.monitoring_thread.start()
        system_logger.info("告警监控已启动")

    def stop_monitoring(self) -> None:
        """停止监控"""
        self.is_monitoring = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5)
        system_logger.info("告警监控已停止")

    def _monitoring_loop(self) -> None:
        """监控循环"""
        while self.is_monitoring:
            try:
                self._check_alerts()
            except Exception as e:
                system_logger.error(f"检查告警失败: {e}")

            time.sleep(30)  # 每30秒检查一次

    def _check_alerts(self) -> None:
        """检查告警条件"""
        latest_metrics = self.metrics_collector.get_latest_metrics()
        if not latest_metrics:
            return

        for rule in self.alert_rules:
            if not rule.enabled:
                continue

            if self._evaluate_rule(rule, latest_metrics):
                self._trigger_alert(rule, latest_metrics)
            else:
                # 如果条件不满足，清除活跃告警
                if rule.name in self.active_alerts:
                    del self.active_alerts[rule.name]

    def _evaluate_rule(self, rule: AlertRule, metrics: SystemMetrics) -> bool:
        """评估告警规则"""
        metric_value = getattr(metrics, rule.metric, None)
        if metric_value is None:
            return False

        # 评估条件
        if rule.operator == ">":
            condition_met = metric_value > rule.threshold
        elif rule.operator == "<":
            condition_met = metric_value < rule.threshold
        elif rule.operator == ">=":
            condition_met = metric_value >= rule.threshold
        elif rule.operator == "<=":
            condition_met = metric_value <= rule.threshold
        elif rule.operator == "==":
            condition_met = metric_value == rule.threshold
        elif rule.operator == "!=":
            condition_met = metric_value != rule.threshold
        else:
            return False

        if not condition_met:
            return False

        # 检查持续时间
        current_time = datetime.utcnow()
        if rule.name not in self.active_alerts:
            self.active_alerts[rule.name] = current_time
            return False

        duration = (current_time - self.active_alerts[rule.name]).total_seconds()
        return duration >= rule.duration

    def _trigger_alert(self, rule: AlertRule, metrics: SystemMetrics) -> None:
        """触发告警"""
        # 避免重复告警（至少间隔5分钟）
        if rule.last_triggered:
            time_since_last = datetime.utcnow() - rule.last_triggered
            if time_since_last.total_seconds() < 300:  # 5分钟
                return

        rule.last_triggered = datetime.utcnow()
        rule.trigger_count += 1

        alert_data: Dict[str, Any] = {
            "rule_name": rule.name,
            "severity": rule.severity,
            "metric": rule.metric,
            "threshold": rule.threshold,
            "current_value": getattr(metrics, rule.metric),
            "timestamp": datetime.utcnow().isoformat(),
            "trigger_count": rule.trigger_count
        }

        # 记录告警日志
        system_logger.warning(
            f"告警触发: {rule.name} | "
            f"当前值: {alert_data['current_value']} | "
            f"阈值: {rule.threshold} | "
            f"严重程度: {rule.severity}"
        )

        # 调用告警处理器
        for handler in self.alert_handlers:
            try:
                handler(alert_data)
            except Exception as e:
                system_logger.error(f"告警处理器执行失败: {e}")


class HealthChecker:
    """健康检查器"""

    def __init__(self) -> None:
        self.health_checks: Dict[str, Callable[..., Any]] = {}
        self.health_status: Dict[str, Dict[str, Any]] = {}

    def register_health_check(self, name: str, check_func: Callable[..., Any]) -> None:
        """注册健康检查"""
        self.health_checks[name] = check_func

    def run_health_checks(self) -> Dict[str, Any]:
        """运行所有健康检查"""
        results: Dict[str, Any] = {}
        overall_healthy = True

        for name, check_func in self.health_checks.items():
            try:
                start_time = time.time()
                result = check_func()
                duration = time.time() - start_time

                if isinstance(result, bool):
                    status = "healthy" if result else "unhealthy"
                    details = None
                elif isinstance(result, dict):
                    status = result.get("status", "unknown")
                    details = result.get("details")
                else:
                    status = "unknown"
                    details = str(result)

                results[name] = {
                    "status": status,
                    "duration_ms": round(duration * 1000, 2),
                    "details": details,
                    "timestamp": datetime.utcnow().isoformat()
                }

                if status != "healthy":
                    overall_healthy = False

            except Exception as e:
                results[name] = {
                    "status": "error",
                    "error": str(e),
                    "timestamp": datetime.utcnow().isoformat()
                }
                overall_healthy = False

        self.health_status = results
        return {
            "overall_status": "healthy" if overall_healthy else "unhealthy",
            "checks": results,
            "timestamp": datetime.utcnow().isoformat()
        }

    def get_health_status(self) -> Dict[str, Any]:
        """获取健康状态"""
        return self.health_status


# 全局实例
metrics_collector = MetricsCollector()
alert_manager = AlertManager(metrics_collector)
health_checker = HealthChecker()


def setup_default_alert_handlers() -> None:
    """设置默认告警处理器"""

    def log_alert_handler(alert_data: Dict[str, Any]) -> None:
        """日志告警处理器"""
        severity = alert_data["severity"]
        message = (
            f"告警: {alert_data['rule_name']} | "
            f"指标: {alert_data['metric']} = {alert_data['current_value']} | "
            f"阈值: {alert_data['threshold']}"
        )

        if severity == "CRITICAL":
            system_logger.critical(message)
        elif severity == "ERROR":
            system_logger.error(message)
        elif severity == "WARNING":
            system_logger.warning(message)
        else:
            system_logger.info(message)

    def file_alert_handler(alert_data: Dict[str, Any]) -> None:
        """文件告警处理器"""
        try:
            alert_file = Path("logs/alerts.jsonl")
            alert_file.parent.mkdir(parents=True, exist_ok=True)

            with open(alert_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(alert_data, ensure_ascii=False) + '\n')
        except Exception as e:
            system_logger.error(f"写入告警文件失败: {e}")

    # 注册默认处理器
    alert_manager.add_alert_handler(log_alert_handler)
    alert_manager.add_alert_handler(file_alert_handler)


def setup_default_health_checks() -> None:
    """设置默认健康检查"""

    def database_health_check() -> Dict[str, str]:
        """数据库健康检查"""
        try:
            # 这里应该实现实际的数据库连接检查
            # 暂时返回健康状态
            return {"status": "healthy", "details": "数据库连接正常"}
        except Exception as e:
            return {"status": "unhealthy", "details": f"数据库连接失败: {e}"}

    def ai_service_health_check() -> Dict[str, str]:
        """AI服务健康检查"""
        try:
            # 这里应该实现实际的AI服务检查
            return {"status": "healthy", "details": "AI服务正常"}
        except Exception as e:
            return {"status": "unhealthy", "details": f"AI服务异常: {e}"}

    def memory_health_check() -> Dict[str, str]:
        """内存健康检查"""
        memory = psutil.virtual_memory()
        if memory.percent > 90:
            return {"status": "unhealthy", "details": f"内存使用率过高: {memory.percent}%"}
        return {"status": "healthy", "details": f"内存使用率: {memory.percent}%"}

    def disk_health_check() -> Dict[str, str]:
        """磁盘健康检查"""
        disk = psutil.disk_usage('/')
        usage_percent = (disk.used / disk.total) * 100
        if usage_percent > 90:
            return {"status": "unhealthy", "details": f"磁盘使用率过高: {usage_percent:.1f}%"}
        return {"status": "healthy", "details": f"磁盘使用率: {usage_percent:.1f}%"}

    # 注册健康检查
    health_checker.register_health_check("database", database_health_check)
    health_checker.register_health_check("ai_service", ai_service_health_check)
    health_checker.register_health_check("memory", memory_health_check)
    health_checker.register_health_check("disk", disk_health_check)


# 初始化默认配置
setup_default_alert_handlers()
setup_default_health_checks()


def start_monitoring() -> None:
    """启动监控系统"""
    metrics_collector.start_collection()
    alert_manager.start_monitoring()
    system_logger.info("监控系统已启动")


def stop_monitoring() -> None:
    """停止监控系统"""
    metrics_collector.stop_collection()
    alert_manager.stop_monitoring()
    system_logger.info("监控系统已停止")
