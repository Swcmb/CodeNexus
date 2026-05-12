"""
任务调度器

提供定时任务调度功能，包括定时备份、系统维护等。
"""

import asyncio
import threading
import time
from datetime import datetime, timedelta
from typing import Callable, Dict, List, Optional
import logging

from .backup_recovery import create_scheduled_backup
from .logger import system_logger


class ScheduledTask:
    """定时任务"""
    
    def __init__(
        self,
        name: str,
        func: Callable,
        interval_seconds: int,
        enabled: bool = True,
        run_immediately: bool = False
    ):
        self.name = name
        self.func = func
        self.interval_seconds = interval_seconds
        self.enabled = enabled
        self.last_run: Optional[datetime] = None
        self.next_run: Optional[datetime] = None
        self.run_count = 0
        self.error_count = 0
        
        if run_immediately:
            self.next_run = datetime.now()
        else:
            self.next_run = datetime.now() + timedelta(seconds=interval_seconds)
    
    def should_run(self) -> bool:
        """检查是否应该运行"""
        if not self.enabled:
            return False
        
        return datetime.now() >= self.next_run
    
    def run(self):
        """执行任务"""
        try:
            system_logger.info(f"执行定时任务: {self.name}")
            self.func()
            self.last_run = datetime.now()
            self.next_run = self.last_run + timedelta(seconds=self.interval_seconds)
            self.run_count += 1
            system_logger.info(f"定时任务执行成功: {self.name}")
            
        except Exception as e:
            self.error_count += 1
            system_logger.error(f"定时任务执行失败: {self.name}, 错误: {e}")
            # 即使失败也要设置下次运行时间
            self.next_run = datetime.now() + timedelta(seconds=self.interval_seconds)
    
    def get_status(self) -> Dict:
        """获取任务状态"""
        return {
            "name": self.name,
            "enabled": self.enabled,
            "interval_seconds": self.interval_seconds,
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "next_run": self.next_run.isoformat() if self.next_run else None,
            "run_count": self.run_count,
            "error_count": self.error_count
        }


class TaskScheduler:
    """任务调度器"""
    
    def __init__(self):
        self.tasks: Dict[str, ScheduledTask] = {}
        self.is_running = False
        self.scheduler_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
    
    def add_task(self, task: ScheduledTask):
        """添加定时任务"""
        self.tasks[task.name] = task
        system_logger.info(f"添加定时任务: {task.name}, 间隔: {task.interval_seconds}秒")
    
    def remove_task(self, task_name: str):
        """移除定时任务"""
        if task_name in self.tasks:
            del self.tasks[task_name]
            system_logger.info(f"移除定时任务: {task_name}")
    
    def enable_task(self, task_name: str):
        """启用任务"""
        if task_name in self.tasks:
            self.tasks[task_name].enabled = True
            system_logger.info(f"启用定时任务: {task_name}")
    
    def disable_task(self, task_name: str):
        """禁用任务"""
        if task_name in self.tasks:
            self.tasks[task_name].enabled = False
            system_logger.info(f"禁用定时任务: {task_name}")
    
    def start(self):
        """启动调度器"""
        if self.is_running:
            return
        
        self.is_running = True
        self.stop_event.clear()
        self.scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self.scheduler_thread.start()
        system_logger.info("任务调度器已启动")
    
    def stop(self):
        """停止调度器"""
        if not self.is_running:
            return
        
        self.is_running = False
        self.stop_event.set()
        
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=5)
        
        system_logger.info("任务调度器已停止")
    
    def _scheduler_loop(self):
        """调度器主循环"""
        while self.is_running and not self.stop_event.is_set():
            try:
                # 检查所有任务
                for task in self.tasks.values():
                    if task.should_run():
                        # 在单独的线程中执行任务，避免阻塞调度器
                        task_thread = threading.Thread(
                            target=task.run,
                            daemon=True
                        )
                        task_thread.start()
                
                # 等待10秒后再次检查
                self.stop_event.wait(10)
                
            except Exception as e:
                system_logger.error(f"调度器循环异常: {e}")
                time.sleep(10)
    
    def get_status(self) -> Dict:
        """获取调度器状态"""
        return {
            "is_running": self.is_running,
            "task_count": len(self.tasks),
            "tasks": [task.get_status() for task in self.tasks.values()]
        }
    
    def run_task_now(self, task_name: str) -> bool:
        """立即运行指定任务"""
        if task_name not in self.tasks:
            return False
        
        try:
            task = self.tasks[task_name]
            task_thread = threading.Thread(target=task.run, daemon=True)
            task_thread.start()
            return True
        except Exception as e:
            system_logger.error(f"立即运行任务失败: {task_name}, 错误: {e}")
            return False


# 全局调度器实例
task_scheduler = TaskScheduler()


def setup_default_tasks():
    """设置默认的定时任务"""
    
    # 每日备份任务（每24小时执行一次）
    daily_backup_task = ScheduledTask(
        name="daily_backup",
        func=create_scheduled_backup,
        interval_seconds=24 * 3600,  # 24小时
        enabled=True,
        run_immediately=False
    )
    task_scheduler.add_task(daily_backup_task)
    
    # 系统状态保存任务（每小时执行一次）
    def save_system_state():
        from .backup_recovery import system_state_manager
        current_state = system_state_manager.get_system_status()
        system_state_manager.save_system_state(current_state)
    
    state_save_task = ScheduledTask(
        name="save_system_state",
        func=save_system_state,
        interval_seconds=3600,  # 1小时
        enabled=True,
        run_immediately=False
    )
    task_scheduler.add_task(state_save_task)
    
    # 日志清理任务（每周执行一次）
    def cleanup_logs():
        import os
        from pathlib import Path
        
        logs_dir = Path("logs")
        if not logs_dir.exists():
            return
        
        # 删除7天前的日志文件
        cutoff_time = datetime.now() - timedelta(days=7)
        for log_file in logs_dir.glob("*.log*"):
            if datetime.fromtimestamp(log_file.stat().st_mtime) < cutoff_time:
                try:
                    log_file.unlink()
                    system_logger.info(f"删除旧日志文件: {log_file}")
                except Exception as e:
                    system_logger.warning(f"删除日志文件失败: {log_file}, 错误: {e}")
    
    log_cleanup_task = ScheduledTask(
        name="cleanup_logs",
        func=cleanup_logs,
        interval_seconds=7 * 24 * 3600,  # 7天
        enabled=True,
        run_immediately=False
    )
    task_scheduler.add_task(log_cleanup_task)
    
    # 系统健康检查任务（每5分钟执行一次）
    def health_check():
        from .monitoring import health_checker
        health_status = health_checker.run_health_checks()
        if health_status["overall_status"] != "healthy":
            system_logger.warning(f"系统健康检查异常: {health_status}")
    
    health_check_task = ScheduledTask(
        name="health_check",
        func=health_check,
        interval_seconds=300,  # 5分钟
        enabled=True,
        run_immediately=True
    )
    task_scheduler.add_task(health_check_task)


def start_scheduler():
    """启动调度器"""
    setup_default_tasks()
    task_scheduler.start()


def stop_scheduler():
    """停止调度器"""
    task_scheduler.stop()


# 异步版本的调度器（用于FastAPI应用）
class AsyncTaskScheduler:
    """异步任务调度器"""
    
    def __init__(self):
        self.tasks: Dict[str, asyncio.Task] = {}
        self.is_running = False
    
    async def start(self):
        """启动异步调度器"""
        if self.is_running:
            return
        
        self.is_running = True
        
        # 启动定时备份任务
        self.tasks["daily_backup"] = asyncio.create_task(
            self._daily_backup_loop()
        )
        
        # 启动健康检查任务
        self.tasks["health_check"] = asyncio.create_task(
            self._health_check_loop()
        )
        
        system_logger.info("异步任务调度器已启动")
    
    async def stop(self):
        """停止异步调度器"""
        if not self.is_running:
            return
        
        self.is_running = False
        
        # 取消所有任务
        for task in self.tasks.values():
            task.cancel()
        
        # 等待任务完成
        await asyncio.gather(*self.tasks.values(), return_exceptions=True)
        self.tasks.clear()
        
        system_logger.info("异步任务调度器已停止")
    
    async def _daily_backup_loop(self):
        """每日备份循环"""
        while self.is_running:
            try:
                # 等待24小时
                await asyncio.sleep(24 * 3600)
                
                if self.is_running:
                    # 在线程池中执行备份（避免阻塞事件循环）
                    loop = asyncio.get_event_loop()
                    await loop.run_in_executor(None, create_scheduled_backup)
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                system_logger.error(f"异步备份任务异常: {e}")
                await asyncio.sleep(3600)  # 出错后等待1小时再重试
    
    async def _health_check_loop(self):
        """健康检查循环"""
        while self.is_running:
            try:
                # 等待5分钟
                await asyncio.sleep(300)
                
                if self.is_running:
                    from .monitoring import health_checker
                    health_status = health_checker.run_health_checks()
                    if health_status["overall_status"] != "healthy":
                        system_logger.warning(f"异步健康检查异常: {health_status}")
                        
            except asyncio.CancelledError:
                break
            except Exception as e:
                system_logger.error(f"异步健康检查任务异常: {e}")
                await asyncio.sleep(60)  # 出错后等待1分钟再重试


# 全局异步调度器实例
async_task_scheduler = AsyncTaskScheduler()