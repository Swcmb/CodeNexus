"""
用户API接口

提供用户相关的HTTP API接口。
"""

from typing import Dict, Any, Optional
from services.user_service import UserService
from utils.auth import AuthManager, PermissionManager
from utils.database import DatabaseManager


class UserAPI:
    """用户API类"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.user_service = UserService(db_manager)
        self.auth_manager = AuthManager()
        self.permission_manager = PermissionManager()
    
    def register(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        用户注册API
        
        Args:
            request_data: 请求数据
            
        Returns:
            API响应
        """
        try:
            result = self.user_service.register_user(
                username=request_data.get('username', ''),
                email=request_data.get('email', ''),
                password=request_data.get('password', ''),
                full_name=request_data.get('full_name'),
                phone=request_data.get('phone')
            )
            
            if result['success']:
                return {
                    'status': 'success',
                    'message': '注册成功',
                    'data': {
                        'user': result['user'],
                        'token': result['token']
                    }
                }
            else:
                return {
                    'status': 'error',
                    'message': result['error'],
                    'code': 'REGISTRATION_FAILED'
                }
                
        except Exception as e:
            return {
                'status': 'error',
                'message': '服务器内部错误',
                'code': 'INTERNAL_ERROR'
            }
    
    def login(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        用户登录API
        
        Args:
            request_data: 请求数据
            
        Returns:
            API响应
        """
        try:
            result = self.user_service.authenticate_user(
                username=request_data.get('username', ''),
                password=request_data.get('password', '')
            )
            
            if result['success']:
                return {
                    'status': 'success',
                    'message': '登录成功',
                    'data': {
                        'user': result['user'],
                        'token': result['token']
                    }
                }
            else:
                return {
                    'status': 'error',
                    'message': result['error'],
                    'code': 'LOGIN_FAILED'
                }
                
        except Exception as e:
            return {
                'status': 'error',
                'message': '服务器内部错误',
                'code': 'INTERNAL_ERROR'
            }
    
    def get_profile(self, token: str) -> Dict[str, Any]:
        """
        获取用户资料API
        
        Args:
            token: JWT令牌
            
        Returns:
            API响应
        """
        try:
            # 验证令牌
            payload = self.auth_manager.verify_token(token)
            if not payload:
                return {
                    'status': 'error',
                    'message': '无效的访问令牌',
                    'code': 'INVALID_TOKEN'
                }
            
            user_id = payload['user_id']
            
            # 检查权限
            if not self.permission_manager.has_permission('user', 'user:read_own', user_id, user_id):
                return {
                    'status': 'error',
                    'message': '权限不足',
                    'code': 'PERMISSION_DENIED'
                }
            
            # 获取用户信息
            user = self.user_service.get_user_by_id(user_id)
            if user:
                return {
                    'status': 'success',
                    'message': '获取用户信息成功',
                    'data': {'user': user}
                }
            else:
                return {
                    'status': 'error',
                    'message': '用户不存在',
                    'code': 'USER_NOT_FOUND'
                }
                
        except Exception as e:
            return {
                'status': 'error',
                'message': '服务器内部错误',
                'code': 'INTERNAL_ERROR'
            }
    
    def update_profile(self, token: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        更新用户资料API
        
        Args:
            token: JWT令牌
            update_data: 更新数据
            
        Returns:
            API响应
        """
        try:
            # 验证令牌
            payload = self.auth_manager.verify_token(token)
            if not payload:
                return {
                    'status': 'error',
                    'message': '无效的访问令牌',
                    'code': 'INVALID_TOKEN'
                }
            
            user_id = payload['user_id']
            
            # 检查权限
            if not self.permission_manager.has_permission('user', 'user:update_own', user_id, user_id):
                return {
                    'status': 'error',
                    'message': '权限不足',
                    'code': 'PERMISSION_DENIED'
                }
            
            # 更新用户信息
            result = self.user_service.update_user(user_id, update_data)
            
            if result['success']:
                return {
                    'status': 'success',
                    'message': '用户信息更新成功',
                    'data': {'user': result['user']}
                }
            else:
                return {
                    'status': 'error',
                    'message': result['error'],
                    'code': 'UPDATE_FAILED'
                }
                
        except Exception as e:
            return {
                'status': 'error',
                'message': '服务器内部错误',
                'code': 'INTERNAL_ERROR'
            }
    
    def change_password(self, token: str, password_data: Dict[str, str]) -> Dict[str, Any]:
        """
        修改密码API
        
        Args:
            token: JWT令牌
            password_data: 密码数据
            
        Returns:
            API响应
        """
        try:
            # 验证令牌
            payload = self.auth_manager.verify_token(token)
            if not payload:
                return {
                    'status': 'error',
                    'message': '无效的访问令牌',
                    'code': 'INVALID_TOKEN'
                }
            
            user_id = payload['user_id']
            
            # 检查权限
            if not self.permission_manager.has_permission('user', 'user:update_own', user_id, user_id):
                return {
                    'status': 'error',
                    'message': '权限不足',
                    'code': 'PERMISSION_DENIED'
                }
            
            # 修改密码
            result = self.user_service.change_password(
                user_id=user_id,
                old_password=password_data.get('old_password', ''),
                new_password=password_data.get('new_password', '')
            )
            
            if result['success']:
                return {
                    'status': 'success',
                    'message': result['message']
                }
            else:
                return {
                    'status': 'error',
                    'message': result['error'],
                    'code': 'PASSWORD_CHANGE_FAILED'
                }
                
        except Exception as e:
            return {
                'status': 'error',
                'message': '服务器内部错误',
                'code': 'INTERNAL_ERROR'
            }
    
    def get_users(self, token: str, page: int = 1, per_page: int = 20) -> Dict[str, Any]:
        """
        获取用户列表API（管理员）
        
        Args:
            token: JWT令牌
            page: 页码
            per_page: 每页数量
            
        Returns:
            API响应
        """
        try:
            # 验证令牌
            payload = self.auth_manager.verify_token(token)
            if not payload:
                return {
                    'status': 'error',
                    'message': '无效的访问令牌',
                    'code': 'INVALID_TOKEN'
                }
            
            user_id = payload['user_id']
            
            # 检查管理员权限
            if not self.permission_manager.has_permission('admin', 'user:read'):
                return {
                    'status': 'error',
                    'message': '权限不足',
                    'code': 'PERMISSION_DENIED'
                }
            
            # 获取用户列表
            result = self.user_service.get_all_users(page, per_page)
            
            if result['success']:
                return {
                    'status': 'success',
                    'message': '获取用户列表成功',
                    'data': {
                        'users': result['users'],
                        'total': result['total'],
                        'page': result['page'],
                        'per_page': result['per_page']
                    }
                }
            else:
                return {
                    'status': 'error',
                    'message': result['error'],
                    'code': 'GET_USERS_FAILED'
                }
                
        except Exception as e:
            return {
                'status': 'error',
                'message': '服务器内部错误',
                'code': 'INTERNAL_ERROR'
            }
    
    def search_users(self, token: str, keyword: str) -> Dict[str, Any]:
        """
        搜索用户API（管理员）
        
        Args:
            token: JWT令牌
            keyword: 搜索关键词
            
        Returns:
            API响应
        """
        try:
            # 验证令牌
            payload = self.auth_manager.verify_token(token)
            if not payload:
                return {
                    'status': 'error',
                    'message': '无效的访问令牌',
                    'code': 'INVALID_TOKEN'
                }
            
            user_id = payload['user_id']
            
            # 检查管理员权限
            if not self.permission_manager.has_permission('admin', 'user:read'):
                return {
                    'status': 'error',
                    'message': '权限不足',
                    'code': 'PERMISSION_DENIED'
                }
            
            # 搜索用户
            users = self.user_service.search_users(keyword)
            
            return {
                'status': 'success',
                'message': '搜索用户成功',
                'data': {'users': users}
            }
                
        except Exception as e:
            return {
                'status': 'error',
                'message': '服务器内部错误',
                'code': 'INTERNAL_ERROR'
            }
    
    def deactivate_user(self, token: str, target_user_id: int) -> Dict[str, Any]:
        """
        禁用用户API（管理员）
        
        Args:
            token: JWT令牌
            target_user_id: 目标用户ID
            
        Returns:
            API响应
        """
        try:
            # 验证令牌
            payload = self.auth_manager.verify_token(token)
            if not payload:
                return {
                    'status': 'error',
                    'message': '无效的访问令牌',
                    'code': 'INVALID_TOKEN'
                }
            
            user_id = payload['user_id']
            
            # 检查管理员权限
            if not self.permission_manager.has_permission('admin', 'user:update'):
                return {
                    'status': 'error',
                    'message': '权限不足',
                    'code': 'PERMISSION_DENIED'
                }
            
            # 禁用用户
            result = self.user_service.deactivate_user(target_user_id)
            
            if result['success']:
                return {
                    'status': 'success',
                    'message': result['message']
                }
            else:
                return {
                    'status': 'error',
                    'message': result['error'],
                    'code': 'DEACTIVATE_FAILED'
                }
                
        except Exception as e:
            return {
                'status': 'error',
                'message': '服务器内部错误',
                'code': 'INTERNAL_ERROR'
            }