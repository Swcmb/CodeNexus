# 示例项目 - 电商系统

这是一个简单的电商系统示例，用于演示codenexus的代码分析功能。

## 项目结构

```
sample_project/
├── src/
│   ├── models/
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── product.py
│   │   └── order.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── user_service.py
│   │   ├── product_service.py
│   │   └── order_service.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── user_api.py
│   │   └── product_api.py
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── database.py
│   │   └── auth.py
│   └── main.py
├── tests/
│   ├── test_user_service.py
│   └── test_order_service.py
└── requirements.txt
```

## 功能模块

1. **用户管理** - 用户注册、登录、认证
2. **商品管理** - 商品信息管理、库存管理
3. **订单管理** - 订单创建、状态管理
4. **数据库工具** - 数据库连接和操作
5. **认证工具** - JWT令牌生成和验证

## 运行方式

```bash
# 安装依赖
pip install -r requirements.txt

# 运行应用
python src/main.py
```

## 使用codenexus分析

```bash
# 解析整个项目
python -m codenexus parse . --output ./analysis

# 查看知识图谱信息
python -m codenexus graph info

# 生成文档
python -m codenexus docs --output ./docs

# 分析影响
python -m codenexus analyze --file src/services/order_service.py --change "添加支付功能"
```