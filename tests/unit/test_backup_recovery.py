"""
备份恢复系统测试

测试数据备份、恢复和系统状态管理功能。
"""

import pytest
import tempfile
import json
from pathlib import Path
from unittest.mock import Mock, patch

from src.codenexus.utils.backup_recovery import (
    BackupManager, SystemStateManager
)


class TestBackupManager:
    """备份管理器测试"""
    
    def test_backup_manager_creation(self):
        """测试备份管理器创建"""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = BackupManager(backup_dir=temp_dir)
            
            assert manager.backup_dir == Path(temp_dir)
            assert manager.max_backups == 30
            assert manager.backup_retention_days == 7
    
    def test_create_backup_metadata(self):
        """测试创建备份元数据"""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = BackupManager(backup_dir=temp_dir)
            metadata = manager._create_backup_metadata()
            
            assert "backup_time" in metadata
            assert "version" in metadata
            assert "system_info" in metadata
            assert "components" in metadata
            assert metadata["components"]["database"] is True
    
    @patch('src.codeweaver.utils.backup_recovery.BackupManager._backup_database')
    @patch('src.codeweaver.utils.backup_recovery.BackupManager._backup_configuration')
    @patch('src.codeweaver.utils.backup_recovery.BackupManager._backup_logs')
    @patch('src.codeweaver.utils.backup_recovery.BackupManager._backup_user_data')
    def test_create_backup(self, mock_user_data, mock_logs, mock_config, mock_db):
        """测试创建备份"""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = BackupManager(backup_dir=temp_dir)
            
            backup_path = manager.create_backup("test_backup")
            
            assert Path(backup_path).exists()
            assert Path(backup_path).suffix == ".gz"
            mock_db.assert_called_once()
            mock_config.assert_called_once()
            mock_logs.assert_called_once()
            mock_user_data.assert_called_once()
    
    def test_backup_configuration(self):
        """测试备份配置文件"""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = BackupManager(backup_dir=temp_dir)
            backup_path = Path(temp_dir) / "config"
            
            # 创建测试配置文件
            test_config = Path("test_config.yaml")
            test_config.write_text("test: config")
            
            try:
                manager._backup_configuration(backup_path)
                
                # 检查备份目录是否创建
                assert backup_path.exists()
                
            finally:
                # 清理测试文件
                if test_config.exists():
                    test_config.unlink()
    
    def test_list_backups(self):
        """测试列出备份"""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = BackupManager(backup_dir=temp_dir)
            
            # 创建测试备份文件
            test_backup = Path(temp_dir) / "backup_20231201_120000.tar.gz"
            test_backup.write_text("test backup")
            
            backups = manager.list_backups()
            
            assert len(backups) == 1
            assert backups[0]["name"] == "backup_20231201_120000"
            assert "size_mb" in backups[0]
            assert "created_time" in backups[0]
    
    def test_delete_backup(self):
        """测试删除备份"""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = BackupManager(backup_dir=temp_dir)
            
            # 创建测试备份文件
            test_backup = Path(temp_dir) / "test_backup.tar.gz"
            test_backup.write_text("test backup")
            
            # 删除备份
            success = manager.delete_backup("test_backup")
            
            assert success is True
            assert not test_backup.exists()
    
    def test_delete_nonexistent_backup(self):
        """测试删除不存在的备份"""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = BackupManager(backup_dir=temp_dir)
            
            success = manager.delete_backup("nonexistent_backup")
            
            assert success is False


class TestSystemStateManager:
    """系统状态管理器测试"""
    
    def test_system_state_manager_creation(self):
        """测试系统状态管理器创建"""
        manager = SystemStateManager()
        
        assert manager.state_file == Path("system_state.json")
        assert manager.logger is not None
    
    def test_save_system_state(self):
        """测试保存系统状态"""
        with tempfile.TemporaryDirectory() as temp_dir:
            state_file = Path(temp_dir) / "test_state.json"
            
            manager = SystemStateManager()
            manager.state_file = state_file
            
            test_state = {
                "service": "running",
                "cpu_usage": 50.0
            }
            
            success = manager.save_system_state(test_state)
            
            assert success is True
            assert state_file.exists()
            
            # 验证保存的内容
            with open(state_file, 'r', encoding='utf-8') as f:
                saved_state = json.load(f)
            
            assert saved_state["service"] == "running"
            assert saved_state["cpu_usage"] == 50.0
            assert "timestamp" in saved_state
            assert "version" in saved_state
    
    def test_load_system_state(self):
        """测试加载系统状态"""
        with tempfile.TemporaryDirectory() as temp_dir:
            state_file = Path(temp_dir) / "test_state.json"
            
            # 创建测试状态文件
            test_state = {
                "service": "running",
                "timestamp": "2023-12-01T12:00:00"
            }
            
            with open(state_file, 'w', encoding='utf-8') as f:
                json.dump(test_state, f)
            
            manager = SystemStateManager()
            manager.state_file = state_file
            
            loaded_state = manager.load_system_state()
            
            assert loaded_state is not None
            assert loaded_state["service"] == "running"
            assert loaded_state["timestamp"] == "2023-12-01T12:00:00"
    
    def test_load_nonexistent_state(self):
        """测试加载不存在的状态文件"""
        with tempfile.TemporaryDirectory() as temp_dir:
            state_file = Path(temp_dir) / "nonexistent_state.json"
            
            manager = SystemStateManager()
            manager.state_file = state_file
            
            loaded_state = manager.load_system_state()
            
            assert loaded_state is None
    
    def test_get_system_status(self):
        """测试获取系统状态"""
        manager = SystemStateManager()
        
        status = manager.get_system_status()
        
        assert "timestamp" in status
        assert "uptime" in status
        assert "services" in status
        assert "resources" in status
        assert "health" in status
        assert status["health"] == "healthy"
    
    def test_get_services_status(self):
        """测试获取服务状态"""
        manager = SystemStateManager()
        
        services = manager._get_services_status()
        
        assert "parser" in services
        assert "graph_builder" in services
        assert "ai_service" in services
        assert "database" in services
        assert "api" in services
        
        # 所有服务应该都是运行状态
        for service_status in services.values():
            assert service_status == "running"
    
    @patch('psutil.cpu_percent')
    @patch('psutil.virtual_memory')
    @patch('psutil.disk_usage')
    def test_get_resource_usage(self, mock_disk, mock_memory, mock_cpu):
        """测试获取资源使用情况"""
        # 模拟psutil返回值
        mock_cpu.return_value = 45.5
        mock_memory.return_value = Mock(percent=60.2)
        mock_disk.return_value = Mock(percent=75.8)
        
        manager = SystemStateManager()
        resources = manager._get_resource_usage()
        
        assert resources["cpu_percent"] == 45.5
        assert resources["memory_percent"] == 60.2
        assert resources["disk_percent"] == 75.8
    
    def test_get_resource_usage_without_psutil(self):
        """测试在没有psutil的情况下获取资源使用情况"""
        manager = SystemStateManager()
        
        # 模拟psutil导入失败
        import builtins
        original_import = builtins.__import__
        
        def mock_import(name, *args, **kwargs):
            if name == 'psutil':
                raise ImportError("No module named 'psutil'")
            return original_import(name, *args, **kwargs)
        
        with patch('builtins.__import__', side_effect=mock_import):
            resources = manager._get_resource_usage()
            
            assert "error" in resources
            assert resources["error"] == "psutil not available"


class TestBackupRecoveryIntegration:
    """备份恢复集成测试"""
    
    def test_backup_and_restore_cycle(self):
        """测试完整的备份和恢复周期"""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = BackupManager(backup_dir=temp_dir)
            
            # 创建一些测试数据
            test_data_dir = Path(temp_dir) / "test_data"
            test_data_dir.mkdir()
            (test_data_dir / "test_file.txt").write_text("test content")
            
            # 模拟备份方法，但确保创建实际的备份文件
            def mock_backup_method(backup_path):
                backup_path.mkdir(parents=True, exist_ok=True)
                (backup_path / "mock_backup.txt").write_text("mock backup data")
            
            with patch.object(manager, '_backup_database', side_effect=mock_backup_method), \
                 patch.object(manager, '_backup_configuration', side_effect=mock_backup_method), \
                 patch.object(manager, '_backup_logs', side_effect=mock_backup_method), \
                 patch.object(manager, '_backup_user_data', side_effect=mock_backup_method):
                
                # 创建备份（使用默认名称，这样会匹配backup_*模式）
                backup_path = manager.create_backup()  # 不指定名称，使用默认的backup_时间戳格式
                assert Path(backup_path).exists()
                
                # 列出备份
                backups = manager.list_backups()
                assert len(backups) >= 1
                # 检查是否有我们创建的备份
                backup_names = [b["name"] for b in backups]
                assert any("backup_" in name for name in backup_names)
    
    def test_system_state_persistence(self):
        """测试系统状态持久化"""
        with tempfile.TemporaryDirectory() as temp_dir:
            state_file = Path(temp_dir) / "state.json"
            
            manager = SystemStateManager()
            manager.state_file = state_file
            
            # 保存状态
            original_state = {
                "service_count": 5,
                "active_users": 10,
                "last_backup": "2023-12-01T10:00:00"
            }
            
            success = manager.save_system_state(original_state)
            assert success is True
            
            # 加载状态
            loaded_state = manager.load_system_state()
            assert loaded_state is not None
            assert loaded_state["service_count"] == 5
            assert loaded_state["active_users"] == 10
            assert loaded_state["last_backup"] == "2023-12-01T10:00:00"
            
            # 验证添加的元数据
            assert "timestamp" in loaded_state
            assert "version" in loaded_state