"""
商品API接口

提供商品相关的HTTP API接口。
"""

from typing import Dict, Any, List
from services.product_service import ProductService
from utils.auth import AuthManager, PermissionManager
from utils.database import DatabaseManager
from models.product import ProductCategory


class ProductAPI:
    """商品API类"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.product_service = ProductService(db_manager)
        self.auth_manager = AuthManager()
        self.permission_manager = PermissionManager()
    
    def create_product(self, token: str, product_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        创建商品API
        
        Args:
            token: JWT令牌
            product_data: 商品数据
            
        Returns:
            API响应
        """
        try:
            # 验证令牌
            payload = self.auth_manager.verify_token(token)
            if not payload:
                return {
                    'status': 'error',
                    'message': '无效的访问令牌',
                    'code': 'INVALID_TOKEN'
                }
            
            user_id = payload['user_id']
            
            # 检查权限
            if not self.permission_manager.has_permission('admin', 'product:create'):
                return {
                    'status': 'error',
                    'message': '权限不足',
                    'code': 'PERMISSION_DENIED'
                }
            
            # 创建商品
            result = self.product_service.create_product(
                name=product_data.get('name', ''),
                description=product_data.get('description', ''),
                price=product_data.get('price', 0.0),
                category=ProductCategory(product_data.get('category', 'electronics')),
                sku=product_data.get('sku', ''),
                stock_quantity=product_data.get('stock_quantity', 0),
                brand=product_data.get('brand'),
                weight=product_data.get('weight'),
                dimensions=product_data.get('dimensions')
            )
            
            if result['success']:
                return {
                    'status': 'success',
                    'message': '商品创建成功',
                    'data': {'product': result['product']}
                }
            else:
                return {
                    'status': 'error',
                    'message': result['error'],
                    'code': 'CREATE_PRODUCT_FAILED'
                }
                
        except Exception as e:
            return {
                'status': 'error',
                'message': '服务器内部错误',
                'code': 'INTERNAL_ERROR'
            }
    
    def get_product(self, product_id: int) -> Dict[str, Any]:
        """
        获取商品详情API
        
        Args:
            product_id: 商品ID
            
        Returns:
            API响应
        """
        try:
            product = self.product_service.get_product_by_id(product_id)
            
            if product:
                return {
                    'status': 'success',
                    'message': '获取商品详情成功',
                    'data': {'product': product}
                }
            else:
                return {
                    'status': 'error',
                    'message': '商品不存在',
                    'code': 'PRODUCT_NOT_FOUND'
                }
                
        except Exception as e:
            return {
                'status': 'error',
                'message': '服务器内部错误',
                'code': 'INTERNAL_ERROR'
            }
    
    def update_product(self, token: str, product_id: int, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        更新商品信息API
        
        Args:
            token: JWT令牌
            product_id: 商品ID
            update_data: 更新数据
            
        Returns:
            API响应
        """
        try:
            # 验证令牌
            payload = self.auth_manager.verify_token(token)
            if not payload:
                return {
                    'status': 'error',
                    'message': '无效的访问令牌',
                    'code': 'INVALID_TOKEN'
                }
            
            user_id = payload['user_id']
            
            # 检查权限
            if not self.permission_manager.has_permission('admin', 'product:update'):
                return {
                    'status': 'error',
                    'message': '权限不足',
                    'code': 'PERMISSION_DENIED'
                }
            
            # 更新商品
            result = self.product_service.update_product(product_id, update_data)
            
            if result['success']:
                return {
                    'status': 'success',
                    'message': '商品信息更新成功',
                    'data': {'product': result['product']}
                }
            else:
                return {
                    'status': 'error',
                    'message': result['error'],
                    'code': 'UPDATE_PRODUCT_FAILED'
                }
                
        except Exception as e:
            return {
                'status': 'error',
                'message': '服务器内部错误',
                'code': 'INTERNAL_ERROR'
            }
    
    def delete_product(self, token: str, product_id: int) -> Dict[str, Any]:
        """
        删除商品API
        
        Args:
            token: JWT令牌
            product_id: 商品ID
            
        Returns:
            API响应
        """
        try:
            # 验证令牌
            payload = self.auth_manager.verify_token(token)
            if not payload:
                return {
                    'status': 'error',
                    'message': '无效的访问令牌',
                    'code': 'INVALID_TOKEN'
                }
            
            user_id = payload['user_id']
            
            # 检查权限
            if not self.permission_manager.has_permission('admin', 'product:delete'):
                return {
                    'status': 'error',
                    'message': '权限不足',
                    'code': 'PERMISSION_DENIED'
                }
            
            # 删除商品
            result = self.product_service.delete_product(product_id)
            
            if result['success']:
                return {
                    'status': 'success',
                    'message': result['message']
                }
            else:
                return {
                    'status': 'error',
                    'message': result['error'],
                    'code': 'DELETE_PRODUCT_FAILED'
                }
                
        except Exception as e:
            return {
                'status': 'error',
                'message': '服务器内部错误',
                'code': 'INTERNAL_ERROR'
            }
    
    def get_products(self, page: int = 1, per_page: int = 20, category: str = None) -> Dict[str, Any]:
        """
        获取商品列表API
        
        Args:
            page: 页码
            per_page: 每页数量
            category: 商品分类
            
        Returns:
            API响应
        """
        try:
            if category:
                # 按分类获取商品
                try:
                    product_category = ProductCategory(category)
                    products = self.product_service.get_products_by_category(product_category)
                    
                    return {
                        'status': 'success',
                        'message': '获取商品列表成功',
                        'data': {
                            'products': products,
                            'total': len(products),
                            'page': 1,
                            'per_page': len(products),
                            'category': category
                        }
                    }
                except ValueError:
                    return {
                        'status': 'error',
                        'message': '无效的商品分类',
                        'code': 'INVALID_CATEGORY'
                    }
            else:
                # 获取所有商品
                result = self.product_service.get_all_products(page, per_page)
                
                if result['success']:
                    return {
                        'status': 'success',
                        'message': '获取商品列表成功',
                        'data': {
                            'products': result['products'],
                            'total': result['total'],
                            'page': result['page'],
                            'per_page': result['per_page']
                        }
                    }
                else:
                    return {
                        'status': 'error',
                        'message': result['error'],
                        'code': 'GET_PRODUCTS_FAILED'
                    }
                
        except Exception as e:
            return {
                'status': 'error',
                'message': '服务器内部错误',
                'code': 'INTERNAL_ERROR'
            }
    
    def get_available_products(self) -> Dict[str, Any]:
        """
        获取可用商品列表API
        
        Returns:
            API响应
        """
        try:
            products = self.product_service.get_available_products()
            
            return {
                'status': 'success',
                'message': '获取可用商品列表成功',
                'data': {
                    'products': products,
                    'total': len(products)
                }
            }
                
        except Exception as e:
            return {
                'status': 'error',
                'message': '服务器内部错误',
                'code': 'INTERNAL_ERROR'
            }
    
    def search_products(self, keyword: str) -> Dict[str, Any]:
        """
        搜索商品API
        
        Args:
            keyword: 搜索关键词
            
        Returns:
            API响应
        """
        try:
            products = self.product_service.search_products(keyword)
            
            return {
                'status': 'success',
                'message': '搜索商品成功',
                'data': {
                    'products': products,
                    'total': len(products),
                    'keyword': keyword
                }
            }
                
        except Exception as e:
            return {
                'status': 'error',
                'message': '服务器内部错误',
                'code': 'INTERNAL_ERROR'
            }
    
    def update_stock(self, token: str, product_id: int, quantity_change: int) -> Dict[str, Any]:
        """
        更新商品库存API
        
        Args:
            token: JWT令牌
            product_id: 商品ID
            quantity_change: 数量变化
            
        Returns:
            API响应
        """
        try:
            # 验证令牌
            payload = self.auth_manager.verify_token(token)
            if not payload:
                return {
                    'status': 'error',
                    'message': '无效的访问令牌',
                    'code': 'INVALID_TOKEN'
                }
            
            user_id = payload['user_id']
            
            # 检查权限
            if not self.permission_manager.has_permission('admin', 'product:update'):
                return {
                    'status': 'error',
                    'message': '权限不足',
                    'code': 'PERMISSION_DENIED'
                }
            
            # 更新库存
            result = self.product_service.update_stock(product_id, quantity_change)
            
            if result['success']:
                return {
                    'status': 'success',
                    'message': result['message'],
                    'data': {
                        'product': result['product'],
                        'stock_quantity': result['product']['stock_quantity']
                    }
                }
            else:
                return {
                    'status': 'error',
                    'message': result['error'],
                    'code': 'UPDATE_STOCK_FAILED'
                }
                
        except Exception as e:
            return {
                'status': 'error',
                'message': '服务器内部错误',
                'code': 'INTERNAL_ERROR'
            }
    
    def add_product_tag(self, token: str, product_id: int, tag: str) -> Dict[str, Any]:
        """
        添加商品标签API
        
        Args:
            token: JWT令牌
            product_id: 商品ID
            tag: 标签
            
        Returns:
            API响应
        """
        try:
            # 验证令牌
            payload = self.auth_manager.verify_token(token)
            if not payload:
                return {
                    'status': 'error',
                    'message': '无效的访问令牌',
                    'code': 'INVALID_TOKEN'
                }
            
            user_id = payload['user_id']
            
            # 检查权限
            if not self.permission_manager.has_permission('admin', 'product:update'):
                return {
                    'status': 'error',
                    'message': '权限不足',
                    'code': 'PERMISSION_DENIED'
                }
            
            # 添加标签
            result = self.product_service.add_product_tag(product_id, tag)
            
            if result['success']:
                return {
                    'status': 'success',
                    'message': result['message'],
                    'data': {'tags': result['tags']}
                }
            else:
                return {
                    'status': 'error',
                    'message': result['error'],
                    'code': 'ADD_TAG_FAILED'
                }
                
        except Exception as e:
            return {
                'status': 'error',
                'message': '服务器内部错误',
                'code': 'INTERNAL_ERROR'
            }
    
    def get_low_stock_products(self, token: str, threshold: int = 10) -> Dict[str, Any]:
        """
        获取库存不足商品API
        
        Args:
            token: JWT令牌
            threshold: 库存阈值
            
        Returns:
            API响应
        """
        try:
            # 验证令牌
            payload = self.auth_manager.verify_token(token)
            if not payload:
                return {
                    'status': 'error',
                    'message': '无效的访问令牌',
                    'code': 'INVALID_TOKEN'
                }
            
            user_id = payload['user_id']
            
            # 检查权限
            if not self.permission_manager.has_permission('admin', 'product:read'):
                return {
                    'status': 'error',
                    'message': '权限不足',
                    'code': 'PERMISSION_DENIED'
                }
            
            # 获取库存不足商品
            products = self.product_service.get_low_stock_products(threshold)
            
            return {
                'status': 'success',
                'message': '获取库存不足商品成功',
                'data': {
                    'products': products,
                    'total': len(products),
                    'threshold': threshold
                }
            }
                
        except Exception as e:
            return {
                'status': 'error',
                'message': '服务器内部错误',
                'code': 'INTERNAL_ERROR'
            }