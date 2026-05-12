"""
商品服务

提供商品相关的业务逻辑处理。
"""

from typing import Optional, List, Dict, Any
from datetime import datetime

from models.product import Product, ProductRepository, ProductFactory, ProductCategory, ProductStatus
from utils.database import DatabaseManager


class ProductService:
    """商品服务类"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.product_repository = ProductRepository()
    
    def create_product(self, name: str, description: str, price: float, 
                      category: ProductCategory, sku: str, stock_quantity: int = 0,
                      **kwargs) -> Dict[str, Any]:
        """
        创建新商品
        
        Args:
            name: 商品名称
            description: 商品描述
            price: 价格
            category: 分类
            sku: SKU编码
            stock_quantity: 库存数量
            **kwargs: 其他属性
            
        Returns:
            创建结果
        """
        # 验证输入
        if not name or not sku:
            return {
                'success': False,
                'error': '商品名称和SKU不能为空'
            }
        
        if price < 0:
            return {
                'success': False,
                'error': '价格不能为负数'
            }
        
        if stock_quantity < 0:
            return {
                'success': False,
                'error': '库存数量不能为负数'
            }
        
        # 检查SKU是否已存在
        existing_product = self.product_repository.find_by_sku(sku)
        if existing_product:
            return {
                'success': False,
                'error': 'SKU已存在'
            }
        
        try:
            # 创建商品
            product = ProductFactory.create_product(
                name=name,
                description=description,
                price=price,
                category=category,
                sku=sku,
                stock_quantity=stock_quantity,
                **kwargs
            )
            
            # 保存商品
            saved_product = self.product_repository.save(product)
            
            return {
                'success': True,
                'product': saved_product.to_dict()
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'创建商品失败: {str(e)}'
            }
    
    def get_product_by_id(self, product_id: int) -> Optional[Dict[str, Any]]:
        """
        根据ID获取商品信息
        
        Args:
            product_id: 商品ID
            
        Returns:
            商品信息或None
        """
        product = self.product_repository.find_by_id(product_id)
        if product:
            return product.to_dict()
        return None
    
    def get_product_by_sku(self, sku: str) -> Optional[Dict[str, Any]]:
        """
        根据SKU获取商品信息
        
        Args:
            sku: SKU编码
            
        Returns:
            商品信息或None
        """
        product = self.product_repository.find_by_sku(sku)
        if product:
            return product.to_dict()
        return None
    
    def update_product(self, product_id: int, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        更新商品信息
        
        Args:
            product_id: 商品ID
            update_data: 更新数据
            
        Returns:
            更新结果
        """
        product = self.product_repository.find_by_id(product_id)
        if not product:
            return {
                'success': False,
                'error': '商品不存在'
            }
        
        try:
            # 更新允许的字段
            updatable_fields = [
                'name', 'description', 'price', 'category', 'status',
                'brand', 'weight', 'dimensions'
            ]
            
            for field, value in update_data.items():
                if field in updatable_fields and hasattr(product, field):
                    # 特殊处理枚举类型
                    if field == 'category' and isinstance(value, str):
                        product.category = ProductCategory(value)
                    elif field == 'status' and isinstance(value, str):
                        product.status = ProductStatus(value)
                    else:
                        setattr(product, field, value)
            
            # 验证价格
            if 'price' in update_data and product.price < 0:
                return {
                    'success': False,
                    'error': '价格不能为负数'
                }
            
            # 保存更新
            updated_product = self.product_repository.save(product)
            
            return {
                'success': True,
                'product': updated_product.to_dict()
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'更新失败: {str(e)}'
            }
    
    def update_stock(self, product_id: int, quantity_change: int) -> Dict[str, Any]:
        """
        更新库存数量
        
        Args:
            product_id: 商品ID
            quantity_change: 数量变化（正数为增加，负数为减少）
            
        Returns:
            更新结果
        """
        product = self.product_repository.find_by_id(product_id)
        if not product:
            return {
                'success': False,
                'error': '商品不存在'
            }
        
        try:
            if quantity_change > 0:
                product.increase_stock(quantity_change)
            elif quantity_change < 0:
                if not product.reduce_stock(abs(quantity_change)):
                    return {
                        'success': False,
                        'error': '库存不足'
                    }
            
            # 保存更新
            updated_product = self.product_repository.save(product)
            
            return {
                'success': True,
                'product': updated_product.to_dict(),
                'message': f'库存更新成功，当前库存: {updated_product.stock_quantity}'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'库存更新失败: {str(e)}'
            }
    
    def delete_product(self, product_id: int) -> Dict[str, Any]:
        """
        删除商品
        
        Args:
            product_id: 商品ID
            
        Returns:
            删除结果
        """
        product = self.product_repository.find_by_id(product_id)
        if not product:
            return {
                'success': False,
                'error': '商品不存在'
            }
        
        # 检查商品状态
        if product.status == ProductStatus.ACTIVE and product.stock_quantity > 0:
            return {
                'success': False,
                'error': '活跃且有库存的商品不能删除'
            }
        
        try:
            success = self.product_repository.delete(product_id)
            
            if success:
                return {
                    'success': True,
                    'message': '商品删除成功'
                }
            else:
                return {
                    'success': False,
                    'error': '删除失败'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f'删除失败: {str(e)}'
            }
    
    def get_products_by_category(self, category: ProductCategory) -> List[Dict[str, Any]]:
        """
        根据分类获取商品列表
        
        Args:
            category: 商品分类
            
        Returns:
            商品列表
        """
        try:
            products = self.product_repository.find_by_category(category)
            return [product.to_dict() for product in products]
        except Exception as e:
            return []
    
    def get_available_products(self) -> List[Dict[str, Any]]:
        """
        获取可用商品列表
        
        Returns:
            可用商品列表
        """
        try:
            products = self.product_repository.find_available()
            return [product.to_dict() for product in products]
        except Exception as e:
            return []
    
    def search_products(self, keyword: str) -> List[Dict[str, Any]]:
        """
        搜索商品
        
        Args:
            keyword: 搜索关键词
            
        Returns:
            匹配的商品列表
        """
        try:
            products = self.product_repository.find_by_name(keyword)
            return [product.to_dict() for product in products]
        except Exception as e:
            return []
    
    def get_low_stock_products(self, threshold: int = 10) -> List[Dict[str, Any]]:
        """
        获取库存不足的商品
        
        Args:
            threshold: 库存阈值
            
        Returns:
            库存不足的商品列表
        """
        try:
            products = self.product_repository.get_low_stock_products(threshold)
            return [product.to_dict() for product in products]
        except Exception as e:
            return []
    
    def get_out_of_stock_products(self) -> List[Dict[str, Any]]:
        """
        获取缺货商品
        
        Returns:
            缺货商品列表
        """
        try:
            products = self.product_repository.get_out_of_stock_products()
            return [product.to_dict() for product in products]
        except Exception as e:
            return []
    
    def add_product_tag(self, product_id: int, tag: str) -> Dict[str, Any]:
        """
        添加商品标签
        
        Args:
            product_id: 商品ID
            tag: 标签
            
        Returns:
            操作结果
        """
        product = self.product_repository.find_by_id(product_id)
        if not product:
            return {
                'success': False,
                'error': '商品不存在'
            }
        
        try:
            product.add_tag(tag)
            self.product_repository.save(product)
            
            return {
                'success': True,
                'message': '标签添加成功',
                'tags': product.tags
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'添加标签失败: {str(e)}'
            }
    
    def remove_product_tag(self, product_id: int, tag: str) -> Dict[str, Any]:
        """
        移除商品标签
        
        Args:
            product_id: 商品ID
            tag: 标签
            
        Returns:
            操作结果
        """
        product = self.product_repository.find_by_id(product_id)
        if not product:
            return {
                'success': False,
                'error': '商品不存在'
            }
        
        try:
            success = product.remove_tag(tag)
            if success:
                self.product_repository.save(product)
                return {
                    'success': True,
                    'message': '标签移除成功',
                    'tags': product.tags
                }
            else:
                return {
                    'success': False,
                    'error': '标签不存在'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f'移除标签失败: {str(e)}'
            }
    
    def get_all_products(self, page: int = 1, per_page: int = 20) -> Dict[str, Any]:
        """
        获取所有商品列表
        
        Args:
            page: 页码
            per_page: 每页数量
            
        Returns:
            商品列表
        """
        try:
            all_products = self.product_repository.find_all()
            
            # 简单分页
            total = len(all_products)
            start = (page - 1) * per_page
            end = start + per_page
            
            products = all_products[start:end]
            
            return {
                'success': True,
                'products': [product.to_dict() for product in products],
                'total': total,
                'page': page,
                'per_page': per_page
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'获取商品列表失败: {str(e)}'
            }