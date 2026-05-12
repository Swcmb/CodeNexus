"""
订单服务

提供订单相关的业务逻辑处理。
"""

from typing import Optional, List, Dict, Any
from datetime import datetime

from models.order import Order, OrderRepository, OrderFactory, OrderStatus, PaymentStatus, ShippingAddress
from models.product import ProductRepository
from utils.database import DatabaseManager


class OrderService:
    """订单服务类"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.order_repository = OrderRepository()
        self.product_repository = ProductRepository()
    
    def create_order(self, user_id: int, items_data: List[Dict[str, Any]], 
                    shipping_address_data: Dict[str, str]) -> Dict[str, Any]:
        """
        创建新订单
        
        Args:
            user_id: 用户ID
            items_data: 订单项数据列表
            shipping_address_data: 配送地址数据
            
        Returns:
            创建结果
        """
        # 验证输入
        if not items_data:
            return {
                'success': False,
                'error': '订单项不能为空'
            }
        
        if not shipping_address_data:
            return {
                'success': False,
                'error': '配送地址不能为空'
            }
        
        try:
            # 验证库存和价格
            validated_items = []
            total_amount = 0.0
            
            for item_data in items_data:
                product_id = item_data['product_id']
                quantity = item_data['quantity']
                
                # 获取商品信息
                product = self.product_repository.find_by_id(product_id)
                if not product:
                    return {
                        'success': False,
                        'error': f'商品ID {product_id} 不存在'
                    }
                
                # 检查库存
                if product.stock_quantity < quantity:
                    return {
                        'success': False,
                        'error': f'商品 {product.name} 库存不足'
                    }
                
                # 添加到验证后的订单项
                validated_items.append({
                    'product_id': product_id,
                    'product_name': product.name,
                    'product_sku': product.sku,
                    'quantity': quantity,
                    'unit_price': product.price
                })
                
                total_amount += product.price * quantity
            
            # 创建订单
            order = OrderFactory.create_order_with_items(user_id, validated_items)
            
            # 设置配送地址
            shipping_address = ShippingAddress(**shipping_address_data)
            order.set_shipping_address(shipping_address)
            
            # 计算税费和运费（简化计算）
            order.tax_amount = total_amount * 0.08  # 8%税率
            order.shipping_cost = 10.0  # 固定运费
            order.calculate_totals()
            
            # 保存订单
            saved_order = self.order_repository.save(order)
            
            # 扣减库存
            for item in validated_items:
                product = self.product_repository.find_by_id(item['product_id'])
                if product:
                    product.reduce_stock(item['quantity'])
                    self.product_repository.save(product)
            
            return {
                'success': True,
                'order': saved_order.to_dict()
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'创建订单失败: {str(e)}'
            }
    
    def get_order_by_id(self, order_id: int) -> Optional[Dict[str, Any]]:
        """
        根据ID获取订单信息
        
        Args:
            order_id: 订单ID
            
        Returns:
            订单信息或None
        """
        order = self.order_repository.find_by_id(order_id)
        if order:
            return order.to_dict()
        return None
    
    def get_order_by_number(self, order_number: str) -> Optional[Dict[str, Any]]:
        """
        根据订单号获取订单信息
        
        Args:
            order_number: 订单号
            
        Returns:
            订单信息或None
        """
        order = self.order_repository.find_by_order_number(order_number)
        if order:
            return order.to_dict()
        return None
    
    def get_user_orders(self, user_id: int, page: int = 1, per_page: int = 20) -> Dict[str, Any]:
        """
        获取用户订单列表
        
        Args:
            user_id: 用户ID
            page: 页码
            per_page: 每页数量
            
        Returns:
            订单列表
        """
        try:
            all_orders = self.order_repository.find_by_user_id(user_id)
            
            # 按创建时间倒序排列
            all_orders.sort(key=lambda x: x.created_at, reverse=True)
            
            # 简单分页
            total = len(all_orders)
            start = (page - 1) * per_page
            end = start + per_page
            
            orders = all_orders[start:end]
            
            return {
                'success': True,
                'orders': [order.to_dict() for order in orders],
                'total': total,
                'page': page,
                'per_page': per_page
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'获取订单列表失败: {str(e)}'
            }
    
    def update_order_status(self, order_id: int, new_status: OrderStatus) -> Dict[str, Any]:
        """
        更新订单状态
        
        Args:
            order_id: 订单ID
            new_status: 新状态
            
        Returns:
            更新结果
        """
        order = self.order_repository.find_by_id(order_id)
        if not order:
            return {
                'success': False,
                'error': '订单不存在'
            }
        
        try:
            # 状态转换验证
            valid_transitions = {
                OrderStatus.PENDING: [OrderStatus.CONFIRMED, OrderStatus.CANCELLED],
                OrderStatus.CONFIRMED: [OrderStatus.PROCESSING, OrderStatus.CANCELLED],
                OrderStatus.PROCESSING: [OrderStatus.SHIPPED, OrderStatus.CANCELLED],
                OrderStatus.SHIPPED: [OrderStatus.DELIVERED],
                OrderStatus.DELIVERED: [OrderStatus.REFUNDED],
                OrderStatus.CANCELLED: [OrderStatus.REFUNDED],
                OrderStatus.REFUNDED: []
            }
            
            if new_status not in valid_transitions.get(order.status, []):
                return {
                    'success': False,
                    'error': f'无法从 {order.status.value} 状态转换到 {new_status.value} 状态'
                }
            
            # 更新状态
            order.update_status(new_status)
            self.order_repository.save(order)
            
            return {
                'success': True,
                'order': order.to_dict(),
                'message': f'订单状态已更新为 {new_status.value}'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'状态更新失败: {str(e)}'
            }
    
    def update_payment_status(self, order_id: int, new_status: PaymentStatus) -> Dict[str, Any]:
        """
        更新支付状态
        
        Args:
            order_id: 订单ID
            new_status: 新支付状态
            
        Returns:
            更新结果
        """
        order = self.order_repository.find_by_id(order_id)
        if not order:
            return {
                'success': False,
                'error': '订单不存在'
            }
        
        try:
            order.update_payment_status(new_status)
            self.order_repository.save(order)
            
            return {
                'success': True,
                'order': order.to_dict(),
                'message': f'支付状态已更新为 {new_status.value}'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'支付状态更新失败: {str(e)}'
            }
    
    def cancel_order(self, order_id: int, reason: Optional[str] = None) -> Dict[str, Any]:
        """
        取消订单
        
        Args:
            order_id: 订单ID
            reason: 取消原因
            
        Returns:
            取消结果
        """
        order = self.order_repository.find_by_id(order_id)
        if not order:
            return {
                'success': False,
                'error': '订单不存在'
            }
        
        # 检查是否可以取消
        if not order.can_be_cancelled():
            return {
                'success': False,
                'error': '订单当前状态不允许取消'
            }
        
        try:
            # 更新订单状态
            order.update_status(OrderStatus.CANCELLED)
            
            # 恢复库存
            for item in order.items:
                product = self.product_repository.find_by_id(item.product_id)
                if product:
                    product.increase_stock(item.quantity)
                    self.product_repository.save(product)
            
            # 添加取消原因
            if reason:
                order.notes = f"取消原因: {reason}"
            
            self.order_repository.save(order)
            
            return {
                'success': True,
                'order': order.to_dict(),
                'message': '订单已取消，库存已恢复'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'取消订单失败: {str(e)}'
            }
    
    def get_pending_orders(self) -> List[Dict[str, Any]]:
        """
        获取待处理订单
        
        Returns:
            待处理订单列表
        """
        try:
            orders = self.order_repository.find_pending_orders()
            return [order.to_dict() for order in orders]
        except Exception as e:
            return []
    
    def get_shipped_orders(self) -> List[Dict[str, Any]]:
        """
        获取已发货订单
        
        Returns:
            已发货订单列表
        """
        try:
            orders = self.order_repository.find_shipped_orders()
            return [order.to_dict() for order in orders]
        except Exception as e:
            return []
    
    def apply_discount(self, order_id: int, discount_amount: float) -> Dict[str, Any]:
        """
        应用订单折扣
        
        Args:
            order_id: 订单ID
            discount_amount: 折扣金额
            
        Returns:
            应用结果
        """
        order = self.order_repository.find_by_id(order_id)
        if not order:
            return {
                'success': False,
                'error': '订单不存在'
            }
        
        # 检查订单状态
        if order.status != OrderStatus.PENDING:
            return {
                'success': False,
                'error': '只有待处理订单可以应用折扣'
            }
        
        try:
            order.apply_discount(discount_amount)
            self.order_repository.save(order)
            
            return {
                'success': True,
                'order': order.to_dict(),
                'message': f'已应用 {discount_amount} 元折扣'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'应用折扣失败: {str(e)}'
            }
    
    def get_order_statistics(self, start_date: Optional[datetime] = None, 
                           end_date: Optional[datetime] = None) -> Dict[str, Any]:
        """
        获取订单统计信息
        
        Args:
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            统计信息
        """
        try:
            # 获取日期范围内的订单
            if start_date and end_date:
                orders = self.order_repository.get_orders_by_date_range(start_date, end_date)
            else:
                orders = self.order_repository.find_all()
            
            # 计算统计数据
            total_orders = len(orders)
            total_revenue = sum(order.total_amount for order in orders if order.is_paid())
            pending_orders = len([o for o in orders if o.status == OrderStatus.PENDING])
            shipped_orders = len([o for o in orders if o.status == OrderStatus.SHIPPED])
            delivered_orders = len([o for o in orders if o.status == OrderStatus.DELIVERED])
            cancelled_orders = len([o for o in orders if o.status == OrderStatus.CANCELLED])
            
            return {
                'success': True,
                'statistics': {
                    'total_orders': total_orders,
                    'total_revenue': total_revenue,
                    'pending_orders': pending_orders,
                    'shipped_orders': shipped_orders,
                    'delivered_orders': delivered_orders,
                    'cancelled_orders': cancelled_orders,
                    'completion_rate': (delivered_orders / total_orders * 100) if total_orders > 0 else 0
                }
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'获取统计信息失败: {str(e)}'
            }