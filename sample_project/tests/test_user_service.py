"""
用户服务测试

测试用户相关的业务逻辑。
"""

import unittest
import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from services.user_service import UserService
from utils.database import DatabaseManager


class TestUserService(unittest.TestCase):
    """用户服务测试类"""
    
    def setUp(self):
        """测试前准备"""
        # 使用内存数据库进行测试
        self.db_manager = DatabaseManager(":memory:")
        self.user_service = UserService(self.db_manager)
    
    def tearDown(self):
        """测试后清理"""
        self.db_manager.close()
    
    def test_register_user_success(self):
        """测试用户注册成功"""
        result = self.user_service.register_user(
            username="testuser",
            email="test@example.com",
            password="password123",
            full_name="测试用户"
        )
        
        self.assertTrue(result['success'])
        self.assertIn('user', result)
        self.assertIn('token', result)
        self.assertEqual(result['user']['username'], "testuser")
        self.assertEqual(result['user']['email'], "test@example.com")
    
    def test_register_user_duplicate_username(self):
        """测试用户名重复注册"""
        # 第一次注册
        self.user_service.register_user(
            username="testuser",
            email="test1@example.com",
            password="password123"
        )
        
        # 第二次注册相同用户名
        result = self.user_service.register_user(
            username="testuser",
            email="test2@example.com",
            password="password123"
        )
        
        self.assertFalse(result['success'])
        self.assertIn('error', result)
        self.assertIn('用户名已存在', result['error'])
    
    def test_register_user_duplicate_email(self):
        """测试邮箱重复注册"""
        # 第一次注册
        self.user_service.register_user(
            username="testuser1",
            email="test@example.com",
            password="password123"
        )
        
        # 第二次注册相同邮箱
        result = self.user_service.register_user(
            username="testuser2",
            email="test@example.com",
            password="password123"
        )
        
        self.assertFalse(result['success'])
        self.assertIn('error', result)
        self.assertIn('邮箱已被注册', result['error'])
    
    def test_register_user_invalid_input(self):
        """测试无效输入注册"""
        # 空用户名
        result = self.user_service.register_user(
            username="",
            email="test@example.com",
            password="password123"
        )
        self.assertFalse(result['success'])
        
        # 空邮箱
        result = self.user_service.register_user(
            username="testuser",
            email="",
            password="password123"
        )
        self.assertFalse(result['success'])
        
        # 空密码
        result = self.user_service.register_user(
            username="testuser",
            email="test@example.com",
            password=""
        )
        self.assertFalse(result['success'])
        
        # 密码太短
        result = self.user_service.register_user(
            username="testuser",
            email="test@example.com",
            password="123"
        )
        self.assertFalse(result['success'])
    
    def test_authenticate_user_success(self):
        """测试用户认证成功"""
        # 先注册用户
        register_result = self.user_service.register_user(
            username="testuser",
            email="test@example.com",
            password="password123"
        )
        
        # 认证用户
        auth_result = self.user_service.authenticate_user("testuser", "password123")
        
        self.assertTrue(auth_result['success'])
        self.assertIn('user', auth_result)
        self.assertIn('token', auth_result)
        self.assertEqual(auth_result['user']['username'], "testuser")
    
    def test_authenticate_user_wrong_password(self):
        """测试错误密码认证"""
        # 先注册用户
        self.user_service.register_user(
            username="testuser",
            email="test@example.com",
            password="password123"
        )
        
        # 使用错误密码认证
        auth_result = self.user_service.authenticate_user("testuser", "wrongpassword")
        
        self.assertFalse(auth_result['success'])
        self.assertIn('error', auth_result)
    
    def test_authenticate_user_not_found(self):
        """测试不存在的用户认证"""
        auth_result = self.user_service.authenticate_user("nonexistent", "password123")
        
        self.assertFalse(auth_result['success'])
        self.assertIn('error', auth_result)
    
    def test_get_user_by_id(self):
        """测试根据ID获取用户"""
        # 先注册用户
        register_result = self.user_service.register_user(
            username="testuser",
            email="test@example.com",
            password="password123"
        )
        user_id = register_result['user']['id']
        
        # 获取用户
        user = self.user_service.get_user_by_id(user_id)
        
        self.assertIsNotNone(user)
        self.assertEqual(user['username'], "testuser")
        self.assertEqual(user['email'], "test@example.com")
        self.assertNotIn('password_hash', user)  # 确保敏感信息不返回
    
    def test_get_user_by_id_not_found(self):
        """测试获取不存在的用户"""
        user = self.user_service.get_user_by_id(999)
        self.assertIsNone(user)
    
    def test_update_user(self):
        """测试更新用户信息"""
        # 先注册用户
        register_result = self.user_service.register_user(
            username="testuser",
            email="test@example.com",
            password="password123"
        )
        user_id = register_result['user']['id']
        
        # 更新用户信息
        update_result = self.user_service.update_user(user_id, {
            'full_name': '更新后的用户名',
            'phone': '13800138000'
        })
        
        self.assertTrue(update_result['success'])
        self.assertEqual(update_result['user']['full_name'], '更新后的用户名')
        self.assertEqual(update_result['user']['phone'], '13800138000')
    
    def test_update_user_not_found(self):
        """测试更新不存在的用户"""
        update_result = self.user_service.update_user(999, {
            'full_name': '更新后的用户名'
        })
        
        self.assertFalse(update_result['success'])
        self.assertIn('error', update_result)
    
    def test_change_password(self):
        """测试修改密码"""
        # 先注册用户
        register_result = self.user_service.register_user(
            username="testuser",
            email="test@example.com",
            password="password123"
        )
        user_id = register_result['user']['id']
        
        # 修改密码
        change_result = self.user_service.change_password(
            user_id, "password123", "newpassword123"
        )
        
        self.assertTrue(change_result['success'])
        
        # 使用新密码认证
        auth_result = self.user_service.authenticate_user("testuser", "newpassword123")
        self.assertTrue(auth_result['success'])
        
        # 使用旧密码认证应该失败
        auth_result = self.user_service.authenticate_user("testuser", "password123")
        self.assertFalse(auth_result['success'])
    
    def test_change_password_wrong_old_password(self):
        """测试使用错误旧密码修改密码"""
        # 先注册用户
        register_result = self.user_service.register_user(
            username="testuser",
            email="test@example.com",
            password="password123"
        )
        user_id = register_result['user']['id']
        
        # 使用错误旧密码修改
        change_result = self.user_service.change_password(
            user_id, "wrongpassword", "newpassword123"
        )
        
        self.assertFalse(change_result['success'])
        self.assertIn('error', change_result)
    
    def test_deactivate_user(self):
        """测试禁用用户"""
        # 先注册用户
        register_result = self.user_service.register_user(
            username="testuser",
            email="test@example.com",
            password="password123"
        )
        user_id = register_result['user']['id']
        
        # 禁用用户
        deactivate_result = self.user_service.deactivate_user(user_id)
        self.assertTrue(deactivate_result['success'])
        
        # 禁用后应该无法认证
        auth_result = self.user_service.authenticate_user("testuser", "password123")
        self.assertFalse(auth_result['success'])
    
    def test_activate_user(self):
        """测试激活用户"""
        # 先注册并禁用用户
        register_result = self.user_service.register_user(
            username="testuser",
            email="test@example.com",
            password="password123"
        )
        user_id = register_result['user']['id']
        
        self.user_service.deactivate_user(user_id)
        
        # 重新激活用户
        activate_result = self.user_service.activate_user(user_id)
        self.assertTrue(activate_result['success'])
        
        # 激活后应该可以认证
        auth_result = self.user_service.authenticate_user("testuser", "password123")
        self.assertTrue(auth_result['success'])
    
    def test_search_users(self):
        """测试搜索用户"""
        # 注册多个用户
        users_data = [
            {"username": "alice", "email": "alice@example.com", "password": "password123"},
            {"username": "bob", "email": "bob@example.com", "password": "password123"},
            {"username": "charlie", "email": "charlie@example.com", "password": "password123"}
        ]
        
        for user_data in users_data:
            self.user_service.register_user(**user_data)
        
        # 搜索用户
        results = self.user_service.search_users("alice")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['username'], "alice")
        
        # 搜索邮箱
        results = self.user_service.search_users("example.com")
        self.assertEqual(len(results), 3)  # 所有用户都包含 example.com


if __name__ == '__main__':
    unittest.main()