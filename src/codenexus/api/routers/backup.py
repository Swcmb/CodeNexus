"""
备份和恢复API路由

提供数据备份、恢复和系统状态管理的API端点。
"""

from datetime import datetime
from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel

from ...utils.backup_recovery import backup_manager, system_state_manager
from ...utils.logger import system_logger

router = APIRouter()


class BackupRequest(BaseModel):
    """备份请求模型"""
    backup_name: Optional[str] = None


class RestoreRequest(BaseModel):
    """恢复请求模型"""
    backup_path: str
    components: Optional[List[str]] = None


class BackupResponse(BaseModel):
    """备份响应模型"""
    success: bool
    backup_path: Optional[str] = None
    message: str


class BackupListResponse(BaseModel):
    """备份列表响应模型"""
    backups: List[Dict]
    total_count: int


@router.post("/create", response_model=BackupResponse)
async def create_backup(
    request: BackupRequest,
    background_tasks: BackgroundTasks
):
    """
    创建系统备份
    
    创建包含数据库、配置、日志和用户数据的完整系统备份。
    """
    try:
        # 在后台任务中执行备份，避免阻塞请求
        def backup_task():
            try:
                backup_path = backup_manager.create_backup(request.backup_name)
                system_logger.info(f"API触发的备份创建成功: {backup_path}")
            except Exception as e:
                system_logger.error(f"API触发的备份创建失败: {e}")
        
        background_tasks.add_task(backup_task)
        
        return BackupResponse(
            success=True,
            message="备份任务已启动，将在后台执行"
        )
        
    except Exception as e:
        system_logger.error(f"创建备份API失败: {e}")
        raise HTTPException(status_code=500, detail=f"创建备份失败: {str(e)}")


@router.get("/list", response_model=BackupListResponse)
async def list_backups():
    """
    列出所有备份
    
    返回系统中所有可用备份的列表，包括备份时间、大小等信息。
    """
    try:
        backups = backup_manager.list_backups()
        
        return BackupListResponse(
            backups=backups,
            total_count=len(backups)
        )
        
    except Exception as e:
        system_logger.error(f"列出备份API失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取备份列表失败: {str(e)}")


@router.post("/restore", response_model=BackupResponse)
async def restore_backup(
    request: RestoreRequest,
    background_tasks: BackgroundTasks
):
    """
    恢复系统备份
    
    从指定的备份文件恢复系统状态。可以选择性地恢复特定组件。
    """
    try:
        # 在后台任务中执行恢复，避免阻塞请求
        def restore_task():
            try:
                success = backup_manager.restore_backup(
                    request.backup_path,
                    request.components
                )
                if success:
                    system_logger.info(f"API触发的备份恢复成功: {request.backup_path}")
                else:
                    system_logger.error(f"API触发的备份恢复失败: {request.backup_path}")
            except Exception as e:
                system_logger.error(f"API触发的备份恢复异常: {e}")
        
        background_tasks.add_task(restore_task)
        
        return BackupResponse(
            success=True,
            message="恢复任务已启动，将在后台执行"
        )
        
    except Exception as e:
        system_logger.error(f"恢复备份API失败: {e}")
        raise HTTPException(status_code=500, detail=f"恢复备份失败: {str(e)}")


@router.delete("/{backup_name}")
async def delete_backup(backup_name: str):
    """
    删除指定备份
    
    Args:
        backup_name: 要删除的备份名称
    """
    try:
        success = backup_manager.delete_backup(backup_name)
        
        if success:
            return {"success": True, "message": f"备份 {backup_name} 删除成功"}
        else:
            raise HTTPException(status_code=404, detail=f"备份 {backup_name} 不存在")
            
    except HTTPException:
        raise
    except Exception as e:
        system_logger.error(f"删除备份API失败: {e}")
        raise HTTPException(status_code=500, detail=f"删除备份失败: {str(e)}")


@router.post("/emergency")
async def emergency_backup(background_tasks: BackgroundTasks):
    """
    创建紧急备份
    
    在系统出现问题时创建紧急备份，用于故障恢复。
    """
    try:
        from ...utils.backup_recovery import emergency_backup
        
        def emergency_task():
            backup_path = emergency_backup()
            if backup_path:
                system_logger.critical(f"API触发的紧急备份创建成功: {backup_path}")
            else:
                system_logger.critical("API触发的紧急备份创建失败")
        
        background_tasks.add_task(emergency_task)
        
        return {
            "success": True,
            "message": "紧急备份任务已启动",
            "priority": "critical"
        }
        
    except Exception as e:
        system_logger.critical(f"紧急备份API失败: {e}")
        raise HTTPException(status_code=500, detail=f"创建紧急备份失败: {str(e)}")


@router.get("/system-state")
async def get_system_state():
    """
    获取当前系统状态
    
    返回系统的当前运行状态，包括服务状态、资源使用情况等。
    """
    try:
        current_state = system_state_manager.get_system_status()
        saved_state = system_state_manager.load_system_state()
        
        return {
            "current_state": current_state,
            "saved_state": saved_state,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        system_logger.error(f"获取系统状态API失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取系统状态失败: {str(e)}")


@router.post("/system-state/save")
async def save_system_state():
    """
    保存当前系统状态
    
    将当前的系统状态保存到文件中，用于后续的状态恢复。
    """
    try:
        current_state = system_state_manager.get_system_status()
        success = system_state_manager.save_system_state(current_state)
        
        if success:
            return {
                "success": True,
                "message": "系统状态保存成功",
                "timestamp": current_state["timestamp"]
            }
        else:
            raise HTTPException(status_code=500, detail="系统状态保存失败")
            
    except HTTPException:
        raise
    except Exception as e:
        system_logger.error(f"保存系统状态API失败: {e}")
        raise HTTPException(status_code=500, detail=f"保存系统状态失败: {str(e)}")


@router.get("/status")
async def get_backup_status():
    """
    获取备份系统状态
    
    返回备份系统的配置和运行状态信息。
    """
    try:
        backups = backup_manager.list_backups()
        
        return {
            "backup_directory": str(backup_manager.backup_dir),
            "max_backups": backup_manager.max_backups,
            "retention_days": backup_manager.backup_retention_days,
            "total_backups": len(backups),
            "latest_backup": backups[0] if backups else None,
            "total_size_mb": sum(backup["size_mb"] for backup in backups),
            "status": "healthy"
        }
        
    except Exception as e:
        system_logger.error(f"获取备份状态API失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取备份状态失败: {str(e)}")