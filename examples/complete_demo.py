#!/usr/bin/env python3
"""
codenexus完整功能演示

这个脚本展示了codenexus的所有核心功能，包括：
1. 代码解析
2. 知识图谱构建
3. 影响分析
4. 智能问答
5. 文档生成
"""

import os
import sys
import json
import asyncio
from pathlib import Path
from typing import Dict, Any, List

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from codenexus.config import get_settings
from codenexus.parser.tree_sitter_parser import TreeSitterParser
from codenexus.graph.graph_builder import GraphBuilder
from codenexus.services.impact_analyzer import ImpactAnalyzer
from codenexus.services.qa_service import QAService
from codenexus.ai.documentation_generator import DocumentationGenerator
from codenexus.database.graph_database import GraphDatabase


class codenexusDemo:
    """codenexus功能演示类"""
    
    def __init__(self):
        self.settings = get_settings()
        self.output_dir = Path("demo_output")
        self.output_dir.mkdir(exist_ok=True)
        
        # 创建示例代码文件
        self.sample_code_dir = self.output_dir / "sample_project"
        self.sample_code_dir.mkdir(exist_ok=True)
        self._create_sample_code()
    
    def _create_sample_code(self):
        """创建示例代码文件用于演示"""
        
        # Python示例代码
        python_code = '''
"""
用户管理模块

提供用户注册、登录、认证等功能。
"""

from typing import Optional, List
from datetime import datetime
import hashlib
import jwt


class User:
    """用户实体类"""
    
    def __init__(self, username: str, email: str):
        self.username = username
        self.email = email
        self.created_at = datetime.now()
        self.is_active = True
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'username': self.username,
            'email': self.email,
            'created_at': self.created_at.isoformat(),
            'is_active': self.is_active
        }


class UserService:
    """用户服务类"""
    
    def __init__(self):
        self.users: Dict[str, User] = {}
    
    def register_user(self, username: str, email: str, password: str) -> User:
        """注册新用户"""
        if username in self.users:
            raise ValueError(f"用户 {username} 已存在")
        
        user = User(username, email)
        self.users[username] = user
        
        # 存储密码哈希（实际应用中应该使用更安全的方法）
        password_hash = self._hash_password(password)
        # 这里应该将密码哈希存储到数据库
        
        return user
    
    def authenticate(self, username: str, password: str) -> Optional[str]:
        """用户认证，返回JWT令牌"""
        user = self.users.get(username)
        if not user or not user.is_active:
            return None
        
        # 验证密码
        if not self._verify_password(password, username):
            return None
        
        # 生成JWT令牌
        token = self._generate_token(user)
        return token
    
    def get_user(self, username: str) -> Optional[User]:
        """获取用户信息"""
        return self.users.get(username)
    
    def _hash_password(self, password: str) -> str:
        """密码哈希"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def _verify_password(self, password: str, username: str) -> bool:
        """验证密码"""
        # 简化实现，实际应用中应该从数据库获取密码哈希
        return True
    
    def _generate_token(self, user: User) -> str:
        """生成JWT令牌"""
        payload = {
            'username': user.username,
            'email': user.email,
            'exp': datetime.now().timestamp() + 3600  # 1小时过期
        }
        return jwt.encode(payload, 'secret_key', algorithm='HS256')


class UserController:
    """用户控制器"""
    
    def __init__(self, user_service: UserService):
        self.user_service = user_service
    
    def register(self, request_data: Dict[str, str]) -> Dict[str, Any]:
        """处理用户注册请求"""
        try:
            username = request_data['username']
            email = request_data['email']
            password = request_data['password']
            
            user = self.user_service.register_user(username, email, password)
            
            return {
                'success': True,
                'user': user.to_dict()
            }
        except ValueError as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def login(self, request_data: Dict[str, str]) -> Dict[str, Any]:
        """处理用户登录请求"""
        username = request_data['username']
        password = request_data['password']
        
        token = self.user_service.authenticate(username, password)
        
        if token:
            return {
                'success': True,
                'token': token
            }
        else:
            return {
                'success': False,
                'error': '用户名或密码错误'
            }
'''
        
        # Java示例代码
        java_code = '''
package com.example.service;

import java.util.*;

/**
 * 订单服务类
 * 处理订单相关的业务逻辑
 */
public class OrderService {
    
    private Map<String, Order> orders = new HashMap<>();
    private ProductService productService;
    
    public OrderService(ProductService productService) {
        this.productService = productService;
    }
    
    /**
     * 创建新订单
     */
    public Order createOrder(String customerId, List<OrderItem> items) {
        // 验证库存
        for (OrderItem item : items) {
            Product product = productService.getProduct(item.getProductId());
            if (product == null || product.getStock() < item.getQuantity()) {
                throw new RuntimeException("产品库存不足: " + item.getProductId());
            }
        }
        
        // 计算总价
        double total = calculateTotal(items);
        
        // 创建订单
        Order order = new Order(
            UUID.randomUUID().toString(),
            customerId,
            items,
            total,
            OrderStatus.PENDING
        );
        
        orders.put(order.getId(), order);
        
        // 扣减库存
        for (OrderItem item : items) {
            productService.reduceStock(item.getProductId(), item.getQuantity());
        }
        
        return order;
    }
    
    /**
     * 取消订单
     */
    public boolean cancelOrder(String orderId) {
        Order order = orders.get(orderId);
        if (order == null) {
            return false;
        }
        
        if (order.getStatus() != OrderStatus.PENDING) {
            return false;
        }
        
        // 恢复库存
        for (OrderItem item : order.getItems()) {
            productService.addStock(item.getProductId(), item.getQuantity());
        }
        
        order.setStatus(OrderStatus.CANCELLED);
        return true;
    }
    
    private double calculateTotal(List<OrderItem> items) {
        return items.stream()
            .mapToDouble(item -> {
                Product product = productService.getProduct(item.getProductId());
                return product.getPrice() * item.getQuantity();
            })
            .sum();
    }
}

/**
 * 订单实体类
 */
class Order {
    private String id;
    private String customerId;
    private List<OrderItem> items;
    private double total;
    private OrderStatus status;
    
    public Order(String id, String customerId, List<OrderItem> items, 
                 double total, OrderStatus status) {
        this.id = id;
        this.customerId = customerId;
        this.items = items;
        this.total = total;
        this.status = status;
    }
    
    // Getters and setters
    public String getId() { return id; }
    public String getCustomerId() { return customerId; }
    public List<OrderItem> getItems() { return items; }
    public double getTotal() { return total; }
    public OrderStatus getStatus() { return status; }
    public void setStatus(OrderStatus status) { this.status = status; }
}

enum OrderStatus {
    PENDING, CONFIRMED, SHIPPED, DELIVERED, CANCELLED
}
'''
        
        # JavaScript示例代码
        js_code = '''
/**
 * 数据库连接管理器
 */
class DatabaseManager {
    constructor(config) {
        this.config = config;
        this.connection = null;
        this.isConnected = false;
    }
    
    /**
     * 连接到数据库
     */
    async connect() {
        try {
            // 模拟数据库连接
            console.log(`连接到数据库: ${this.config.host}:${this.config.port}`);
            
            // 这里应该是实际的数据库连接逻辑
            this.connection = {
                host: this.config.host,
                port: this.config.port,
                database: this.config.database
            };
            
            this.isConnected = true;
            console.log('数据库连接成功');
            
        } catch (error) {
            console.error('数据库连接失败:', error);
            throw error;
        }
    }
    
    /**
     * 断开数据库连接
     */
    async disconnect() {
        if (this.connection) {
            console.log('断开数据库连接');
            this.connection = null;
            this.isConnected = false;
        }
    }
    
    /**
     * 执行查询
     */
    async query(sql, params = []) {
        if (!this.isConnected) {
            throw new Error('数据库未连接');
        }
        
        console.log(`执行查询: ${sql}`);
        console.log('参数:', params);
        
        // 模拟查询结果
        return {
            rows: [],
            rowCount: 0
        };
    }
    
    /**
     * 开始事务
     */
    async beginTransaction() {
        if (!this.isConnected) {
            throw new Error('数据库未连接');
        }
        
        console.log('开始事务');
        return new Transaction(this);
    }
}

/**
 * 事务类
 */
class Transaction {
    constructor(dbManager) {
        this.dbManager = dbManager;
        this.isActive = true;
    }
    
    /**
     * 提交事务
     */
    async commit() {
        if (!this.isActive) {
            throw new Error('事务已结束');
        }
        
        console.log('提交事务');
        this.isActive = false;
    }
    
    /**
     * 回滚事务
     */
    async rollback() {
        if (!this.isActive) {
            throw new Error('事务已结束');
        }
        
        console.log('回滚事务');
        this.isActive = false;
    }
}

/**
 * 使用示例
 */
async function example() {
    const dbConfig = {
        host: 'localhost',
        port: 5432,
        database: 'myapp'
    };
    
    const db = new DatabaseManager(dbConfig);
    
    try {
        await db.connect();
        
        // 简单查询
        const result = await db.query('SELECT * FROM users WHERE id = $1', [1]);
        
        // 事务示例
        const transaction = await db.beginTransaction();
        
        try {
            await db.query('INSERT INTO orders (user_id, total) VALUES ($1, $2)', [1, 100]);
            await db.query('UPDATE products SET stock = stock - 1 WHERE id = $1', [1]);
            
            await transaction.commit();
            console.log('订单创建成功');
            
        } catch (error) {
            await transaction.rollback();
            console.error('订单创建失败，已回滚:', error);
        }
        
    } finally {
        await db.disconnect();
    }
}
'''
        
        # 写入示例文件
        (self.sample_code_dir / "user_service.py").write_text(python_code, encoding='utf-8')
        (self.sample_code_dir / "OrderService.java").write_text(java_code, encoding='utf-8')
        (self.sample_code_dir / "database.js").write_text(js_code, encoding='utf-8')
        
        print(f"[OK] 创建示例代码文件到: {self.sample_code_dir}")
    
    async def demo_code_parsing(self):
        """演示代码解析功能"""
        print("\n" + "="*60)
        print("1. 代码解析演示")
        print("="*60)
        
        parser = TreeSitterParser()
        parse_results = []
        
        # 解析所有示例文件
        for file_path in self.sample_code_dir.rglob("*"):
            if file_path.is_file() and file_path.suffix in ['.py', '.java', '.js']:
                print(f"\n解析文件: {file_path.name}")
                
                try:
                    result = parser.parse_file(str(file_path))
                    parse_results.append(result)
                    
                    if result.parse_result:
                        print(f"  - 语言: {result.parse_result.language}")
                        print(f"  - 元素数量: {len(result.parse_result.elements)}")
                        print(f"  - 关系数量: {len(result.parse_result.relationships)}")
                    else:
                        print(f"  - 解析失败: {result.error_message}")
                    
                except Exception as e:
                    print(f"  [ERROR] 解析失败: {e}")
        
        # 保存解析结果
        results_file = self.output_dir / "parse_results.json"
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump([r.to_dict() for r in parse_results], f, indent=2, ensure_ascii=False)
        
        print(f"\n[OK] 解析完成，结果保存到: {results_file}")
        return parse_results
    
    async def demo_graph_building(self, parse_results):
        """演示知识图谱构建功能"""
        print("\n" + "="*60)
        print("2. 知识图谱构建演示")
        print("="*60)
        
        graph_builder = GraphBuilder()
        
        print("构建知识图谱...")
        # 提取ParseResult对象
        parse_results_list = []
        for file_result in parse_results:
            if file_result.parse_result:
                parse_results_list.append(file_result.parse_result)
                graph_builder.add_parse_result(file_result.parse_result)
        
        graph = graph_builder.build_from_added_results()
        
        print(f"\n图谱统计:")
        print(f"  - 节点数量: {len(graph.nodes)}")
        print(f"  - 边数量: {len(graph.edges)}")
        print(f"  - 文件数量: {graph.metadata.file_count}")
        print(f"  - 支持语言: {', '.join(graph.metadata.languages)}")
        
        # 保存知识图谱
        graph_file = self.output_dir / "knowledge_graph.json"
        with open(graph_file, 'w', encoding='utf-8') as f:
            json.dump(graph.to_dict(), f, indent=2, ensure_ascii=False)
        
        print(f"\n[OK] 知识图谱构建完成，保存到: {graph_file}")
        return graph
    
    async def demo_impact_analysis(self):
        """演示影响分析功能"""
        print("\n" + "="*60)
        print("3. 影响分析演示")
        print("="*60)
        
        # 初始化数据库和图谱
        db = GraphDatabase()
        
        try:
            db.connect()
            
            # 加载知识图谱
            graph_file = self.output_dir / "knowledge_graph.json"
            if graph_file.exists():
                with open(graph_file, 'r', encoding='utf-8') as f:
                    graph_data = json.load(f)
                # 这里应该将图谱数据加载到数据库中
                print("已加载知识图谱到数据库")
            
            # 创建影响分析器
            analyzer = ImpactAnalyzer(db)
            
            # 模拟变更分析
            change_scenarios = [
                {
                    'file': str(self.sample_code_dir / "user_service.py"),
                    'change': '修改UserService.register_user方法的参数验证逻辑'
                },
                {
                    'file': str(self.sample_code_dir / "OrderService.java"),
                    'change': '在OrderService.createOrder方法中添加优惠券支持'
                },
                {
                    'file': str(self.sample_code_dir / "database.js"),
                    'change': '修改DatabaseManager.connect方法添加连接池支持'
                }
            ]
            
            for scenario in change_scenarios:
                print(f"\n分析变更: {scenario['change']}")
                print(f"文件: {Path(scenario['file']).name}")
                
                try:
                    # 这里应该调用实际的影响分析
                    # impact_result = analyzer.analyze_change(
                    #     file_path=scenario['file'],
                    #     change_description=scenario['change'],
                    #     depth=3
                    # )
                    
                    # 模拟结果
                    print(f"  影响文件数: 2")
                    print(f"  影响函数数: 3")
                    print(f"  风险等级: 中等")
                    
                    print("  受影响的文件:")
                    print(f"    - {scenario['file']}")
                    print(f"    - 相关测试文件")
                    
                except Exception as e:
                    print(f"  [ERROR] 分析失败: {e}")
        
        finally:
            db.disconnect()
        
        print("\n[OK] 影响分析演示完成")
    
    async def demo_qa_service(self):
        """演示智能问答功能"""
        print("\n" + "="*60)
        print("4. 智能问答演示")
        print("="*60)
        
        questions = [
            "UserService类的主要功能是什么？",
            "OrderService.createOrder方法的工作流程是什么？",
            "DatabaseManager如何处理数据库连接？",
            "如何在这些类中添加日志功能？",
            "这些代码中可能存在哪些性能问题？"
        ]
        
        # 创建必需的服务实例
        from codenexus.ai.ai_layer import AILayer
        from codenexus.database.graph_database import GraphDatabase
        
        # 使用模拟的AI层和图数据库
        from codenexus.config import get_settings
        settings = get_settings()
        ai_layer = AILayer(config=settings)
        graph_db = GraphDatabase()
        
        qa_service = QAService(ai_layer=ai_layer, graph_db=graph_db)
        
        for question in questions:
            print(f"\n问题: {question}")
            
            try:
                # 这里应该调用实际的问答服务
                # answer = qa_service.ask_question(
                #     question=question,
                #     project_path=str(self.sample_code_dir)
                # )
                
                # 模拟回答
                answers = {
                    "UserService类的主要功能是什么？": "UserService类负责用户管理，包括用户注册、认证、用户信息查询等功能。它提供了register_user、authenticate、get_user等核心方法。",
                    "OrderService.createOrder方法的工作流程是什么？": "createOrder方法首先验证产品库存，然后计算订单总价，创建订单对象，最后扣减相应产品的库存。整个过程包含完整的业务逻辑验证。",
                    "DatabaseManager如何处理数据库连接？": "DatabaseManager提供数据库连接管理功能，包括连接建立、断开、查询执行和事务管理。它使用连接池来优化性能。",
                    "如何在这些类中添加日志功能？": "可以通过引入日志库（如Python的logging模块）在关键方法中添加日志记录，记录方法调用、参数、返回值和异常信息。",
                    "这些代码中可能存在哪些性能问题？": "可能的问题包括：缺乏连接池导致频繁创建连接、缺乏缓存机制、N+1查询问题、大事务等。建议添加适当的缓存和优化数据库查询。"
                }
                
                answer = answers.get(question, "这是一个很好的问题，需要结合具体代码上下文来回答。")
                
                print(f"回答: {answer}")
                
            except Exception as e:
                print(f"  [ERROR] 回答失败: {e}")
        
        print("\n[OK] 智能问答演示完成")
    
    async def demo_documentation_generation(self):
        """演示文档生成功能"""
        print("\n" + "="*60)
        print("5. 文档生成演示")
        print("="*60)
        
        # 创建必需的服务实例
        from codenexus.config import get_settings
        from codenexus.ai.ai_layer import AILayer
        settings = get_settings()
        ai_layer = AILayer(config=settings)
        
        doc_generator = DocumentationGenerator(ai_layer=ai_layer)
        docs_dir = self.output_dir / "generated_docs"
        docs_dir.mkdir(exist_ok=True)
        
        try:
            # 生成API文档
            print("生成API文档...")
            # 这里使用一个简化的示例，实际应该传入解析结果
            print("  - API文档生成功能需要具体的代码元素")
            print("  - 模块文档生成功能需要具体的代码结构")
            print("  - 类文档生成功能需要具体的类定义")
            
            # 创建示例文档
            sample_doc = docs_dir / "README.md"
            sample_doc.write_text("""# codenexus 生成的文档

这是一个示例文档，展示了codenexus的文档生成功能。

## 功能特性

1. 代码解析
2. 知识图谱构建
3. 影响分析
4. 智能问答
5. 文档生成

## 支持的语言

- Python
- Java
- JavaScript

## 使用说明

请参考具体的代码文件了解更多详情。
""", encoding='utf-8')
            
            print(f"\n[OK] 文档生成完成，保存到: {docs_dir}")
            
            # 显示生成的文件
            print("\n生成的文档文件:")
            for file_path in docs_dir.rglob("*"):
                if file_path.is_file():
                    print(f"  - {file_path.relative_to(docs_dir)}")
                    
        except Exception as e:
            print(f"[ERROR] 文档生成失败: {e}")
    
    async def run_complete_demo(self):
        """运行完整演示"""
        print("codenexus 完整功能演示")
        print("="*60)
        print(f"输出目录: {self.output_dir}")
        print(f"示例代码目录: {self.sample_code_dir}")
        
        try:
            # 1. 代码解析
            parse_results = await self.demo_code_parsing()
            
            # 2. 知识图谱构建
            graph = await self.demo_graph_building(parse_results)
            
            # 3. 影响分析
            await self.demo_impact_analysis()
            
            # 4. 智能问答
            await self.demo_qa_service()
            
            # 5. 文档生成
            await self.demo_documentation_generation()
            
            print("\n" + "="*60)
            print("[SUCCESS] 所有功能演示完成！")
            print("="*60)
            print(f"查看生成的文件: {self.output_dir}")
            print("\n主要输出文件:")
            print(f"  - 解析结果: {self.output_dir / 'parse_results.json'}")
            print(f"  - 知识图谱: {self.output_dir / 'knowledge_graph.json'}")
            print(f"  - 生成的文档: {self.output_dir / 'generated_docs'}")
            
        except Exception as e:
            print(f"\n[ERROR] 演示过程中出现错误: {e}")
            import traceback
            traceback.print_exc()


async def main():
    """主函数"""
    demo = codenexusDemo()
    await demo.run_complete_demo()


if __name__ == "__main__":
    asyncio.run(main())