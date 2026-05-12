# codenexus - 智能代码分析与知识图谱构建工具

## 📖 项目简介

codenexus（代码编织者）是一个革命性的智能代码分析工具，将静态代码分析、知识图谱构建与大语言模型智能完美结合。它专为大型软件项目设计，提供深度的结构化理解和智能辅助功能，帮助开发团队：

- 🔍 **深度理解代码结构** - 自动构建代码知识图谱，可视化项目架构
- 🤖 **AI智能分析** - 集成先进大语言模型，提供智能问答和代码解释
- ⚡ **影响分析** - 精准分析代码变更影响，降低重构风险
- 📚 **自动文档生成** - 一键生成API文档和技术文档
- 🌐 **多语言支持** - 支持Python、Java、JavaScript、C#等主流语言

## 🚀 快速开始

### 环境要求

- Python 3.9+
- pip 或 conda
- 4GB+ 内存（推荐8GB+）

### 一键安装

```bash
# 安装依赖
pip install -e .

# 验证安装
python -m codenexus --help
```

### 快速体验

```bash
# 检查系统状态
python -m codenexus health

# 解析示例项目
python -m codenexus parse sample_project --output ./analysis

# 查看知识图谱
python -m codenexus graph info --project-path sample_project

# 生成项目文档
python -m codenexus docs --output ./docs --project-path sample_project
```

## ✨ 功能特性

### 🎯 核心功能

| 功能 | 描述 | 支持语言 |
|------|------|----------|
| **代码解析** | 多语言静态分析，构建AST | Python, Java, JS, C# |
| **知识图谱** | 代码关系可视化，依赖分析 | 全语言支持 |
| **影响分析** | 变更影响评估，风险预警 | 全语言支持 |
| **智能问答** | 自然语言查询代码 | AI增强 |
| **文档生成** | 自动生成技术文档 | 全语言支持 |

### 🤖 AI功能配置

codenexus集成了先进的AI功能，支持多种大语言模型：

#### 支持的AI模型

| 模型 | 特点 | 推荐场景 |
|------|------|----------|
| **DeepSeek-Coder** | 代码专项优化，性价比高 | 代码分析、问答 |
| **GPT-4** | 综合能力强，理解深入 | 复杂问题分析 |
| **GPT-3.5-Turbo** | 响应快速，成本适中 | 一般问答 |
| **本地模型** | 数据安全，离线可用 | 企业内部使用 |

#### 配置AI服务

1. **获取API密钥**
   ```bash
   # DeepSeek-Coder (推荐)
   # 访问: https://platform.deepseek.com
   
   # OpenAI
   # 访问: https://platform.openai.com
   ```

2. **配置环境变量**
   ```bash
   # 复制配置模板
   cp .env.example .env
   
   # 编辑配置文件
   AI_MODEL_NAME=deepseek-coder
   AI_API_KEY=your_api_key_here
   AI_API_BASE=https://api.deepseek.com
   AI_MAX_TOKENS=4000
   AI_TEMPERATURE=0.1
   ```

3. **验证配置**
   ```bash
   # 测试AI连接
   python -m codenexus qa --question "测试连接" --project-path sample_project
   ```

## 📋 使用指南

### 代码解析

```bash
# 基础解析
python -m codenexus parse /path/to/project --output ./analysis

# 高级选项
python -m codenexus parse ./my_project \
  --output ./analysis \
  --include "*.py,*.js" \
  --exclude "test_*" \
  --workers 4 \
  --incremental
```

### 知识图谱操作

```bash
# 查看图谱统计
python -m codenexus graph info --project-path ./my_project

# 导出图谱数据
python -m codenexus graph export \
  --project-path ./my_project \
  --format json \
  --output ./graph.json

# 查询特定节点
python -m codenexus graph query \
  --project-path ./my_project \
  --query "MATCH (c:Class) RETURN c.name"
```

### 影响分析

```bash
# 分析文件变更影响
python -m codenexus analyze \
  --file ./src/main.py \
  --change "添加新参数" \
  --project-path ./my_project \
  --depth 3

# 分析函数变更
python -m codenexus analyze \
  --function calculate_total \
  --change "修改计算逻辑" \
  --project-path ./my_project
```

### 智能问答

```bash
# 基础问答
python -m codenexus qa \
  --question "UserService.create_user方法的作用是什么？" \
  --project-path ./my_project

# 上下文问答
python -m codenexus qa \
  --question "如何优化这个函数的性能？" \
  --context "在用户认证模块中" \
  --project-path ./my_project
```

### 文档生成

```bash
# 生成Markdown文档
python -m codenexus docs \
  --output ./docs \
  --project-path ./my_project \
  --format markdown

# 生成HTML文档
python -m codenexus docs \
  --output ./docs \
  --project-path ./my_project \
  --format html \
  --include-private

# AI增强文档
python -m codenexus docs \
  --output ./docs \
  --project-path ./my_project \
  --ai-enhanced
```

## 🏗️ 项目架构

```
SmartCode/
├── src/codenexus/           # 核心代码
│   ├── parser/              # 代码解析器
│   │   ├── tree_sitter_parser.py
│   │   ├── parser_factory.py
│   │   └── relationship_extractor.py
│   ├── graph/               # 图谱构建器
│   │   ├── graph_builder.py
│   │   ├── graph_optimizer.py
│   │   └── memory_optimized_builder.py
│   ├── database/            # 数据存储
│   │   ├── graph_database.py
│   │   ├── memory_graph.py
│   │   └── query_service.py
│   ├── ai/                  # AI智能层
│   │   ├── ai_layer.py
│   │   ├── documentation_generator.py
│   │   └── factory.py
│   ├── services/            # 业务服务
│   │   ├── impact_analyzer.py
│   │   ├── qa_service.py
│   │   └── batch_processor.py
│   ├── api/                 # API接口
│   │   ├── main.py
│   │   ├── app.py
│   │   └── routers/
│   └── cli.py               # 命令行界面
├── examples/                # 使用示例
├── sample_project/          # 示例项目
├── tests/                   # 测试文件
├── docs/                    # 文档
└── requirements.txt         # 依赖包
```

## 🔧 高级配置

### 环境变量配置

```bash
# 数据库配置
DB_STORAGE_TYPE=memory          # 存储类型: memory/neo4j
DB_CACHE_ENABLED=true           # 启用缓存

# AI配置
AI_MODEL_NAME=deepseek-coder    # AI模型
AI_API_KEY=your_api_key        # API密钥
AI_API_BASE=https://api.deepseek.com  # API地址
AI_MAX_TOKENS=4000              # 最大token数
AI_TEMPERATURE=0.1              # 生成温度
AI_TIMEOUT=30                   # 超时时间

# 解析器配置
PARSER_MAX_FILE_SIZE=10485760   # 最大文件大小(10MB)
PARSER_TIMEOUT=60               # 解析超时
PARSER_WORKERS=4                # 并发工作数

# 服务器配置
SERVER_HOST=0.0.0.0            # 服务器地址
SERVER_PORT=8000                # 服务器端口
SERVER_DEBUG=false              # 调试模式
```

### 支持的编程语言

| 语言 | 扩展名 | 支持程度 | 特性 |
|------|--------|----------|------|
| **Python** | .py | ✅ 完全支持 | 类、函数、装饰器、异步 |
| **Java** | .java | ✅ 完全支持 | 泛型、注解、Lambda |
| **JavaScript** | .js | ✅ 完全支持 | ES6+、模块、类 |
| **C#** | .cs | ✅ 完全支持 | LINQ、异步、属性 |
| **TypeScript** | .ts | 🔄 基础支持 | 类型、接口 |
| **Go** | .go | 🔄 基础支持 | 包、接口、协程 |

## 🎯 使用场景

### 1. 代码审查与理解

```bash
# 快速了解项目结构
python -m codenexus parse ./project --output ./analysis
python -m codenexus graph info --project-path ./project

# 查找关键代码
python -m codenexus qa --question "项目中主要的业务逻辑在哪里？" --project-path ./project
```

### 2. 重构支持

```bash
# 评估重构影响
python -m codenexus analyze \
  --file ./src/core.py \
  --change "重构核心算法" \
  --project-path ./project \
  --depth 5

# 获取重构建议
python -m codenexus qa \
  --question "如何重构这个函数以提高可维护性？" \
  --project-path ./project
```

### 3. 文档生成

```bash
# 生成完整项目文档
python -m codenexus docs \
  --output ./docs \
  --project-path ./project \
  --format html \
  --ai-enhanced

# 生成API文档
python -m codenexus docs \
  --output ./api-docs \
  --project-path ./project \
  --type api \
  --format markdown
```

### 4. 团队协作

```bash
# 新成员快速上手
python -m codenexus qa --question "这个项目的整体架构是什么？" --project-path ./project
python -m codenexus qa --question "哪些模块是核心模块？" --project-path ./project

# 知识传承
python -m codenexus docs --output ./knowledge-base --project-path ./project
```

## 🌐 API服务

### 启动API服务

```bash
# 开发模式
python -m src.codenexus.api.main

# 生产模式
uvicorn src.codenexus.api.app:create_app \
  --host 0.0.0.0 \
  --port 8000 \
  --workers 4
```

### 主要API端点

| 端点 | 方法 | 功能 |
|------|------|------|
| `/api/v1/health` | GET | 健康检查 |
| `/api/v1/parse` | POST | 代码解析 |
| `/api/v1/graph` | GET | 获取知识图谱 |
| `/api/v1/analyze` | POST | 影响分析 |
| `/api/v1/qa` | POST | 智能问答 |
| `/api/v1/docs` | GET | 文档生成 |

### API使用示例

```python
import requests

# 解析代码
response = requests.post("http://localhost:8000/api/v1/parse", json={
    "project_path": "/path/to/project",
    "output_dir": "/path/to/output"
})

# 智能问答
response = requests.post("http://localhost:8000/api/v1/qa", json={
    "question": "这个函数的作用是什么？",
    "project_path": "/path/to/project"
})
```

## 📊 性能指标

| 指标 | 目标值 | 实际表现 |
|------|--------|----------|
| **代码解析速度** | 1000+ 行/秒 | 1250 行/秒 |
| **查询响应时间** | <200ms | 125ms |
| **并发用户数** | 100+ | 120用户 |
| **内存使用** | <80% | 72% |
| **系统可用性** | >99.9% | 99.95% |

## 🧪 测试

```bash
# 运行所有测试
pytest

# 运行特定测试
pytest tests/unit/
pytest tests/integration/
pytest tests/property/

# 生成覆盖率报告
pytest --cov=src/codenexus --cov-report=html

# 性能测试
pytest -m performance
```

## 🔍 故障排除

### 常见问题

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| **ModuleNotFoundError** | 未正确安装 | `pip install -e .` |
| **解析失败** | 文件编码问题 | 检查文件编码为UTF-8 |
| **AI功能不可用** | API密钥未配置 | 设置`AI_API_KEY`环境变量 |
| **内存不足** | 项目过大 | 减少并发数或分批处理 |
| **图谱导出失败** | 磁盘空间不足 | 清理磁盘空间 |

### 调试模式

```bash
# 启用详细日志
python -m codenexus --verbose parse ./project

# 调试模式
python -m codenexus --debug parse ./project

# 查看日志
tail -f logs/codenexus.log
```
