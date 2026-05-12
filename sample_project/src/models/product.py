"""
商品模型

定义商品相关的数据结构和基本操作。
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from enum import Enum


class ProductStatus(Enum):
    """商品状态枚举"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    OUT_OF_STOCK = "out_of_stock"
    DISCONTINUED = "discontinued"


class ProductCategory(Enum):
    """商品分类枚举"""
    ELECTRONICS = "electronics"
    CLOTHING = "clothing"
    BOOKS = "books"
    HOME = "home"
    SPORTS = "sports"
    TOYS = "toys"


@dataclass
class Product:
    """商品实体类"""
    id: Optional[int] = None
    name: str = ""
    description: str = ""
    price: float = 0.0
    category: ProductCategory = ProductCategory.ELECTRONICS
    status: ProductStatus = ProductStatus.ACTIVE
    stock_quantity: int = 0
    sku: str = ""
    brand: Optional[str] = None
    weight: Optional[float] = None
    dimensions: Optional[Dict[str, float]] = None
    images: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'price': self.price,
            'category': self.category.value,
            'status': self.status.value,
            'stock_quantity': self.stock_quantity,
            'sku': self.sku,
            'brand': self.brand,
            'weight': self.weight,
            'dimensions': self.dimensions,
            'images': self.images,
            'tags': self.tags,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    def is_available(self) -> bool:
        """检查商品是否可用"""
        return (
            self.status == ProductStatus.ACTIVE and 
            self.stock_quantity > 0
        )
    
    def reduce_stock(self, quantity: int) -> bool:
        """减少库存"""
        if self.stock_quantity >= quantity:
            self.stock_quantity -= quantity
            self.updated_at = datetime.now()
            
            # 如果库存为0，更新状态
            if self.stock_quantity == 0:
                self.status = ProductStatus.OUT_OF_STOCK
            
            return True
        return False
    
    def increase_stock(self, quantity: int):
        """增加库存"""
        self.stock_quantity += quantity
        self.updated_at = datetime.now()
        
        # 如果之前缺货，现在恢复为活跃状态
        if self.status == ProductStatus.OUT_OF_STOCK:
            self.status = ProductStatus.ACTIVE
    
    def update_status(self, status: ProductStatus):
        """更新商品状态"""
        self.status = status
        self.updated_at = datetime.now()
    
    def add_tag(self, tag: str):
        """添加标签"""
        if tag not in self.tags:
            self.tags.append(tag)
            self.updated_at = datetime.now()
    
    def remove_tag(self, tag: str) -> bool:
        """移除标签"""
        if tag in self.tags:
            self.tags.remove(tag)
            self.updated_at = datetime.now()
            return True
        return False
    
    def add_image(self, image_url: str):
        """添加图片"""
        if image_url not in self.images:
            self.images.append(image_url)
            self.updated_at = datetime.now()
    
    def get_discounted_price(self, discount_percentage: float) -> float:
        """获取折扣价格"""
        if 0 <= discount_percentage <= 100:
            return self.price * (1 - discount_percentage / 100)
        return self.price


class ProductFactory:
    """商品工厂类"""
    
    @staticmethod
    def create_product(
        name: str,
        description: str,
        price: float,
        category: ProductCategory,
        sku: str,
        stock_quantity: int = 0,
        **kwargs
    ) -> Product:
        """创建新商品"""
        return Product(
            name=name,
            description=description,
            price=price,
            category=category,
            sku=sku,
            stock_quantity=stock_quantity,
            **kwargs
        )
    
    @staticmethod
    def create_simple_product(name: str, price: float, sku: str) -> Product:
        """创建简单商品"""
        return ProductFactory.create_product(
            name=name,
            description=f"{name} - 基础商品",
            price=price,
            category=ProductCategory.ELECTRONICS,
            sku=sku,
            stock_quantity=100
        )


class ProductRepository:
    """商品仓库类 - 模拟数据库操作"""
    
    def __init__(self):
        self._products: Dict[int, Product] = {}
        self._next_id = 1
        self._sku_index: Dict[str, int] = {}
    
    def save(self, product: Product) -> Product:
        """保存商品"""
        if product.id is None:
            product.id = self._next_id
            self._next_id += 1
        
        self._products[product.id] = product
        self._sku_index[product.sku] = product.id
        product.updated_at = datetime.now()
        return product
    
    def find_by_id(self, product_id: int) -> Optional[Product]:
        """根据ID查找商品"""
        return self._products.get(product_id)
    
    def find_by_sku(self, sku: str) -> Optional[Product]:
        """根据SKU查找商品"""
        product_id = self._sku_index.get(sku)
        return self._products.get(product_id) if product_id else None
    
    def find_by_category(self, category: ProductCategory) -> List[Product]:
        """根据分类查找商品"""
        return [
            product for product in self._products.values()
            if product.category == category
        ]
    
    def find_available(self) -> List[Product]:
        """查找可用商品"""
        return [
            product for product in self._products.values()
            if product.is_available()
        ]
    
    def find_by_name(self, name: str) -> List[Product]:
        """根据名称查找商品（模糊匹配）"""
        return [
            product for product in self._products.values()
            if name.lower() in product.name.lower()
        ]
    
    def find_all(self) -> List[Product]:
        """获取所有商品"""
        return list(self._products.values())
    
    def delete(self, product_id: int) -> bool:
        """删除商品"""
        product = self._products.get(product_id)
        if product:
            del self._products[product_id]
            del self._sku_index[product.sku]
            return True
        return False
    
    def count(self) -> int:
        """获取商品总数"""
        return len(self._products)
    
    def get_low_stock_products(self, threshold: int = 10) -> List[Product]:
        """获取库存不足的商品"""
        return [
            product for product in self._products.values()
            if product.stock_quantity <= threshold and product.stock_quantity > 0
        ]
    
    def get_out_of_stock_products(self) -> List[Product]:
        """获取缺货商品"""
        return [
            product for product in self._products.values()
            if product.stock_quantity == 0
        ]