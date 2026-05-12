"""
用户模型

定义用户相关的数据结构和基本操作。
"""

from datetime import datetime
from typing import Optional, Dict, Any
from dataclasses import dataclass, field
import hashlib


@dataclass
class User:
    """用户实体类"""
    id: Optional[int] = None
    username: str = ""
    email: str = ""
    password_hash: str = ""
    full_name: Optional[str] = None
    phone: Optional[str] = None
    is_active: bool = True
    is_admin: bool = False
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    last_login: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式，排除敏感信息"""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'full_name': self.full_name,
            'phone': self.phone,
            'is_active': self.is_active,
            'is_admin': self.is_admin,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'last_login': self.last_login.isoformat() if self.last_login else None
        }
    
    @staticmethod
    def hash_password(password: str) -> str:
        """生成密码哈希"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def verify_password(self, password: str) -> bool:
        """验证密码"""
        return self.password_hash == self.hash_password(password)
    
    def update_last_login(self):
        """更新最后登录时间"""
        self.last_login = datetime.now()
        self.updated_at = datetime.now()


class UserFactory:
    """用户工厂类"""
    
    @staticmethod
    def create_user(username: str, email: str, password: str, **kwargs) -> User:
        """创建新用户"""
        password_hash = User.hash_password(password)
        
        return User(
            username=username,
            email=email,
            password_hash=password_hash,
            **kwargs
        )
    
    @staticmethod
    def create_admin_user(username: str, email: str, password: str) -> User:
        """创建管理员用户"""
        return UserFactory.create_user(
            username=username,
            email=email,
            password=password,
            is_admin=True
        )


class UserRepository:
    """用户仓库类 - 模拟数据库操作"""
    
    def __init__(self):
        self._users: Dict[int, User] = {}
        self._next_id = 1
    
    def save(self, user: User) -> User:
        """保存用户"""
        if user.id is None:
            user.id = self._next_id
            self._next_id += 1
        
        self._users[user.id] = user
        user.updated_at = datetime.now()
        return user
    
    def find_by_id(self, user_id: int) -> Optional[User]:
        """根据ID查找用户"""
        return self._users.get(user_id)
    
    def find_by_username(self, username: str) -> Optional[User]:
        """根据用户名查找用户"""
        for user in self._users.values():
            if user.username == username:
                return user
        return None
    
    def find_by_email(self, email: str) -> Optional[User]:
        """根据邮箱查找用户"""
        for user in self._users.values():
            if user.email == email:
                return user
        return None
    
    def find_all(self) -> list[User]:
        """获取所有用户"""
        return list(self._users.values())
    
    def delete(self, user_id: int) -> bool:
        """删除用户"""
        if user_id in self._users:
            del self._users[user_id]
            return True
        return False
    
    def count(self) -> int:
        """获取用户总数"""
        return len(self._users)