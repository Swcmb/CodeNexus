"""
数据模型模块

包含所有实体类的定义。
"""

from .user import User, UserFactory, UserRepository
from .product import Product, ProductFactory, ProductRepository, ProductCategory, ProductStatus
from .order import Order, OrderFactory, OrderRepository, OrderStatus, PaymentStatus, OrderItem, ShippingAddress

__all__ = [
    'User', 'UserFactory', 'UserRepository',
    'Product', 'ProductFactory', 'ProductRepository', 'ProductCategory', 'ProductStatus',
    'Order', 'OrderFactory', 'OrderRepository', 'OrderStatus', 'PaymentStatus', 'OrderItem', 'ShippingAddress'
]