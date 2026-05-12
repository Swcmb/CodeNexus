"""
认证工具

提供JWT令牌生成、验证和用户认证相关功能。
"""

import jwt
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any


class AuthManager:
    """认证管理器"""
    
    def __init__(self, secret_key: str = None, token_expiry_hours: int = 24):
        self.secret_key = secret_key or secrets.token_urlsafe(32)
        self.token_expiry_hours = token_expiry_hours
        self.algorithm = 'HS256'
    
    def generate_token(self, user_id: int, additional_claims: Optional[Dict[str, Any]] = None) -> str:
        """
        生成JWT令牌
        
        Args:
            user_id: 用户ID
            additional_claims: 额外的声明信息
            
        Returns:
            JWT令牌字符串
        """
        now = datetime.utcnow()
        expiry = now + timedelta(hours=self.token_expiry_hours)
        
        payload = {
            'user_id': user_id,
            'iat': now,
            'exp': expiry,
            'type': 'access'
        }
        
        if additional_claims:
            payload.update(additional_claims)
        
        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        return token
    
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        验证JWT令牌
        
        Args:
            token: JWT令牌字符串
            
        Returns:
            令牌载荷或None（如果验证失败）
        """
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            
            # 检查令牌类型
            if payload.get('type') != 'access':
                return None
            
            # 检查是否过期
            if datetime.utcnow() > datetime.fromtimestamp(payload['exp']):
                return None
            
            return payload
            
        except jwt.InvalidTokenError:
            return None
    
    def refresh_token(self, token: str) -> Optional[str]:
        """
        刷新JWT令牌
        
        Args:
            token: 原始JWT令牌
            
        Returns:
            新的JWT令牌或None（如果刷新失败）
        """
        payload = self.verify_token(token)
        if not payload:
            return None
        
        # 生成新令牌（保留用户ID和其他声明）
        user_id = payload['user_id']
        additional_claims = {k: v for k, v in payload.items() 
                           if k not in ['iat', 'exp', 'type']}
        
        return self.generate_token(user_id, additional_claims)
    
    def generate_refresh_token(self, user_id: int, days: int = 30) -> str:
        """
        生成刷新令牌
        
        Args:
            user_id: 用户ID
            days: 有效天数
            
        Returns:
            刷新令牌字符串
        """
        now = datetime.utcnow()
        expiry = now + timedelta(days=days)
        
        payload = {
            'user_id': user_id,
            'iat': now,
            'exp': expiry,
            'type': 'refresh'
        }
        
        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        return token
    
    def verify_refresh_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        验证刷新令牌
        
        Args:
            token: 刷新令牌字符串
            
        Returns:
            令牌载荷或None（如果验证失败）
        """
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            
            # 检查令牌类型
            if payload.get('type') != 'refresh':
                return None
            
            return payload
            
        except jwt.InvalidTokenError:
            return None
    
    @staticmethod
    def hash_password(password: str, salt: Optional[str] = None) -> tuple[str, str]:
        """
        密码哈希
        
        Args:
            password: 明文密码
            salt: 盐值（可选）
            
        Returns:
            (哈希密码, 盐值)
        """
        if salt is None:
            salt = secrets.token_hex(16)
        
        # 使用PBKDF2进行密码哈希
        password_hash = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt.encode('utf-8'),
            100000  # 迭代次数
        )
        
        return password_hash.hex(), salt
    
    @staticmethod
    def verify_password(password: str, password_hash: str, salt: str) -> bool:
        """
        验证密码
        
        Args:
            password: 明文密码
            password_hash: 存储的密码哈希
            salt: 盐值
            
        Returns:
            是否匹配
        """
        computed_hash, _ = AuthManager.hash_password(password, salt)
        return computed_hash == password_hash
    
    def generate_password_reset_token(self, user_id: int, hours: int = 1) -> str:
        """
        生成密码重置令牌
        
        Args:
            user_id: 用户ID
            hours: 有效小时数
            
        Returns:
            重置令牌字符串
        """
        now = datetime.utcnow()
        expiry = now + timedelta(hours=hours)
        
        payload = {
            'user_id': user_id,
            'iat': now,
            'exp': expiry,
            'type': 'password_reset',
            'purpose': 'reset_password'
        }
        
        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        return token
    
    def verify_password_reset_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        验证密码重置令牌
        
        Args:
            token: 重置令牌字符串
            
        Returns:
            令牌载荷或None（如果验证失败）
        """
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            
            # 检查令牌类型和用途
            if (payload.get('type') != 'password_reset' or 
                payload.get('purpose') != 'reset_password'):
                return None
            
            return payload
            
        except jwt.InvalidTokenError:
            return None
    
    def generate_email_verification_token(self, user_id: int, email: str, hours: int = 24) -> str:
        """
        生成邮箱验证令牌
        
        Args:
            user_id: 用户ID
            email: 邮箱地址
            hours: 有效小时数
            
        Returns:
            验证令牌字符串
        """
        now = datetime.utcnow()
        expiry = now + timedelta(hours=hours)
        
        payload = {
            'user_id': user_id,
            'email': email,
            'iat': now,
            'exp': expiry,
            'type': 'email_verification',
            'purpose': 'verify_email'
        }
        
        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        return token
    
    def verify_email_verification_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        验证邮箱验证令牌
        
        Args:
            token: 验证令牌字符串
            
        Returns:
            令牌载荷或None（如果验证失败）
        """
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            
            # 检查令牌类型和用途
            if (payload.get('type') != 'email_verification' or 
                payload.get('purpose') != 'verify_email'):
                return None
            
            return payload
            
        except jwt.InvalidTokenError:
            return None
    
    def get_token_info(self, token: str) -> Optional[Dict[str, Any]]:
        """
        获取令牌信息（不验证过期时间）
        
        Args:
            token: JWT令牌字符串
            
        Returns:
            令牌信息或None
        """
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm], options={'verify_exp': False})
            
            return {
                'user_id': payload.get('user_id'),
                'type': payload.get('type'),
                'issued_at': datetime.fromtimestamp(payload['iat']) if 'iat' in payload else None,
                'expires_at': datetime.fromtimestamp(payload['exp']) if 'exp' in payload else None,
                'is_expired': datetime.utcnow() > datetime.fromtimestamp(payload['exp']) if 'exp' in payload else True
            }
            
        except jwt.InvalidTokenError:
            return None
    
    def is_token_expired(self, token: str) -> bool:
        """
        检查令牌是否过期
        
        Args:
            token: JWT令牌字符串
            
        Returns:
            是否过期
        """
        info = self.get_token_info(token)
        return info.get('is_expired', True) if info else True
    
    def revoke_token(self, token: str) -> bool:
        """
        撤销令牌（简化实现，实际应用中需要使用黑名单）
        
        Args:
            token: JWT令牌字符串
            
        Returns:
            是否成功撤销
        """
        # 简化实现：将令牌加入黑名单
        # 实际应用中应该使用Redis或数据库存储黑名单
        return True


class PermissionManager:
    """权限管理器"""
    
    def __init__(self):
        self.permissions = {
            'admin': [
                'user:create', 'user:read', 'user:update', 'user:delete',
                'product:create', 'product:read', 'product:update', 'product:delete',
                'order:create', 'order:read', 'order:update', 'order:delete',
                'system:manage'
            ],
            'user': [
                'user:read_own', 'user:update_own',
                'product:read', 'order:create', 'order:read_own', 'order:update_own'
            ],
            'guest': [
                'product:read'
            ]
        }
    
    def has_permission(self, user_role: str, permission: str, user_id: Optional[int] = None, 
                      resource_user_id: Optional[int] = None) -> bool:
        """
        检查用户是否有指定权限
        
        Args:
            user_role: 用户角色
            permission: 权限字符串
            user_id: 用户ID
            resource_user_id: 资源所属用户ID
            
        Returns:
            是否有权限
        """
        role_permissions = self.permissions.get(user_role, [])
        
        # 检查直接权限
        if permission in role_permissions:
            return True
        
        # 检查自有资源权限
        if user_id and resource_user_id and user_id == resource_user_id:
            own_permissions = [p for p in role_permissions if p.endswith('_own')]
            required_own_permission = permission.replace(':read', ':read_own').replace(':update', ':update_own')
            if required_own_permission in own_permissions:
                return True
        
        return False
    
    def get_user_permissions(self, user_role: str) -> list[str]:
        """
        获取用户角色的所有权限
        
        Args:
            user_role: 用户角色
            
        Returns:
            权限列表
        """
        return self.permissions.get(user_role, [])


# 全局认证管理器实例
auth_manager = AuthManager()
permission_manager = PermissionManager()