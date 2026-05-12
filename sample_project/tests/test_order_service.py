"""
订单服务测试

测试订单相关的业务逻辑。
"""

import unittest
import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from services.user_service import UserService
from services.product_service import ProductService
from services.order_service import OrderService
from utils.database import DatabaseManager
from models.product import ProductCategory


class TestOrderService(unittest.TestCase):
    """订单服务测试类"""
    
    def setUp(self):
        """测试前准备"""
        # 使用内存数据库进行测试
        self.db_manager = DatabaseManager(":memory:")
        self.user_service = UserService(self.db_manager)
        self.product_service = ProductService(self.db_manager)
        self.order_service = OrderService(self.db_manager)
        
        # 创建测试用户
        user_result = self.user_service.register_user(
            username="testuser",
            email="test@example.com",
            password="password123"
        )
        self.user_id = user_result['user']['id']
        
        # 创建测试商品
        product_result = self.product_service.create_product(
            name="测试商品",
            description="测试商品描述",
            price=100.0,
            category=ProductCategory.ELECTRONICS,
            sku="TEST001",
            stock_quantity=50
        )
        self.product_id = product_result['product']['id']
    
    def tearDown(self):
        """测试后清理"""
        self.db_manager.close()
    
    def test_create_order_success(self):
        """测试创建订单成功"""
        items_data = [
            {
                'product_id': self.product_id,
                'quantity': 2
            }
        ]
        
        shipping_address = {
            'street': '测试地址123号',
            'city': '测试城市',
            'state': '测试省份',
            'postal_code': '100000',
            'country': '中国',
            'phone': '13800138000'
        }
        
        result = self.order_service.create_order(self.user_id, items_data, shipping_address)
        
        self.assertTrue(result['success'])
        self.assertIn('order', result)
        self.assertEqual(result['order']['user_id'], self.user_id)
        self.assertEqual(len(result['order']['items']), 1)
        self.assertEqual(result['order']['items'][0]['quantity'], 2)
        self.assertEqual(result['order']['status'], 'pending')
    
    def test_create_order_empty_items(self):
        """测试创建订单无商品项"""
        shipping_address = {
            'street': '测试地址123号',
            'city': '测试城市',
            'state': '测试省份',
            'postal_code': '100000',
            'country': '中国',
            'phone': '13800138000'
        }
        
        result = self.order_service.create_order(self.user_id, [], shipping_address)
        
        self.assertFalse(result['success'])
        self.assertIn('error', result)
    
    def test_create_order_no_shipping_address(self):
        """测试创建订单无配送地址"""
        items_data = [
            {
                'product_id': self.product_id,
                'quantity': 1
            }
        ]
        
        result = self.order_service.create_order(self.user_id, items_data, {})
        
        self.assertFalse(result['success'])
        self.assertIn('error', result)
    
    def test_create_order_product_not_found(self):
        """测试创建订单商品不存在"""
        items_data = [
            {
                'product_id': 999,  # 不存在的商品ID
                'quantity': 1
            }
        ]
        
        shipping_address = {
            'street': '测试地址123号',
            'city': '测试城市',
            'state': '测试省份',
            'postal_code': '100000',
            'country': '中国',
            'phone': '13800138000'
        }
        
        result = self.order_service.create_order(self.user_id, items_data, shipping_address)
        
        self.assertFalse(result['success'])
        self.assertIn('error', result)
    
    def test_create_order_insufficient_stock(self):
        """测试创建订单库存不足"""
        items_data = [
            {
                'product_id': self.product_id,
                'quantity': 100  # 超过库存数量
            }
        ]
        
        shipping_address = {
            'street': '测试地址123号',
            'city': '测试城市',
            'state': '测试省份',
            'postal_code': '100000',
            'country': '中国',
            'phone': '13800138000'
        }
        
        result = self.order_service.create_order(self.user_id, items_data, shipping_address)
        
        self.assertFalse(result['success'])
        self.assertIn('error', result)
    
    def test_get_order_by_id(self):
        """测试根据ID获取订单"""
        # 先创建订单
        items_data = [{'product_id': self.product_id, 'quantity': 1}]
        shipping_address = {
            'street': '测试地址', 'city': '测试城市', 'state': '测试省份',
            'postal_code': '100000', 'country': '中国', 'phone': '13800138000'
        }
        
        create_result = self.order_service.create_order(self.user_id, items_data, shipping_address)
        order_id = create_result['order']['id']
        
        # 获取订单
        order = self.order_service.get_order_by_id(order_id)
        
        self.assertIsNotNone(order)
        self.assertEqual(order['id'], order_id)
        self.assertEqual(order['user_id'], self.user_id)
    
    def test_get_order_by_number(self):
        """测试根据订单号获取订单"""
        # 先创建订单
        items_data = [{'product_id': self.product_id, 'quantity': 1}]
        shipping_address = {
            'street': '测试地址', 'city': '测试城市', 'state': '测试省份',
            'postal_code': '100000', 'country': '中国', 'phone': '13800138000'
        }
        
        create_result = self.order_service.create_order(self.user_id, items_data, shipping_address)
        order_number = create_result['order']['order_number']
        
        # 获取订单
        order = self.order_service.get_order_by_number(order_number)
        
        self.assertIsNotNone(order)
        self.assertEqual(order['order_number'], order_number)
    
    def test_get_user_orders(self):
        """测试获取用户订单列表"""
        # 创建多个订单
        for i in range(3):
            items_data = [{'product_id': self.product_id, 'quantity': 1}]
            shipping_address = {
                'street': f'测试地址{i}号', 'city': '测试城市', 'state': '测试省份',
                'postal_code': '100000', 'country': '中国', 'phone': '13800138000'
            }
            self.order_service.create_order(self.user_id, items_data, shipping_address)
        
        # 获取用户订单
        result = self.order_service.get_user_orders(self.user_id)
        
        self.assertTrue(result['success'])
        self.assertEqual(len(result['orders']), 3)
        self.assertEqual(result['total'], 3)
    
    def test_update_order_status(self):
        """测试更新订单状态"""
        # 先创建订单
        items_data = [{'product_id': self.product_id, 'quantity': 1}]
        shipping_address = {
            'street': '测试地址', 'city': '测试城市', 'state': '测试省份',
            'postal_code': '100000', 'country': '中国', 'phone': '13800138000'
        }
        
        create_result = self.order_service.create_order(self.user_id, items_data, shipping_address)
        order_id = create_result['order']['id']
        
        # 更新状态
        from models.order import OrderStatus
        update_result = self.order_service.update_order_status(order_id, OrderStatus.CONFIRMED)
        
        self.assertTrue(update_result['success'])
        self.assertEqual(update_result['order']['status'], 'confirmed')
    
    def test_update_order_status_invalid_transition(self):
        """测试无效的订单状态转换"""
        # 先创建订单
        items_data = [{'product_id': self.product_id, 'quantity': 1}]
        shipping_address = {
            'street': '测试地址', 'city': '测试城市', 'state': '测试省份',
            'postal_code': '100000', 'country': '中国', 'phone': '13800138000'
        }
        
        create_result = self.order_service.create_order(self.user_id, items_data, shipping_address)
        order_id = create_result['order']['id']
        
        # 尝试无效的状态转换（从pending直接到shipped）
        from models.order import OrderStatus
        update_result = self.order_service.update_order_status(order_id, OrderStatus.SHIPPED)
        
        self.assertFalse(update_result['success'])
        self.assertIn('error', update_result)
    
    def test_cancel_order(self):
        """测试取消订单"""
        # 先创建订单
        items_data = [{'product_id': self.product_id, 'quantity': 5}]
        shipping_address = {
            'street': '测试地址', 'city': '测试城市', 'state': '测试省份',
            'postal_code': '100000', 'country': '中国', 'phone': '13800138000'
        }
        
        create_result = self.order_service.create_order(self.user_id, items_data, shipping_address)
        order_id = create_result['order']['id']
        
        # 检查库存是否减少
        product = self.product_service.get_product_by_id(self.product_id)
        original_stock = product['stock_quantity']
        self.assertEqual(original_stock, 45)  # 50 - 5
        
        # 取消订单
        cancel_result = self.order_service.cancel_order(order_id, "用户要求取消")
        
        self.assertTrue(cancel_result['success'])
        self.assertEqual(cancel_result['order']['status'], 'cancelled')
        
        # 检查库存是否恢复
        product = self.product_service.get_product_by_id(self.product_id)
        self.assertEqual(product['stock_quantity'], 50)  # 恢复到原始库存
    
    def test_cancel_order_not_allowed(self):
        """测试取消不允许取消的订单"""
        # 先创建订单
        items_data = [{'product_id': self.product_id, 'quantity': 1}]
        shipping_address = {
            'street': '测试地址', 'city': '测试城市', 'state': '测试省份',
            'postal_code': '100000', 'country': '中国', 'phone': '13800138000'
        }
        
        create_result = self.order_service.create_order(self.user_id, items_data, shipping_address)
        order_id = create_result['order']['id']
        
        # 将订单状态更新为已发货
        from models.order import OrderStatus
        self.order_service.update_order_status(order_id, OrderStatus.SHIPPED)
        
        # 尝试取消已发货的订单
        cancel_result = self.order_service.cancel_order(order_id)
        
        self.assertFalse(cancel_result['success'])
        self.assertIn('error', cancel_result)
    
    def test_apply_discount(self):
        """测试应用订单折扣"""
        # 先创建订单
        items_data = [{'product_id': self.product_id, 'quantity': 2}]
        shipping_address = {
            'street': '测试地址', 'city': '测试城市', 'state': '测试省份',
            'postal_code': '100000', 'country': '中国', 'phone': '13800138000'
        }
        
        create_result = self.order_service.create_order(self.user_id, items_data, shipping_address)
        order_id = create_result['order']['id']
        original_total = create_result['order']['total_amount']
        
        # 应用折扣
        discount_result = self.order_service.apply_discount(order_id, 10.0)
        
        self.assertTrue(discount_result['success'])
        self.assertEqual(discount_result['order']['discount_amount'], 10.0)
        self.assertEqual(discount_result['order']['total_amount'], original_total - 10.0)
    
    def test_get_order_statistics(self):
        """测试获取订单统计信息"""
        # 创建几个订单
        for i in range(3):
            items_data = [{'product_id': self.product_id, 'quantity': 1}]
            shipping_address = {
                'street': f'测试地址{i}号', 'city': '测试城市', 'state': '测试省份',
                'postal_code': '100000', 'country': '中国', 'phone': '13800138000'
            }
            self.order_service.create_order(self.user_id, items_data, shipping_address)
        
        # 获取统计信息
        stats_result = self.order_service.get_order_statistics()
        
        self.assertTrue(stats_result['success'])
        stats = stats_result['statistics']
        self.assertEqual(stats['total_orders'], 3)
        self.assertGreater(stats['total_revenue'], 0)


if __name__ == '__main__':
    unittest.main()