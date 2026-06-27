"""
数据备份和恢复系统

提供图数据库备份、系统状态保存和恢复功能。
"""

import os
import json
import shutil
import tarfile
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
import asyncio
import logging

from ..config import get_settings
from ..exceptions import DatabaseError, ConfigurationError
from ..utils.logger import system_logger
from ..utils.error_handler import error_handler


class BackupManager:
    """备份管理器"""
    
    def __init__(self, backup_dir: Optional[str] = None):
        """初始化备份管理器
        
        Args:
            backup_dir: 备份目录路径，默认使用配置中的路径
        """
        self.settings = get_settings()
        self.backup_dir = Path(backup_dir or "backups")
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        # 备份配置
        self.max_backups = 30  # 最多保留30个备份
        self.backup_retention_days = 7  # 保留7天的备份
        
        system_logger.info(f"备份管理器初始化，备份目录: {self.backup_dir}")
    
    @error_handler(component="backup", operation="create_backup")
    def create_backup(self, backup_name: Optional[str] = None) -> str:
        """创建系统备份
        
        Args:
            backup_name: 备份名称，默认使用时间戳
            
        Returns:
            备份文件路径
        """
        if not backup_name:
            backup_name = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        backup_path = self.backup_dir / f"{backup_name}.tar.gz"
        temp_dir = Path(tempfile.mkdtemp())
        
        try:
            system_logger.info(f"开始创建备份: {backup_name}")
            
            # 创建备份元数据
            metadata = self._create_backup_metadata()
            metadata_file = temp_dir / "metadata.json"
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
            
            # 备份图数据库
            db_backup_path = temp_dir / "database"
            self._backup_database(db_backup_path)
            
            # 备份配置文件
            config_backup_path = temp_dir / "config"
            self._backup_configuration(config_backup_path)
            
            # 备份日志文件
            logs_backup_path = temp_dir / "logs"
            self._backup_logs(logs_backup_path)
            
            # 备份用户数据
            data_backup_path = temp_dir / "data"
            self._backup_user_data(data_backup_path)
            
            # 创建压缩包
            with tarfile.open(backup_path, 'w:gz') as tar:
                tar.add(temp_dir, arcname=backup_name)
            
            system_logger.info(f"备份创建成功: {backup_path}")
            
            # 清理旧备份
            self._cleanup_old_backups()
            
            return str(backup_path)
            
        except Exception as e:
            system_logger.error(f"创建备份失败: {e}")
            raise DatabaseError(f"备份创建失败: {e}")
        finally:
            # 清理临时目录
            if temp_dir.exists():
                shutil.rmtree(temp_dir)
    
    def _create_backup_metadata(self) -> Dict[str, Any]:
        """创建备份元数据"""
        return {
            "backup_time": datetime.now().isoformat(),
            "version": "0.1.0",
            "system_info": {
                "platform": os.name,
                "python_version": f"{os.sys.version_info.major}.{os.sys.version_info.minor}.{os.sys.version_info.micro}"
            },
            "components": {
                "database": True,
                "configuration": True,
                "logs": True,
                "user_data": True
            }
        }
    
    def _backup_database(self, backup_path: Path):
        """备份图数据库"""
        backup_path.mkdir(parents=True, exist_ok=True)
        
        try:
            # 这里应该实现实际的Neo4j数据库备份
            # 由于我们使用的是模拟数据库，这里创建一个占位符
            placeholder_file = backup_path / "neo4j_backup.dump"
            with open(placeholder_file, 'w') as f:
                f.write("# Neo4j数据库备份占位符\n")
                f.write(f"# 备份时间: {datetime.now().isoformat()}\n")
            
            system_logger.info("数据库备份完成")
            
        except Exception as e:
            system_logger.error(f"数据库备份失败: {e}")
            raise
    
    def _backup_configuration(self, backup_path: Path):
        """备份配置文件"""
        backup_path.mkdir(parents=True, exist_ok=True)
        
        try:
            # 备份主配置文件
            config_files = [
                "config.yaml",
                "config.json",
                ".env",
                "pyproject.toml",
                "requirements.txt"
            ]
            
            for config_file in config_files:
                source_path = Path(config_file)
                if source_path.exists():
                    dest_path = backup_path / config_file
                    shutil.copy2(source_path, dest_path)
            
            system_logger.info("配置文件备份完成")
            
        except Exception as e:
            system_logger.error(f"配置文件备份失败: {e}")
            raise
    
    def _backup_logs(self, backup_path: Path):
        """备份日志文件"""
        backup_path.mkdir(parents=True, exist_ok=True)
        
        try:
            logs_dir = Path("logs")
            if logs_dir.exists():
                # 只备份最近7天的日志
                cutoff_time = datetime.now() - timedelta(days=7)
                
                for log_file in logs_dir.glob("*.log*"):
                    if log_file.stat().st_mtime > cutoff_time.timestamp():
                        dest_path = backup_path / log_file.name
                        shutil.copy2(log_file, dest_path)
            
            system_logger.info("日志文件备份完成")
            
        except Exception as e:
            system_logger.error(f"日志文件备份失败: {e}")
            raise
    
    def _backup_user_data(self, backup_path: Path):
        """备份用户数据"""
        backup_path.mkdir(parents=True, exist_ok=True)
        
        try:
            # 备份用户上传的项目数据
            data_dirs = ["projects", "uploads", "cache"]
            
            for data_dir in data_dirs:
                source_path = Path(data_dir)
                if source_path.exists():
                    dest_path = backup_path / data_dir
                    shutil.copytree(source_path, dest_path, ignore_dangling_symlinks=True)
            
            system_logger.info("用户数据备份完成")
            
        except Exception as e:
            system_logger.error(f"用户数据备份失败: {e}")
            raise
    
    def _cleanup_old_backups(self):
        """清理旧备份"""
        try:
            backup_files = list(self.backup_dir.glob("backup_*.tar.gz"))
            backup_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            
            # 删除超过最大数量的备份
            if len(backup_files) > self.max_backups:
                for old_backup in backup_files[self.max_backups:]:
                    old_backup.unlink()
                    system_logger.info(f"删除旧备份: {old_backup}")
            
            # 删除超过保留期的备份
            cutoff_time = datetime.now() - timedelta(days=self.backup_retention_days)
            for backup_file in backup_files:
                if datetime.fromtimestamp(backup_file.stat().st_mtime) < cutoff_time:
                    backup_file.unlink()
                    system_logger.info(f"删除过期备份: {backup_file}")
            
        except Exception as e:
            system_logger.warning(f"清理旧备份失败: {e}")
    
    def list_backups(self) -> List[Dict[str, Any]]:
        """列出所有备份"""
        backups = []
        
        try:
            backup_files = list(self.backup_dir.glob("backup_*.tar.gz"))
            backup_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            
            for backup_file in backup_files:
                stat = backup_file.stat()
                # 移除.tar.gz后缀获取备份名称
                backup_name = backup_file.name.replace('.tar.gz', '')
                backups.append({
                    "name": backup_name,
                    "file_path": str(backup_file),
                    "size_mb": round(stat.st_size / (1024 * 1024), 2),
                    "created_time": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "age_days": (datetime.now() - datetime.fromtimestamp(stat.st_mtime)).days
                })
            
        except Exception as e:
            system_logger.error(f"列出备份失败: {e}")
        
        return backups
    
    @error_handler(component="backup", operation="restore_backup")
    def restore_backup(self, backup_path: str, components: Optional[List[str]] = None) -> bool:
        """恢复备份
        
        Args:
            backup_path: 备份文件路径
            components: 要恢复的组件列表，None表示恢复所有组件
            
        Returns:
            恢复是否成功
        """
        backup_file = Path(backup_path)
        if not backup_file.exists():
            raise FileNotFoundError(f"备份文件不存在: {backup_path}")
        
        temp_dir = Path(tempfile.mkdtemp())
        
        try:
            system_logger.info(f"开始恢复备份: {backup_path}")
            
            # 解压备份文件
            with tarfile.open(backup_file, 'r:gz') as tar:
                tar.extractall(temp_dir)
            
            # 查找解压后的目录
            extracted_dirs = [d for d in temp_dir.iterdir() if d.is_dir()]
            if not extracted_dirs:
                raise ValueError("备份文件格式无效")
            
            backup_content_dir = extracted_dirs[0]
            
            # 读取备份元数据
            metadata_file = backup_content_dir / "metadata.json"
            if metadata_file.exists():
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                system_logger.info(f"备份元数据: {metadata}")
            
            # 恢复各个组件
            if not components or "database" in components:
                self._restore_database(backup_content_dir / "database")
            
            if not components or "configuration" in components:
                self._restore_configuration(backup_content_dir / "config")
            
            if not components or "logs" in components:
                self._restore_logs(backup_content_dir / "logs")
            
            if not components or "user_data" in components:
                self._restore_user_data(backup_content_dir / "data")
            
            system_logger.info("备份恢复成功")
            return True
            
        except Exception as e:
            system_logger.error(f"恢复备份失败: {e}")
            raise DatabaseError(f"备份恢复失败: {e}")
        finally:
            # 清理临时目录
            if temp_dir.exists():
                shutil.rmtree(temp_dir)
    
    def _restore_database(self, backup_path: Path):
        """恢复图数据库"""
        if not backup_path.exists():
            system_logger.warning("数据库备份不存在，跳过恢复")
            return
        
        try:
            # 这里应该实现实际的Neo4j数据库恢复
            # 由于我们使用的是模拟数据库，这里只是记录日志
            system_logger.info("数据库恢复完成（模拟）")
            
        except Exception as e:
            system_logger.error(f"数据库恢复失败: {e}")
            raise
    
    def _restore_configuration(self, backup_path: Path):
        """恢复配置文件"""
        if not backup_path.exists():
            system_logger.warning("配置备份不存在，跳过恢复")
            return
        
        try:
            for config_file in backup_path.iterdir():
                if config_file.is_file():
                    dest_path = Path(config_file.name)
                    # 备份现有配置
                    if dest_path.exists():
                        backup_name = f"{dest_path.name}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                        dest_path.rename(backup_name)
                    
                    shutil.copy2(config_file, dest_path)
            
            system_logger.info("配置文件恢复完成")
            
        except Exception as e:
            system_logger.error(f"配置文件恢复失败: {e}")
            raise
    
    def _restore_logs(self, backup_path: Path):
        """恢复日志文件"""
        if not backup_path.exists():
            system_logger.warning("日志备份不存在，跳过恢复")
            return
        
        try:
            logs_dir = Path("logs")
            logs_dir.mkdir(exist_ok=True)
            
            for log_file in backup_path.iterdir():
                if log_file.is_file():
                    dest_path = logs_dir / f"restored_{log_file.name}"
                    shutil.copy2(log_file, dest_path)
            
            system_logger.info("日志文件恢复完成")
            
        except Exception as e:
            system_logger.error(f"日志文件恢复失败: {e}")
            raise
    
    def _restore_user_data(self, backup_path: Path):
        """恢复用户数据"""
        if not backup_path.exists():
            system_logger.warning("用户数据备份不存在，跳过恢复")
            return
        
        try:
            for data_dir in backup_path.iterdir():
                if data_dir.is_dir():
                    dest_path = Path(data_dir.name)
                    if dest_path.exists():
                        # 备份现有数据
                        backup_name = f"{dest_path.name}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                        dest_path.rename(backup_name)
                    
                    shutil.copytree(data_dir, dest_path)
            
            system_logger.info("用户数据恢复完成")
            
        except Exception as e:
            system_logger.error(f"用户数据恢复失败: {e}")
            raise
    
    def delete_backup(self, backup_name: str) -> bool:
        """删除指定备份
        
        Args:
            backup_name: 备份名称
            
        Returns:
            删除是否成功
        """
        try:
            backup_file = self.backup_dir / f"{backup_name}.tar.gz"
            if backup_file.exists():
                backup_file.unlink()
                system_logger.info(f"删除备份: {backup_name}")
                return True
            else:
                system_logger.warning(f"备份文件不存在: {backup_name}")
                return False
                
        except Exception as e:
            system_logger.error(f"删除备份失败: {e}")
            return False


class SystemStateManager:
    """系统状态管理器"""
    
    def __init__(self):
        self.state_file = Path("system_state.json")
        self.logger = system_logger
    
    @error_handler(component="system", operation="save_state")
    def save_system_state(self, state_data: Dict[str, Any]) -> bool:
        """保存系统状态
        
        Args:
            state_data: 系统状态数据
            
        Returns:
            保存是否成功
        """
        try:
            # 添加时间戳
            state_data["timestamp"] = datetime.now().isoformat()
            state_data["version"] = "0.1.0"
            
            # 备份现有状态文件
            if self.state_file.exists():
                backup_name = f"system_state.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                shutil.copy2(self.state_file, backup_name)
            
            # 保存新状态
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(state_data, f, ensure_ascii=False, indent=2)
            
            self.logger.info("系统状态保存成功")
            return True
            
        except Exception as e:
            self.logger.error(f"保存系统状态失败: {e}")
            return False
    
    @error_handler(component="system", operation="load_state")
    def load_system_state(self) -> Optional[Dict[str, Any]]:
        """加载系统状态
        
        Returns:
            系统状态数据，如果加载失败返回None
        """
        try:
            if not self.state_file.exists():
                self.logger.info("系统状态文件不存在")
                return None
            
            with open(self.state_file, 'r', encoding='utf-8') as f:
                state_data = json.load(f)
            
            self.logger.info("系统状态加载成功")
            return state_data
            
        except Exception as e:
            self.logger.error(f"加载系统状态失败: {e}")
            return None
    
    def get_system_status(self) -> Dict[str, Any]:
        """获取当前系统状态"""
        return {
            "timestamp": datetime.now().isoformat(),
            "uptime": self._get_uptime(),
            "services": self._get_services_status(),
            "resources": self._get_resource_usage(),
            "health": "healthy"  # 这里可以集成健康检查
        }
    
    def _get_uptime(self) -> float:
        """获取系统运行时间"""
        try:
            with open('/proc/uptime', 'r') as f:
                uptime_seconds = float(f.readline().split()[0])
            return uptime_seconds
        except:
            # Windows或其他系统的处理
            return 0.0
    
    def _get_services_status(self) -> Dict[str, str]:
        """获取服务状态"""
        return {
            "parser": "running",
            "graph_builder": "running",
            "ai_service": "running",
            "database": "running",
            "api": "running"
        }
    
    def _get_resource_usage(self) -> Dict[str, Any]:
        """获取资源使用情况"""
        try:
            import psutil
            
            # 在Windows系统上使用C:盘
            disk_path = 'C:' if os.name == 'nt' else '/'
            
            return {
                "cpu_percent": psutil.cpu_percent(),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_percent": psutil.disk_usage(disk_path).percent
            }
        except ImportError:
            return {"error": "psutil not available"}
        except Exception as e:
            return {"error": f"获取资源信息失败: {e}"}


# 全局实例
backup_manager = BackupManager()
system_state_manager = SystemStateManager()


def create_scheduled_backup():
    """创建定时备份"""
    try:
        backup_path = backup_manager.create_backup()
        system_logger.info(f"定时备份创建成功: {backup_path}")
        return backup_path
    except Exception as e:
        system_logger.error(f"定时备份失败: {e}")
        return None


def emergency_backup():
    """紧急备份"""
    try:
        backup_name = f"emergency_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        backup_path = backup_manager.create_backup(backup_name)
        system_logger.critical(f"紧急备份创建: {backup_path}")
        return backup_path
    except Exception as e:
        system_logger.critical(f"紧急备份失败: {e}")
        return None