"""
用户服务

提供用户相关的业务逻辑处理。
"""

from typing import Optional, List, Dict, Any
from datetime import datetime

from models.user import User, UserRepository, UserFactory
from utils.auth import AuthManager
from utils.database import DatabaseManager


class UserService:
    """用户服务类"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.user_repository = UserRepository()
        self.auth_manager = AuthManager()
    
    def register_user(self, username: str, email: str, password: str, 
                     full_name: Optional[str] = None, phone: Optional[str] = None) -> Dict[str, Any]:
        """
        用户注册
        
        Args:
            username: 用户名
            email: 邮箱
            password: 密码
            full_name: 全名
            phone: 电话
            
        Returns:
            注册结果
        """
        # 验证输入
        if not username or not email or not password:
            return {
                'success': False,
                'error': '用户名、邮箱和密码不能为空'
            }
        
        if len(password) < 6:
            return {
                'success': False,
                'error': '密码长度至少6位'
            }
        
        # 检查用户名是否已存在
        existing_user = self.user_repository.find_by_username(username)
        if existing_user:
            return {
                'success': False,
                'error': '用户名已存在'
            }
        
        # 检查邮箱是否已存在
        existing_email = self.user_repository.find_by_email(email)
        if existing_email:
            return {
                'success': False,
                'error': '邮箱已被注册'
            }
        
        try:
            # 创建新用户
            user = UserFactory.create_user(
                username=username,
                email=email,
                password=password,
                full_name=full_name,
                phone=phone
            )
            
            # 保存用户
            saved_user = self.user_repository.save(user)
            
            # 生成JWT令牌
            token = self.auth_manager.generate_token(saved_user.id)
            
            return {
                'success': True,
                'user': saved_user.to_dict(),
                'token': token
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'注册失败: {str(e)}'
            }
    
    def authenticate_user(self, username: str, password: str) -> Dict[str, Any]:
        """
        用户认证
        
        Args:
            username: 用户名
            password: 密码
            
        Returns:
            认证结果
        """
        if not username or not password:
            return {
                'success': False,
                'error': '用户名和密码不能为空'
            }
        
        # 查找用户
        user = self.user_repository.find_by_username(username)
        if not user:
            return {
                'success': False,
                'error': '用户名或密码错误'
            }
        
        # 验证密码
        if not user.verify_password(password):
            return {
                'success': False,
                'error': '用户名或密码错误'
            }
        
        # 检查用户是否激活
        if not user.is_active:
            return {
                'success': False,
                'error': '用户账户已被禁用'
            }
        
        try:
            # 更新最后登录时间
            user.update_last_login()
            self.user_repository.save(user)
            
            # 生成JWT令牌
            token = self.auth_manager.generate_token(user.id)
            
            return {
                'success': True,
                'user': user.to_dict(),
                'token': token
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'登录失败: {str(e)}'
            }
    
    def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        根据ID获取用户信息
        
        Args:
            user_id: 用户ID
            
        Returns:
            用户信息或None
        """
        user = self.user_repository.find_by_id(user_id)
        if user:
            return user.to_dict()
        return None
    
    def update_user(self, user_id: int, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        更新用户信息
        
        Args:
            user_id: 用户ID
            update_data: 更新数据
            
        Returns:
            更新结果
        """
        user = self.user_repository.find_by_id(user_id)
        if not user:
            return {
                'success': False,
                'error': '用户不存在'
            }
        
        try:
            # 更新允许的字段
            updatable_fields = ['full_name', 'phone', 'email']
            
            for field, value in update_data.items():
                if field in updatable_fields and hasattr(user, field):
                    setattr(user, field, value)
            
            # 如果更新邮箱，检查是否重复
            if 'email' in update_data:
                existing_user = self.user_repository.find_by_email(update_data['email'])
                if existing_user and existing_user.id != user_id:
                    return {
                        'success': False,
                        'error': '邮箱已被其他用户使用'
                    }
            
            # 保存更新
            updated_user = self.user_repository.save(user)
            
            return {
                'success': True,
                'user': updated_user.to_dict()
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'更新失败: {str(e)}'
            }
    
    def change_password(self, user_id: int, old_password: str, new_password: str) -> Dict[str, Any]:
        """
        修改密码
        
        Args:
            user_id: 用户ID
            old_password: 旧密码
            new_password: 新密码
            
        Returns:
            修改结果
        """
        user = self.user_repository.find_by_id(user_id)
        if not user:
            return {
                'success': False,
                'error': '用户不存在'
            }
        
        # 验证旧密码
        if not user.verify_password(old_password):
            return {
                'success': False,
                'error': '旧密码错误'
            }
        
        # 验证新密码
        if len(new_password) < 6:
            return {
                'success': False,
                'error': '新密码长度至少6位'
            }
        
        try:
            # 更新密码
            user.password_hash = User.hash_password(new_password)
            self.user_repository.save(user)
            
            return {
                'success': True,
                'message': '密码修改成功'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'密码修改失败: {str(e)}'
            }
    
    def deactivate_user(self, user_id: int) -> Dict[str, Any]:
        """
        禁用用户
        
        Args:
            user_id: 用户ID
            
        Returns:
            操作结果
        """
        user = self.user_repository.find_by_id(user_id)
        if not user:
            return {
                'success': False,
                'error': '用户不存在'
            }
        
        try:
            user.is_active = False
            self.user_repository.save(user)
            
            return {
                'success': True,
                'message': '用户已被禁用'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'操作失败: {str(e)}'
            }
    
    def activate_user(self, user_id: int) -> Dict[str, Any]:
        """
        激活用户
        
        Args:
            user_id: 用户ID
            
        Returns:
            操作结果
        """
        user = self.user_repository.find_by_id(user_id)
        if not user:
            return {
                'success': False,
                'error': '用户不存在'
            }
        
        try:
            user.is_active = True
            self.user_repository.save(user)
            
            return {
                'success': True,
                'message': '用户已被激活'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'操作失败: {str(e)}'
            }
    
    def get_all_users(self, page: int = 1, per_page: int = 20) -> Dict[str, Any]:
        """
        获取所有用户列表
        
        Args:
            page: 页码
            per_page: 每页数量
            
        Returns:
            用户列表
        """
        try:
            all_users = self.user_repository.find_all()
            
            # 简单分页
            total = len(all_users)
            start = (page - 1) * per_page
            end = start + per_page
            
            users = all_users[start:end]
            
            return {
                'success': True,
                'users': [user.to_dict() for user in users],
                'total': total,
                'page': page,
                'per_page': per_page
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'获取用户列表失败: {str(e)}'
            }
    
    def search_users(self, keyword: str) -> List[Dict[str, Any]]:
        """
        搜索用户
        
        Args:
            keyword: 搜索关键词
            
        Returns:
            匹配的用户列表
        """
        try:
            all_users = self.user_repository.find_all()
            
            # 简单的关键词搜索
            matched_users = []
            keyword_lower = keyword.lower()
            
            for user in all_users:
                if (keyword_lower in user.username.lower() or 
                    keyword_lower in user.email.lower() or
                    (user.full_name and keyword_lower in user.full_name.lower())):
                    matched_users.append(user.to_dict())
            
            return matched_users
            
        except Exception as e:
            return []