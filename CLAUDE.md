# CLAUDE.md - SmartCode (CodeNexus)

## 项目概述

智能代码分析与知识图谱构建工具，通过静态代码解析（Tree-sitter）构建代码知识图谱，并集成 LLM（默认 DeepSeek-Coder）提供智能问答、影响分析、文档生成和风险检测能力。

## 技术栈

| 类别 | 技术 |
|:---|:---|
| 语言 | Python 3.9+ |
| 构建 | setuptools / pyproject.toml |
| 代码解析 | tree-sitter (Python/Java/JavaScript/C#) |
| Web 框架 | FastAPI + Uvicorn |
| 数据验证 | Pydantic v2 |
| AI 集成 | OpenAI SDK (兼容 DeepSeek-Coder) |
| CLI | Click + Rich |
| 图数据库 | 内存图数据库（MemoryGraphDatabase） |
| 测试 | pytest + pytest-asyncio + hypothesis（属性测试） |
| 代码规范 | black + isort + flake8 + mypy |

## 目录结构

```
D:/SmartCode/
├── src/codeweaver/               # 核心源码（包名 codeweaver）
│   ├── __init__.py               # 版本 0.1.0
│   ├── __main__.py               # python -m codenexus 入口
│   ├── cli.py                    # Click CLI（parse/docs/analyze/qa/health/graph）
│   ├── config.py                 # 配置管理（环境变量驱动的 dataclass）
│   ├── interfaces.py             # 抽象接口定义（8 个 ABC 接口）
│   ├── exceptions.py             # 自定义异常层次
│   ├── models/
│   │   └── core.py               # 核心数据模型（CodeElement/Relationship/CodeGraph 等）
│   ├── parser/
│   │   ├── tree_sitter_parser.py # Tree-sitter 多语言解析器
│   │   ├── parser_factory.py     # 解析器工厂
│   │   ├── relationship_extractor.py # 关系提取
│   │   └── cross_file_analyzer.py    # 跨文件分析
│   ├── graph/
│   │   ├── graph_builder.py      # 图谱构建
│   │   ├── graph_optimizer.py    # 图谱优化
│   │   └── memory_optimized_builder.py # 内存优化构建
│   ├── database/
│   │   ├── graph_database.py     # 图数据库接口（包装内存实现）
│   │   ├── memory_graph.py       # 内存图数据库实现
│   │   ├── mock_database.py      # 模拟数据库（测试用）
│   │   └── query_service.py      # 查询服务
│   ├── ai/
│   │   ├── ai_layer.py           # AI 智能层（OpenAI SDK 接口）
│   │   ├── documentation_generator.py # 文档生成
│   │   ├── factory.py            # AI 工厂
│   │   └── utils.py              # AI 工具函数
│   ├── services/
│   │   ├── impact_analyzer.py    # 影响分析
│   │   ├── impact_visualizer.py  # 影响可视化
│   │   ├── impact_grader.py      # 影响评级
│   │   ├── qa_service.py         # 智能问答
│   │   ├── risk_detection_service.py # 风险检测
│   │   ├── cache_service.py      # 缓存服务
│   │   ├── cache_manager.py      # 缓存管理
│   │   ├── batch_processor.py    # 批处理
│   │   ├── performance_manager.py # 性能管理
│   │   ├── file_watcher.py       # 文件监控
│   │   └── incremental_updater.py # 增量更新
│   ├── api/
│   │   ├── app.py                # FastAPI 应用工厂
│   │   ├── main.py               # 服务器启动脚本
│   │   ├── models.py             # API 数据模型
│   │   ├── middleware.py         # 中间件
│   │   ├── dependencies.py       # 依赖注入
│   │   └── routers/              # 8 个路由模块
│   │       ├── health.py         # /api/v1/health
│   │       ├── parser.py         # /api/v1/parser
│   │       ├── graph.py          # /api/v1/graph
│   │       ├── documentation.py  # /api/v1/docs
│   │       ├── qa.py             # /api/v1/qa
│   │       ├── risk.py           # /api/v1/risk
│   │       ├── visualization.py  # /api/v1/viz
│   │       └── backup.py         # /api/v1/backup
│   └── utils/
│       ├── logger.py             # 日志配置
│       ├── error_handler.py      # 错误处理（熔断器等）
│       ├── monitoring.py         # 系统监控
│       ├── scheduler.py          # 异步任务调度
│       └── backup_recovery.py    # 备份恢复
├── tests/
│   ├── unit/                     # 单元测试（20+ 文件）
│   ├── integration/              # 集成测试（API 端点、文档集成）
│   └── property/                 # 基于属性的测试（hypothesis）
├── examples/                     # 功能演示脚本（10 个 demo）
├── sample_project/               # 示例项目（用于测试解析和图谱构建）
├── docs/                         # 项目文档
├── analysis/                     # 解析输出目录
├── conftest.py                   # pytest 全局 fixture
├── pyproject.toml                # 项目配置
├── requirements.txt              # 依赖列表
└── .env.example                  # 环境变量模板
```

## 构建/运行/测试命令

```bash
# 安装（开发模式）
pip install -e ".[dev]"

# CLI 使用
python -m codenexus health                              # 健康检查
python -m codenexus parse <path> -o <output>             # 解析项目
python -m codenexus docs -o <output>                     # 生成文档
python -m codenexus qa -q "问题" -p <project>            # 智能问答
python -m codenexus analyze -f <file> -c "变更描述"      # 影响分析
python -m codenexus graph-export -o <output>             # 导出图谱

# 启动 API 服务
python -m src.codeweaver.api.main                        # 开发模式（端口 8000）
uvicorn src.codeweaver.api.app:create_app --port 8000    # 生产模式

# 测试
pytest                                         # 全量测试（含覆盖率报告）
pytest tests/unit/                             # 仅单元测试
pytest tests/integration/                      # 仅集成测试
pytest tests/property/                         # 仅属性测试
pytest -m unit                                 # 按标记运行
pytest --cov=src/codeweaver --cov-report=html  # HTML 覆盖率报告

# 代码质量
black src/ tests/                              # 格式化
isort src/ tests/                              # import 排序
flake8 src/                                    # 静态检查
mypy src/                                      # 类型检查
```

## 开发规范要点

1. **接口驱动设计**：所有核心组件通过 `interfaces.py` 中的 ABC 定义接口，实现类需遵守对应接口契约。
2. **配置管理**：通过环境变量驱动（参考 `.env.example`），`config.py` 中的 `dataclass` 统一管理。
3. **异常处理**：使用 `exceptions.py` 中的自定义异常层次，业务层抛 `codenexusError` 子类，API 层抛 `codenexusException`。
4. **异步优先**：服务层（`services/`）和 AI 层主要使用 `async/await`，CLI 层通过 `asyncio.run()` 桥接。
5. **测试分类**：`unit`（纯逻辑）、`integration`（API 端点）、`property`（hypothesis 属性测试），通过 pytest marker 区分。
6. **命名注意**：pyproject.toml 中项目名为 `codenexus`，但源码包目录为 `src/codeweaver/`，CLI 入口点映射为 `codenexus.cli:cli`，`__main__.py` 中引用 `.cli`。新增模块时请注意当前包路径。
7. **中文注释**：关键逻辑和复杂代码段添加中文注释。
8. **代码格式**：black（行宽 88）、isort（profile=black）、mypy strict 模式。

## 关键依赖

| 依赖 | 用途 |
|:---|:---|
| tree-sitter + 语言包 | 多语言 AST 解析 |
| fastapi + uvicorn | Web API 服务 |
| pydantic v2 | 数据验证和序列化 |
| openai | LLM 集成（兼容 DeepSeek） |
| click + rich | CLI 界面 |
| pytest + hypothesis | 测试框架 + 属性测试 |
