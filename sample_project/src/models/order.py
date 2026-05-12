"""
订单模型

定义订单相关的数据结构和基本操作。
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from enum import Enum
import uuid


class OrderStatus(Enum):
    """订单状态枚举"""
    PENDING = "pending"
    CONFIRMED = "confirmed"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class PaymentStatus(Enum):
    """支付状态枚举"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"


@dataclass
class OrderItem:
    """订单项"""
    id: Optional[int] = None
    product_id: int = 0
    product_name: str = ""
    product_sku: str = ""
    quantity: int = 1
    unit_price: float = 0.0
    total_price: float = 0.0
    
    def __post_init__(self):
        """计算总价"""
        self.total_price = self.unit_price * self.quantity
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'id': self.id,
            'product_id': self.product_id,
            'product_name': self.product_name,
            'product_sku': self.product_sku,
            'quantity': self.quantity,
            'unit_price': self.unit_price,
            'total_price': self.total_price
        }
    
    def update_quantity(self, new_quantity: int):
        """更新数量并重新计算总价"""
        if new_quantity > 0:
            self.quantity = new_quantity
            self.total_price = self.unit_price * self.quantity


@dataclass
class ShippingAddress:
    """配送地址"""
    street: str = ""
    city: str = ""
    state: str = ""
    postal_code: str = ""
    country: str = ""
    phone: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'street': self.street,
            'city': self.city,
            'state': self.state,
            'postal_code': self.postal_code,
            'country': self.country,
            'phone': self.phone
        }
    
    def get_full_address(self) -> str:
        """获取完整地址"""
        return f"{self.street}, {self.city}, {self.state} {self.postal_code}, {self.country}"


@dataclass
class Order:
    """订单实体类"""
    id: Optional[int] = None
    order_number: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: int = 0
    items: List[OrderItem] = field(default_factory=list)
    status: OrderStatus = OrderStatus.PENDING
    payment_status: PaymentStatus = PaymentStatus.PENDING
    subtotal: float = 0.0
    tax_amount: float = 0.0
    shipping_cost: float = 0.0
    discount_amount: float = 0.0
    total_amount: float = 0.0
    currency: str = "CNY"
    shipping_address: Optional[ShippingAddress] = None
    notes: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    shipped_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    
    def __post_init__(self):
        """计算总金额"""
        self.calculate_totals()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'id': self.id,
            'order_number': self.order_number,
            'user_id': self.user_id,
            'items': [item.to_dict() for item in self.items],
            'status': self.status.value,
            'payment_status': self.payment_status.value,
            'subtotal': self.subtotal,
            'tax_amount': self.tax_amount,
            'shipping_cost': self.shipping_cost,
            'discount_amount': self.discount_amount,
            'total_amount': self.total_amount,
            'currency': self.currency,
            'shipping_address': self.shipping_address.to_dict() if self.shipping_address else None,
            'notes': self.notes,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'shipped_at': self.shipped_at.isoformat() if self.shipped_at else None,
            'delivered_at': self.delivered_at.isoformat() if self.delivered_at else None
        }
    
    def add_item(self, product_id: int, product_name: str, product_sku: str, 
                 quantity: int, unit_price: float) -> OrderItem:
        """添加订单项"""
        item = OrderItem(
            product_id=product_id,
            product_name=product_name,
            product_sku=product_sku,
            quantity=quantity,
            unit_price=unit_price
        )
        self.items.append(item)
        self.calculate_totals()
        self.updated_at = datetime.now()
        return item
    
    def remove_item(self, item_index: int) -> bool:
        """移除订单项"""
        if 0 <= item_index < len(self.items):
            del self.items[item_index]
            self.calculate_totals()
            self.updated_at = datetime.now()
            return True
        return False
    
    def calculate_totals(self):
        """计算订单总金额"""
        self.subtotal = sum(item.total_price for item in self.items)
        self.total_amount = self.subtotal + self.tax_amount + self.shipping_cost - self.discount_amount
    
    def update_status(self, status: OrderStatus):
        """更新订单状态"""
        self.status = status
        self.updated_at = datetime.now()
        
        # 更新时间戳
        if status == OrderStatus.SHIPPED and not self.shipped_at:
            self.shipped_at = datetime.now()
        elif status == OrderStatus.DELIVERED and not self.delivered_at:
            self.delivered_at = datetime.now()
    
    def update_payment_status(self, payment_status: PaymentStatus):
        """更新支付状态"""
        self.payment_status = payment_status
        self.updated_at = datetime.now()
    
    def can_be_cancelled(self) -> bool:
        """检查订单是否可以取消"""
        return self.status in [OrderStatus.PENDING, OrderStatus.CONFIRMED]
    
    def is_paid(self) -> bool:
        """检查订单是否已支付"""
        return self.payment_status == PaymentStatus.COMPLETED
    
    def is_completed(self) -> bool:
        """检查订单是否已完成"""
        return self.status == OrderStatus.DELIVERED and self.is_paid()
    
    def apply_discount(self, discount_amount: float):
        """应用折扣"""
        if 0 <= discount_amount <= self.subtotal:
            self.discount_amount = discount_amount
            self.calculate_totals()
            self.updated_at = datetime.now()
    
    def set_shipping_address(self, address: ShippingAddress):
        """设置配送地址"""
        self.shipping_address = address
        self.updated_at = datetime.now()


class OrderFactory:
    """订单工厂类"""
    
    @staticmethod
    def create_order(user_id: int) -> Order:
        """创建新订单"""
        return Order(user_id=user_id)
    
    @staticmethod
    def create_order_with_items(user_id: int, items_data: List[Dict[str, Any]]) -> Order:
        """创建包含商品的订单"""
        order = Order(user_id=user_id)
        
        for item_data in items_data:
            order.add_item(
                product_id=item_data['product_id'],
                product_name=item_data['product_name'],
                product_sku=item_data['product_sku'],
                quantity=item_data['quantity'],
                unit_price=item_data['unit_price']
            )
        
        return order


class OrderRepository:
    """订单仓库类 - 模拟数据库操作"""
    
    def __init__(self):
        self._orders: Dict[int, Order] = {}
        self._next_id = 1
        self._order_number_index: Dict[str, int] = {}
    
    def save(self, order: Order) -> Order:
        """保存订单"""
        if order.id is None:
            order.id = self._next_id
            self._next_id += 1
        
        self._orders[order.id] = order
        self._order_number_index[order.order_number] = order.id
        order.updated_at = datetime.now()
        return order
    
    def find_by_id(self, order_id: int) -> Optional[Order]:
        """根据ID查找订单"""
        return self._orders.get(order_id)
    
    def find_by_order_number(self, order_number: str) -> Optional[Order]:
        """根据订单号查找订单"""
        order_id = self._order_number_index.get(order_number)
        return self._orders.get(order_id) if order_id else None
    
    def find_by_user_id(self, user_id: int) -> List[Order]:
        """根据用户ID查找订单"""
        return [
            order for order in self._orders.values()
            if order.user_id == user_id
        ]
    
    def find_by_status(self, status: OrderStatus) -> List[Order]:
        """根据状态查找订单"""
        return [
            order for order in self._orders.values()
            if order.status == status
        ]
    
    def find_pending_orders(self) -> List[Order]:
        """查找待处理订单"""
        return self.find_by_status(OrderStatus.PENDING)
    
    def find_shipped_orders(self) -> List[Order]:
        """查找已发货订单"""
        return self.find_by_status(OrderStatus.SHIPPED)
    
    def find_all(self) -> List[Order]:
        """获取所有订单"""
        return list(self._orders.values())
    
    def delete(self, order_id: int) -> bool:
        """删除订单"""
        order = self._orders.get(order_id)
        if order:
            del self._orders[order_id]
            del self._order_number_index[order.order_number]
            return True
        return False
    
    def count(self) -> int:
        """获取订单总数"""
        return len(self._orders)
    
    def get_revenue_by_period(self, start_date: datetime, end_date: datetime) -> float:
        """获取指定时间段内的收入"""
        return sum(
            order.total_amount for order in self._orders.values()
            if start_date <= order.created_at <= end_date and order.is_paid()
        )
    
    def get_orders_by_date_range(self, start_date: datetime, end_date: datetime) -> List[Order]:
        """获取指定日期范围内的订单"""
        return [
            order for order in self._orders.values()
            if start_date <= order.created_at <= end_date
        ]