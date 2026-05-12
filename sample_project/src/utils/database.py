"""
数据库管理工具

提供数据库连接和操作的基础功能。
"""

import sqlite3
from typing import Optional, Dict, Any, List
from contextlib import contextmanager
import threading
import time


class DatabaseManager:
    """数据库管理器"""
    
    def __init__(self, database_path: str = "ecommerce.db"):
        self.database_path = database_path
        self._local = threading.local()
        self._initialize_database()
    
    def _initialize_database(self):
        """初始化数据库表结构"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # 创建用户表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username VARCHAR(50) UNIQUE NOT NULL,
                    email VARCHAR(100) UNIQUE NOT NULL,
                    password_hash VARCHAR(255) NOT NULL,
                    full_name VARCHAR(100),
                    phone VARCHAR(20),
                    is_active BOOLEAN DEFAULT TRUE,
                    is_admin BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP
                )
            ''')
            
            # 创建商品表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS products (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name VARCHAR(200) NOT NULL,
                    description TEXT,
                    price DECIMAL(10,2) NOT NULL,
                    category VARCHAR(50) NOT NULL,
                    status VARCHAR(20) DEFAULT 'active',
                    stock_quantity INTEGER DEFAULT 0,
                    sku VARCHAR(100) UNIQUE NOT NULL,
                    brand VARCHAR(100),
                    weight DECIMAL(8,2),
                    dimensions TEXT,  -- JSON格式存储
                    images TEXT,      -- JSON格式存储
                    tags TEXT,        -- JSON格式存储
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 创建订单表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    order_number VARCHAR(100) UNIQUE NOT NULL,
                    user_id INTEGER NOT NULL,
                    status VARCHAR(20) DEFAULT 'pending',
                    payment_status VARCHAR(20) DEFAULT 'pending',
                    subtotal DECIMAL(10,2) NOT NULL,
                    tax_amount DECIMAL(10,2) DEFAULT 0,
                    shipping_cost DECIMAL(10,2) DEFAULT 0,
                    discount_amount DECIMAL(10,2) DEFAULT 0,
                    total_amount DECIMAL(10,2) NOT NULL,
                    currency VARCHAR(10) DEFAULT 'CNY',
                    shipping_address TEXT,  -- JSON格式存储
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    shipped_at TIMESTAMP,
                    delivered_at TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            ''')
            
            # 创建订单项表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS order_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    order_id INTEGER NOT NULL,
                    product_id INTEGER NOT NULL,
                    product_name VARCHAR(200) NOT NULL,
                    product_sku VARCHAR(100) NOT NULL,
                    quantity INTEGER NOT NULL,
                    unit_price DECIMAL(10,2) NOT NULL,
                    total_price DECIMAL(10,2) NOT NULL,
                    FOREIGN KEY (order_id) REFERENCES orders (id)
                )
            ''')
            
            # 创建索引
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_products_sku ON products(sku)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_products_category ON products(category)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_orders_user_id ON orders(user_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_orders_order_number ON orders(order_number)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status)')
            
            conn.commit()
    
    @contextmanager
    def get_connection(self):
        """获取数据库连接的上下文管理器"""
        if not hasattr(self._local, 'connection'):
            self._local.connection = sqlite3.connect(
                self.database_path,
                check_same_thread=False
            )
            self._local.connection.row_factory = sqlite3.Row  # 使结果可以按列名访问
        
        try:
            yield self._local.connection
        except Exception:
            self._local.connection.rollback()
            raise
        finally:
            # 不关闭连接，保持线程本地连接
            pass
    
    def execute_query(self, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """执行查询语句"""
        with self.get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    
    def execute_update(self, query: str, params: tuple = ()) -> int:
        """执行更新语句"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            return cursor.rowcount
    
    def execute_insert(self, query: str, params: tuple = ()) -> int:
        """执行插入语句，返回新插入的ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            return cursor.lastrowid
    
    def execute_scalar(self, query: str, params: tuple = ()) -> Any:
        """执行查询并返回单个值"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return cursor.fetchone()[0]
    
    def begin_transaction(self):
        """开始事务"""
        with self.get_connection() as conn:
            conn.execute("BEGIN")
    
    def commit_transaction(self):
        """提交事务"""
        with self.get_connection() as conn:
            conn.commit()
    
    def rollback_transaction(self):
        """回滚事务"""
        with self.get_connection() as conn:
            conn.rollback()
    
    def table_exists(self, table_name: str) -> bool:
        """检查表是否存在"""
        query = '''
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name=?
        '''
        result = self.execute_query(query, (table_name,))
        return len(result) > 0
    
    def get_table_info(self, table_name: str) -> List[Dict[str, Any]]:
        """获取表结构信息"""
        query = f"PRAGMA table_info({table_name})"
        return self.execute_query(query)
    
    def backup_database(self, backup_path: str) -> bool:
        """备份数据库"""
        try:
            source = sqlite3.connect(self.database_path)
            backup = sqlite3.connect(backup_path)
            source.backup(backup)
            source.close()
            backup.close()
            return True
        except Exception:
            return False
    
    def get_database_size(self) -> int:
        """获取数据库文件大小（字节）"""
        import os
        try:
            return os.path.getsize(self.database_path)
        except OSError:
            return 0
    
    def get_table_count(self, table_name: str) -> int:
        """获取表的记录数"""
        try:
            return self.execute_scalar(f"SELECT COUNT(*) FROM {table_name}")
        except Exception:
            return 0
    
    def health_check(self) -> Dict[str, Any]:
        """数据库健康检查"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                cursor.fetchone()
            
            # 获取统计信息
            stats = {
                'connection_status': 'healthy',
                'database_size': self.get_database_size(),
                'tables': {}
            }
            
            # 检查主要表的记录数
            tables = ['users', 'products', 'orders', 'order_items']
            for table in tables:
                if self.table_exists(table):
                    stats['tables'][table] = self.get_table_count(table)
            
            return stats
            
        except Exception as e:
            return {
                'connection_status': 'unhealthy',
                'error': str(e)
            }
    
    def close(self):
        """关闭数据库连接"""
        if hasattr(self._local, 'connection'):
            self._local.connection.close()
            delattr(self._local, 'connection')


class DatabasePool:
    """数据库连接池（简化版）"""
    
    def __init__(self, database_path: str, max_connections: int = 10):
        self.database_path = database_path
        self.max_connections = max_connections
        self._pool = []
        self._lock = threading.Lock()
        self._created_connections = 0
    
    def get_connection(self) -> sqlite3.Connection:
        """从连接池获取连接"""
        with self._lock:
            if self._pool:
                return self._pool.pop()
            elif self._created_connections < self.max_connections:
                self._created_connections += 1
                conn = sqlite3.connect(self.database_path, check_same_thread=False)
                conn.row_factory = sqlite3.Row
                return conn
            else:
                # 等待可用连接
                while not self._pool:
                    time.sleep(0.1)
                return self._pool.pop()
    
    def return_connection(self, conn: sqlite3.Connection):
        """将连接返回到连接池"""
        with self._lock:
            if len(self._pool) < self.max_connections:
                self._pool.append(conn)
            else:
                conn.close()
                self._created_connections -= 1
    
    def close_all(self):
        """关闭所有连接"""
        with self._lock:
            for conn in self._pool:
                conn.close()
            self._pool.clear()
            self._created_connections = 0


# 全局数据库管理器实例
db_manager = DatabaseManager()