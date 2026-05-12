"""
电商系统主入口

启动和管理整个电商系统。
"""

import sys
import os
from pathlib import Path

# 添加项目路径到系统路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from services.user_service import UserService
from services.product_service import ProductService
from services.order_service import OrderService
from utils.database import DatabaseManager
from utils.auth import AuthManager


class ECommerceSystem:
    """电商系统主类"""
    
    def __init__(self):
        """初始化系统"""
        print("正在初始化电商系统...")
        
        # 初始化数据库管理器
        self.db_manager = DatabaseManager()
        
        # 初始化服务
        self.user_service = UserService(self.db_manager)
        self.product_service = ProductService(self.db_manager)
        self.order_service = OrderService(self.db_manager)
        self.auth_manager = AuthManager()
        
        print("系统初始化完成！")
    
    def create_sample_data(self):
        """创建示例数据"""
        print("\n正在创建示例数据...")
        
        # 创建示例用户
        admin_result = self.user_service.register_user(
            username="admin",
            email="admin@example.com",
            password="admin123",
            full_name="系统管理员"
        )
        
        if admin_result['success']:
            print(f"[OK] 创建管理员用户: {admin_result['user']['username']}")
        else:
            print(f"[ERROR] 创建管理员失败: {admin_result['error']}")
        
        user_result = self.user_service.register_user(
            username="testuser",
            email="user@example.com",
            password="user123",
            full_name="测试用户"
        )
        
        if user_result['success']:
            print(f"[OK] 创建普通用户: {user_result['user']['username']}")
        else:
            print(f"[ERROR] 创建用户失败: {user_result['error']}")
        
        # 创建示例商品
        from models.product import ProductCategory
        
        products_data = [
            {
                'name': '智能手机',
                'description': '高性能智能手机，支持5G网络',
                'price': 2999.00,
                'category': ProductCategory.ELECTRONICS,
                'sku': 'PHONE001',
                'stock_quantity': 100,
                'brand': 'TechBrand',
                'tags': ['5G', '智能手机', '热门']
            },
            {
                'name': '笔记本电脑',
                'description': '轻薄便携的商务笔记本',
                'price': 5999.00,
                'category': ProductCategory.ELECTRONICS,
                'sku': 'LAPTOP001',
                'stock_quantity': 50,
                'brand': 'CompTech',
                'tags': ['笔记本', '商务', '轻薄']
            },
            {
                'name': '运动鞋',
                'description': '舒适透气的运动鞋',
                'price': 299.00,
                'category': ProductCategory.SPORTS,
                'sku': 'SHOES001',
                'stock_quantity': 200,
                'brand': 'SportWear',
                'tags': ['运动', '舒适', '透气']
            },
            {
                'name': '编程书籍',
                'description': 'Python编程入门指南',
                'price': 59.00,
                'category': ProductCategory.BOOKS,
                'sku': 'BOOK001',
                'stock_quantity': 500,
                'tags': ['编程', 'Python', '入门']
            }
        ]
        
        for product_data in products_data:
            result = self.product_service.create_product(**product_data)
            if result['success']:
                print(f"[OK] 创建商品: {result['product']['name']}")
            else:
                print(f"[ERROR] 创建商品失败: {result['error']}")
        
        print("示例数据创建完成！")
    
    def demo_user_operations(self):
        """演示用户操作"""
        print("\n=== 用户操作演示 ===")
        
        # 用户登录
        login_result = self.user_service.authenticate_user("testuser", "user123")
        if login_result['success']:
            user_id = login_result['user']['id']
            token = login_result['token']
            print(f"[OK] 用户登录成功: {login_result['user']['username']}")
            
            # 获取用户信息
            user_info = self.user_service.get_user_by_id(user_id)
            if user_info:
                print(f"[OK] 获取用户信息: {user_info['username']} ({user_info['email']})")
            
            # 更新用户信息
            update_result = self.user_service.update_user(user_id, {
                'full_name': '更新后的测试用户',
                'phone': '13800138000'
            })
            if update_result['success']:
                print(f"[OK] 用户信息更新成功")
            
            return user_id, token
        else:
            print(f"[ERROR] 用户登录失败: {login_result['error']}")
            return None, None
    
    def demo_product_operations(self):
        """演示商品操作"""
        print("\n=== 商品操作演示 ===")
        
        # 获取所有商品
        all_products = self.product_service.get_all_products()
        if all_products['success']:
            print(f"[OK] 获取到 {len(all_products['products'])} 个商品")
            
            # 显示前3个商品
            for i, product in enumerate(all_products['products'][:3]):
                print(f"  {i+1}. {product['name']} - RMB{product['price']} (库存: {product['stock_quantity']})")
        
        # 搜索商品
        search_results = self.product_service.search_products("手机")
        print(f"[OK] 搜索'手机'找到 {len(search_results)} 个商品")
        
        # 获取库存不足的商品
        low_stock = self.product_service.get_low_stock_products(threshold=100)
        print(f"[OK] 库存不足的商品: {len(low_stock)} 个")
        
        return all_products['products'] if all_products['success'] else []
    
    def demo_order_operations(self, user_id, products):
        """演示订单操作"""
        print("\n=== 订单操作演示 ===")
        
        if not user_id or not products:
            print("✗ 缺少用户或商品信息，跳过订单演示")
            return
        
        # 创建订单
        order_items = [
            {
                'product_id': products[0]['id'],
                'quantity': 1
            },
            {
                'product_id': products[1]['id'] if len(products) > 1 else products[0]['id'],
                'quantity': 2
            }
        ]
        
        shipping_address = {
            'street': '北京市朝阳区建国路88号',
            'city': '北京',
            'state': '北京',
            'postal_code': '100020',
            'country': '中国',
            'phone': '13800138000'
        }
        
        order_result = self.order_service.create_order(user_id, order_items, shipping_address)
        if order_result['success']:
            order = order_result['order']
            print(f"[OK] 创建订单成功: {order['order_number']}")
            print(f"  订单金额: RMB{order['total_amount']}")
            print(f"  订单状态: {order['status']}")
            
            order_id = order['id']
            
            # 更新订单状态
            status_result = self.order_service.update_order_status(order_id, "confirmed")
            if status_result['success']:
                print(f"[OK] 订单状态更新为: {status_result['order']['status']}")
            
            # 更新支付状态
            payment_result = self.order_service.update_payment_status(order_id, "completed")
            if payment_result['success']:
                print(f"[OK] 支付状态更新为: {payment_result['order']['payment_status']}")
            
            return order_id
        else:
            print(f"[ERROR] 创建订单失败: {order_result['error']}")
            return None
    
    def demo_statistics(self):
        """演示统计功能"""
        print("\n=== 统计信息演示 ===")
        
        # 用户统计
        all_users = self.user_service.get_all_users()
        if all_users['success']:
            print(f"[OK] 总用户数: {all_users['total']}")
        
        # 商品统计
        all_products = self.product_service.get_all_products()
        if all_products['success']:
            print(f"[OK] 总商品数: {all_products['total']}")
        
        # 订单统计
        order_stats = self.order_service.get_order_statistics()
        if order_stats['success']:
            stats = order_stats['statistics']
            print(f"[OK] 订单统计:")
            print(f"  总订单数: {stats['total_orders']}")
            print(f"  总收入: RMB{stats['total_revenue']:.2f}")
            print(f"  完成率: {stats['completion_rate']:.1f}%")
        
        # 数据库健康检查
        db_health = self.db_manager.health_check()
        if db_health['connection_status'] == 'healthy':
            print(f"[OK] 数据库状态: 健康")
            print(f"  数据库大小: {db_health['database_size']} 字节")
            for table, count in db_health['tables'].items():
                print(f"  {table} 表记录数: {count}")
    
    def run_demo(self):
        """运行完整演示"""
        print("=" * 60)
        print("codenexus 示例项目 - 电商系统演示")
        print("=" * 60)
        
        try:
            # 创建示例数据
            self.create_sample_data()
            
            # 演示各种操作
            user_id, token = self.demo_user_operations()
            products = self.demo_product_operations()
            order_id = self.demo_order_operations(user_id, products)
            
            # 显示统计信息
            self.demo_statistics()
            
            print("\n" + "=" * 60)
            print("演示完成！")
            print("=" * 60)
            print("\n使用 codenexus 分析此项目:")
            print("python -m codenexus parse . --output ./analysis")
            print("python -m codenexus graph info")
            print("python -m codenexus docs --output ./docs")
            
        except Exception as e:
            print(f"\n演示过程中出现错误: {e}")
            import traceback
            traceback.print_exc()


def main():
    """主函数"""
    system = ECommerceSystem()
    system.run_demo()


if __name__ == "__main__":
    main()
