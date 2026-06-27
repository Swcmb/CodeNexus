<div align="center">

# CodeNexus

**智能代码分析与知识图谱构建工具**

[Intelligent Code Analysis & Knowledge Graph Construction Tool]

![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-009688?logo=fastapi&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)
![CI](https://img.shields.io/badge/CI-GitHub%20Actions-2088FF?logo=githubactions&logoColor=white)
![Version](https://img.shields.io/badge/Version-0.1.0-blue)

[English](#english-overview) | [中文](#简介)

</div>

---

## 简介

CodeNexus 是一款面向开发团队的智能代码分析工具，将**静态代码分析**、**知识图谱**与**大语言模型**相结合，为大型软件项目提供深度的结构化理解和智能辅助能力。

### 核心能力

| 能力 | 说明 |
|:---|:---|
| **多语言代码解析** | 基于 tree-sitter 支持 Python、Java、JavaScript、C# 四种语言的 AST 解析 |
| **知识图谱构建** | 自动从代码中提取实体与关系，构建并优化知识图谱 |
| **影响分析** | 评估代码变更的影响范围和风险等级 |
| **智能问答** | 基于知识图谱和 AI 模型，回答关于项目代码的自然语言问题 |
| **自动文档生成** | 利用 AI 自动生成项目文档（Markdown / HTML） |
| **风险检测** | 识别代码中的潜在风险点 |
| **代码可视化** | 以图形方式展示代码结构与依赖关系 |
| **REST API + CLI** | 同时提供 HTTP API 和命令行两种使用方式 |
| **批量处理与缓存** | 支持大规模项目的高效处理 |
| **文件监听与增量更新** | 监听文件变更并自动更新知识图谱 |

---

## 快速开始

### 环境要求

- Python >= 3.9（推荐 3.11 或 3.12）
- 操作系统：Windows / macOS / Linux

### 安装

```bash
# 克隆仓库
git clone https://github.com/Swcmb/CodeNexus.git
cd CodeNexus

# 安装（可编辑模式）
pip install -e .

# 或同时安装开发依赖
pip install -e ".[dev]"
```

### 配置

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env，填入 AI API Key 等配置
# AI_API_KEY=your_api_key_here
# AI_API_BASE=https://api.deepseek.com
```

> **提示**：未配置 AI API Key 时，代码解析和知识图谱功能仍可正常使用，仅 AI 相关功能（智能问答、文档生成）不可用。

### 验证安装

```bash
# 检查系统组件状态
codenexus health
```

---

## 使用方式

### CLI 命令行

```bash
# 查看帮助
codenexus --help

# 1. 解析项目并构建知识图谱
codenexus parse -p /path/to/project -o ./output

# 2. 查看知识图谱信息
codenexus graph-info -p /path/to/project

# 3. 影响分析
codenexus analyze -f /path/to/file.py -c "重构了 UserService 的登录逻辑" -p /path/to/project

# 4. 智能问答（需配置 AI API Key）
codenexus qa -q "OrderService 类的核心职责是什么？" -p /path/to/project

# 5. 生成文档
codenexus docs -p /path/to/project -o ./docs -f markdown

# 6. 导出知识图谱
codenexus graph-export -p /path/to/project -o ./graph.json -f json
```

所有命令均支持 `--verbose` / `-v` 参数以显示详细日志。

### REST API

```bash
# 方式一：直接启动
python -m codenexus.api.main

# 方式二：通过 uvicorn 启动（支持热重载）
uvicorn codenexus.api.app:create_app --factory --reload
```

API 默认运行在 `http://localhost:8000`，启动后访问以下地址：

| 地址 | 说明 |
|:---|:---|
| `http://localhost:8000/docs` | Swagger UI 交互式文档 |
| `http://localhost:8000/redoc` | ReDoc 文档 |
| `http://localhost:8000/api/v1/health` | 健康检查端点 |

#### API 路由一览

| 前缀 | 模块 | 说明 |
|:---|:---|:---|
| `/api/v1/health` | health | 健康检查 |
| `/api/v1/parser` | parser | 代码解析 |
| `/api/v1/graph` | graph | 知识图谱操作 |
| `/api/v1/docs` | documentation | 文档生成 |
| `/api/v1/qa` | qa | 智能问答 |
| `/api/v1/risk` | risk | 风险检测 |
| `/api/v1/viz` | visualization | 可视化 |
| `/api/v1/backup` | backup | 备份恢复 |

### Docker 部署

```bash
# 配置环境变量
cp .env.example .env
# 编辑 .env 填入必要的配置

# 构建并启动
docker compose up -d

# 查看日志
docker compose logs -f

# 停止服务
docker compose down
```

---

## 项目架构

### 整体结构

```
+------------------------------------------------------------------+
|                        使用入口 (Entry Points)                     |
|         CLI (codenexus)           REST API (FastAPI)              |
+----------------------------------+-------------------------------+
                                   |
+------------------------------------------------------------------+
|                         服务层 (Services)                          |
|  ImpactAnalyzer | QAService | RiskDetection | CacheManager |     |
|  BatchProcessor | FileWatcher | IncrementalUpdater               |
+------------------------------------------------------------------+
                                   |
          +------------------------+------------------------+
          |                        |                        |
+---------v--------+    +---------v--------+    +----------v-------+
|   AI 层 (AI)     |    |  图谱层 (Graph)   |    |  解析层 (Parser)  |
|  AILayer         |    |  GraphBuilder    |    |  TreeSitterParser |
|  DocGenerator    |    |  GraphOptimizer  |    |  RelationshipExtr |
|  OpenAI API      |    |  MemoryOptBuilder|    |  CrossFileAnalyzer|
+---------+--------+    +---------+--------+    +----------+-------+
          |                        |                        |
+---------v--------+    +---------v--------+    +----------v-------+
|  数据库 (DB)      |    |  数据模型 (Models) |    |  工具层 (Utils)   |
|  GraphDatabase   |    |  CodeElement     |    |  Logger           |
|  MemoryGraph     |    |  CodeGraph       |    |  Monitoring       |
|  QueryService    |    |  Relationship    |    |  Scheduler        |
|  MockDatabase    |    |  ParseResult     |    |  ErrorHandler     |
+------------------+    +------------------+    |  BackupRecovery   |
                                                +------------------+
```

### 目录结构

```
CodeNexus/
├── src/codenexus/           # 核心源码
│   ├── ai/                  # AI 层 - LLM 集成与文档生成
│   │   ├── ai_layer.py      # AI 能力封装
│   │   ├── documentation_generator.py
│   │   ├── factory.py       # AI 服务工厂
│   │   └── utils.py
│   ├── api/                 # FastAPI REST API
│   │   ├── app.py           # 应用工厂
│   │   ├── main.py          # 启动入口
│   │   ├── middleware.py     # 日志/错误中间件
│   │   ├── dependencies.py  # 依赖注入
│   │   ├── models.py        # API 数据模型
│   │   └── routers/         # 8 个路由模块
│   ├── database/            # 图数据库层
│   │   ├── graph_database.py
│   │   ├── memory_graph.py  # 内存图存储
│   │   ├── mock_database.py # 测试用 Mock
│   │   └── query_service.py
│   ├── graph/               # 知识图谱构建与优化
│   │   ├── graph_builder.py
│   │   ├── graph_optimizer.py
│   │   └── memory_optimized_builder.py
│   ├── models/              # 核心数据模型
│   │   └── core.py          # CodeElement, CodeGraph, Relationship 等
│   ├── parser/              # 代码解析引擎
│   │   ├── tree_sitter_parser.py   # Tree-sitter 多语言解析
│   │   ├── relationship_extractor.py
│   │   ├── cross_file_analyzer.py
│   │   └── parser_factory.py
│   ├── services/            # 业务服务
│   │   ├── impact_analyzer.py      # 影响分析
│   │   ├── impact_grader.py        # 影响评级
│   │   ├── impact_visualizer.py    # 影响可视化
│   │   ├── qa_service.py           # 智能问答
│   │   ├── risk_detection_service.py
│   │   ├── cache_manager.py / cache_service.py
│   │   ├── batch_processor.py
│   │   ├── file_watcher.py
│   │   ├── incremental_updater.py
│   │   └── performance_manager.py
│   ├── utils/               # 工具模块
│   │   ├── logger.py
│   │   ├── monitoring.py
│   │   ├── scheduler.py
│   │   ├── error_handler.py
│   │   └── backup_recovery.py
│   ├── cli.py               # Click CLI 入口
│   ├── config.py            # 配置管理
│   ├── exceptions.py        # 自定义异常
│   └── interfaces.py        # 抽象接口定义
├── tests/                   # 测试套件
│   ├── unit/                # 单元测试
│   ├── property/            # 基于属性的测试 (Hypothesis)
│   └── integration/         # 集成测试
├── examples/                # 使用示例
├── sample_project/          # 示例项目（用于演示和测试）
├── pyproject.toml           # 项目配置与依赖
├── docker-compose.yml       # Docker 编排
├── .github/workflows/ci.yml # CI 流水线
└── .env.example             # 环境变量模板
```

### 技术栈

| 层次 | 技术 | 用途 |
|:---|:---|:---|
| 解析引擎 | tree-sitter | 多语言 AST 解析（Python / Java / JavaScript / C#） |
| Web 框架 | FastAPI + Uvicorn | REST API 服务 |
| 数据校验 | Pydantic v2 | 请求/响应模型与配置管理 |
| AI 集成 | OpenAI API (deepseek-coder) | 智能问答与文档生成 |
| CLI 框架 | Click + Rich | 命令行交互与格式化输出 |
| 代码高亮 | Pygments | 语法着色 |
| HTTP 客户端 | httpx | 异步 HTTP 请求 |
| 包管理 | setuptools + wheel | 项目构建与分发 |

---

## 配置说明

通过 `.env` 文件或环境变量进行配置：

### AI 模型配置

| 变量 | 默认值 | 说明 |
|:---|:---|:---|
| `AI_MODEL_NAME` | `deepseek-coder` | AI 模型名称 |
| `AI_API_KEY` | - | API 密钥（**必填**以启用 AI 功能） |
| `AI_API_BASE` | `https://api.deepseek.com` | API 端点地址 |
| `AI_MAX_TOKENS` | `4000` | 单次请求最大 Token 数 |
| `AI_TEMPERATURE` | `0.1` | 生成温度（越低越确定） |
| `AI_TIMEOUT` | `30` | 请求超时时间（秒） |

### 解析器配置

| 变量 | 默认值 | 说明 |
|:---|:---|:---|
| `PARSER_MAX_FILE_SIZE` | `10485760` | 单文件最大解析大小（10MB） |
| `PARSER_TIMEOUT` | `60` | 解析超时时间（秒） |
| `PARSER_WORKERS` | `4` | 并行解析线程数 |

### 服务器配置

| 变量 | 默认值 | 说明 |
|:---|:---|:---|
| `SERVER_HOST` | `0.0.0.0` | 监听地址 |
| `SERVER_PORT` | `8000` | 监听端口 |
| `SERVER_DEBUG` | `false` | 是否启用调试模式 |
| `SERVER_WORKERS` | `1` | 工作进程数 |

### 可选依赖

| 变量 | 说明 |
|:---|:---|
| `NEO4J_URI` / `NEO4J_USER` / `NEO4J_PASSWORD` | Neo4j 图数据库连接（可选，默认使用内存图） |
| `REDIS_HOST` / `REDIS_PORT` / `REDIS_DB` | Redis 缓存连接（可选，需安装 `codenexus[cache]`） |

---

## 开发指南

### 开发环境搭建

```bash
# 克隆并安装
git clone https://github.com/Swcmb/CodeNexus.git
cd CodeNexus
pip install -e ".[dev]"
```

### 运行测试

```bash
# 全部测试
pytest

# 仅单元测试
pytest tests/unit/

# 仅属性测试（Hypothesis）
pytest tests/property/

# 仅集成测试
pytest tests/integration/

# 生成覆盖率报告
pytest --cov=src/codenexus --cov-report=html
```

### 代码质量工具

```bash
# 格式化
black src/ tests/

# 导入排序
isort src/ tests/

# 代码检查
flake8 src/ tests/

# 类型检查
mypy src/
```

### 项目标记 (Markers)

| Marker | 说明 |
|:---|:---|
| `unit` | 单元测试 |
| `property` | 基于属性的测试 |
| `integration` | 集成测试 |
| `slow` | 慢速测试 |
| `asyncio` | 异步测试 |

### CI 流水线

项目使用 GitHub Actions 进行持续集成，PR 提交时自动执行：

1. **Lint** -- black / isort / flake8 / mypy（Python 3.9 - 3.12 矩阵）
2. **Test** -- 单元测试 + 属性测试 + 集成测试 + 覆盖率报告
3. **Build** -- 构建 sdist/wheel 并验证可安装性

### 架构设计原则

- **接口驱动**：所有核心组件均通过抽象接口（`interfaces.py`）定义契约，便于替换实现
- **分层架构**：解析 -> 图谱 -> 服务 -> API，各层职责清晰
- **可扩展性**：新增编程语言支持只需扩展 `parser/` 模块
- **容错机制**：内置熔断器（`with_circuit_breaker`）、全局错误处理和重试策略

---

## 示例代码

项目提供了 `examples/` 目录下的多个使用示例：

| 示例 | 说明 |
|:---|:---|
| `parser_demo.py` | 代码解析演示 |
| `graph_builder_demo.py` | 知识图谱构建演示 |
| `graph_optimizer_demo.py` | 图谱优化演示 |
| `relationship_demo.py` | 关系提取演示 |
| `impact_analyzer_demo.py` | 影响分析演示 |
| `impact_visualization_demo.py` | 影响可视化演示 |
| `qa_service_demo.py` | 智能问答演示 |
| `documentation_generator_demo.py` | 文档生成演示 |
| `ai_layer_demo.py` | AI 层演示 |
| `complete_demo.py` | 完整流程演示 |

---

## English Overview

CodeNexus is an intelligent code analysis tool that combines **static code analysis**, **knowledge graphs**, and **large language models** to provide deep structural understanding and intelligent assistance for large-scale software projects.

### Key Features

- **Multi-language Parsing** -- Supports Python, Java, JavaScript, and C# via tree-sitter
- **Knowledge Graph** -- Automatically extracts entities and relationships from code
- **Impact Analysis** -- Evaluates the scope and risk of code changes
- **AI-powered Q&A** -- Natural language questions about your codebase
- **Auto Documentation** -- AI-generated docs in Markdown or HTML
- **Risk Detection** -- Identifies potential risks in code
- **REST API + CLI** -- Use via HTTP API or command line
- **Batch Processing & Caching** -- Efficient handling of large projects
- **File Watching** -- Incremental updates on file changes

### Quick Start

```bash
pip install -e .

# Parse a project
codenexus parse -p ./my-project -o ./output

# Ask a question
codenexus qa -q "What does OrderService do?"

# Start the API server
uvicorn codenexus.api.app:create_app --factory --reload
```

---

## 许可证

本项目基于 [MIT License](LICENSE) 开源。

Copyright (c) 2026 codenexus Team

---

<div align="center">

**如果本项目对你有帮助，欢迎 Star 支持！**

[![Star](https://img.shields.io/github/stars/Swcmb/CodeNexus?style=social)](https://github.com/Swcmb/CodeNexus)

</div>
