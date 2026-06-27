# SmartCode (CodeNexus) 项目完善规格文档

> 版本: 2.0 | 日期: 2026-06-27 | 状态: 待审批 | 变更: 基于审查反馈修订

---

## 1. Purpose (目标)

将 SmartCode 从 "mostly_complete" 提升为 "production_ready" 状态。具体目标：

1. **消除运行时崩溃风险** — 完全重写 `CodeGraph.remove_node/remove_edge/get_neighbors`（现有代码访问了 `GraphNode`/`GraphEdge` 上完全不存在的属性，从未经过运行验证），修正 conftest.py fixture 字段与数据模型的严重不匹配。
2. **补全项目基础设施** — 添加 README.md、LICENSE、.gitignore、CI/CD 工作流等开源项目必备文件。
3. **统一依赖声明** — 消除 `requirements.txt` 与 `pyproject.toml` 之间的不一致，移除 Neo4j/Redis 未使用依赖，并处理 `cache_service.py` 对 `redis` 的硬依赖。
4. **修复配置漂移** — `.env.example` 与实际内存数据库架构对齐，清理 `.gitignore` 中 Neo4j/Redis 残留条目。
5. **补全 C# 解析器** — 将已声明的 `tree-sitter-c-sharp` 依赖真正接入解析器（含 `_setup_languages`、`_detect_language`、`parse_project`、`_get_element_type` 全链路适配）。
6. **替换 CLI Mock 数据** — `analyze` 命令接入真实的 `ImpactAnalyzer`，适配完全不同的返回类型 `ImpactAnalysisResult`。

---

## 2. Boundaries (范围界定)

### 纳入范围

| 类别 | 内容 |
|:---|:---|
| 必须修复 (P0) | CodeGraph 三个方法完全重写、.gitignore（含清理 Neo4j/Redis 残留）、LICENSE、README.md、CI/CD、依赖统一（含 cache_service.py redis 处理）、.env.example 修正 |
| 应该补全 (P1) | CLI analyze 真实调用（含返回类型适配）、C# 解析器全链路初始化、conftest.py fixture 字段修正、全部 37 个测试文件导入路径修正、.flake8 配置 |
| 建议补全 (P2) | Dockerfile、.pre-commit-config.yaml、GraphML 导出、测试运行验证、mypy 类型检查收敛 |

### 不纳入范围

- 不重构现有架构（内存图数据库保持不变）
- 不添加新的业务功能（如新的语言支持 beyond C#）
- 不改变 API 接口签名
- 不引入外部数据库依赖（Neo4j/Redis 维持移除决策）
- 不进行性能基准测试
- 不重写现有测试逻辑（仅修正导入路径和 fixture 字段）

---

## 3. Technical Approach (技术方案)

### 3.1 CodeGraph 三个方法完全重写

**问题分析**：`D:\SmartCode\src\codeweaver\models\core.py` 第 214-265 行的 `remove_node`、`remove_edge`、`get_neighbors` 三个方法是从未经过运行验证的死代码。问题不仅是 List-as-Dict 误用，还涉及访问完全不存在的属性：

| 方法 | 行号 | 错误 1: 容器误用 | 错误 2: 不存在的属性 |
|:---|:---|:---|:---|
| `remove_node` | 214-228 | `node_id not in self.nodes` / `del self.nodes[node_id]`（对 List 做 Dict 操作） | `node.incoming_edges`、`node.outgoing_edges`（GraphNode 无此属性）；`self.metadata.total_nodes`（实际为 `node_count`） |
| `remove_edge` | 230-245 | `edge_id not in self.edges` / `del self.edges[edge_id]`（对 List 做 Dict 操作） | `edge.source_node_id`、`edge.target_node_id`（实际为 `source_id`、`target_id`）；`node.remove_outgoing_edge()`、`node.remove_incoming_edge()`（GraphNode 无此方法）；`self.metadata.total_edges`（实际为 `edge_count`） |
| `get_neighbors` | 247-265 | `node_id not in self.nodes` / `self.nodes[node_id]`（对 List 做 Dict 操作） | `node.outgoing_edges`、`node.incoming_edges`（GraphNode 无此属性）；`edge.target_node_id`、`edge.source_node_id`（实际为 `target_id`、`source_id`） |

**关键数据模型字段**（用于修复参考）：
- `GraphNode`: `id`, `label`, `type`, `properties`（无 `incoming_edges`/`outgoing_edges`/`element`）
- `GraphEdge`: `id`, `source_id`, `target_id`, `type`, `properties`（无 `source_node_id`/`target_node_id`/`relationship`）
- `GraphMetadata`: `node_count`, `edge_count`, `file_count`, `languages`, `node_types`, `edge_types`, `creation_time`, `version`（无 `total_nodes`/`total_edges`/`project_name`/`project_path`/`language`）
- `CodeGraph`: `nodes: List[GraphNode]`, `edges: List[GraphEdge]`（List 而非 Dict）

**修复方案** — 三个方法均需完全重写：

```python
def remove_node(self, node_id: str) -> None:
    """移除节点及其相关边"""
    # 先移除关联的边
    edges_to_remove = [
        edge.id for edge in self.edges
        if edge.source_id == node_id or edge.target_id == node_id
    ]
    for edge_id in edges_to_remove:
        self.remove_edge(edge_id)

    # 移除节点（基于 List 过滤）
    original_count = len(self.nodes)
    self.nodes = [n for n in self.nodes if n.id != node_id]
    if len(self.nodes) < original_count:
        self.metadata.node_count = len(self.nodes)

def remove_edge(self, edge_id: str) -> None:
    """移除边"""
    original_count = len(self.edges)
    self.edges = [e for e in self.edges if e.id != edge_id]
    if len(self.edges) < original_count:
        self.metadata.edge_count = len(self.edges)

def get_neighbors(self, node_id: str, direction: str = "both") -> List[str]:
    """获取邻居节点ID列表"""
    neighbors = set()
    for edge in self.edges:
        if direction in ("both", "outgoing") and edge.source_id == node_id:
            neighbors.add(edge.target_id)
        if direction in ("both", "incoming") and edge.target_id == node_id:
            neighbors.add(edge.source_id)
    return list(neighbors)
```

### 3.2 conftest.py fixture 完全重写

**问题分析**：根目录 `conftest.py` 的 `sample_code_graph` fixture 使用了大量不存在的字段：

| 对象 | fixture 使用的字段 | 实际模型字段 | 问题 |
|:---|:---|:---|:---|
| `GraphNode(id="node1", element=element1)` | `element` | `id`, `label`, `type`, `properties` | `element` 字段不存在 |
| `GraphEdge(id="edge1", relationship=relationship, source_node_id="node1", target_node_id="node2")` | `relationship`, `source_node_id`, `target_node_id` | `id`, `source_id`, `target_id`, `type`, `properties` | 三个字段均不存在 |
| `GraphMetadata(project_name="test_project", project_path="/test", language="python")` | `project_name`, `project_path`, `language` | `node_count`, `edge_count`, `file_count`, `languages`, `node_types`, `edge_types`, `creation_time`, `version` | 三个字段均不存在 |

**修复方案**：
- 将 `conftest.py` 从根目录移到 `tests/conftest.py`
- 将导入路径从 `src.codenexus.*` 改为 `src.codeweaver.*`
- 修正 `sample_code_graph` fixture 中所有字段，使用正确的 `GraphNode`/`GraphEdge`/`GraphMetadata` 字段名

```python
@pytest.fixture
def sample_code_graph():
    """示例代码图fixture"""
    from src.codeweaver.models.core import (
        CodeGraph, GraphNode, GraphEdge, GraphMetadata,
    )

    node1 = GraphNode(id="node1", label="ClassA", type="class")
    node2 = GraphNode(id="node2", label="ClassB", type="class")

    edge = GraphEdge(id="edge1", source_id="node1", target_id="node2", type="inherits")

    graph = CodeGraph()
    graph.add_node(node1)
    graph.add_node(node2)
    graph.add_edge(edge)

    return graph
```

### 3.3 全部 37 个测试文件导入路径修正

**问题分析**：全部 37 个测试文件使用 `from src.codenexus.*` 导入路径（共 124 处），但实际包路径为 `src.codeweaver`（对应目录 `src/codeweaver/`）。仅修正 conftest.py 不足以使测试通过。

**修复方案**：
- 全局替换：`from src.codenexus.` → `from src.codeweaver.`（37 个文件，124 处替换）
- 同步修正 `import src.codenexus.` → `import src.codeweaver.`（如有）
- 修正范围包含根目录 `conftest.py`（移至 `tests/conftest.py`）及所有 `tests/` 子目录文件

### 3.4 依赖统一 + cache_service.py redis 处理

**问题分析**：`requirements.txt` 中未列出 `redis`，但 `src/codeweaver/services/cache_service.py` 第 12 行直接 `import redis`。仅从 requirements.txt 移除 redis 而不处理此导入会导致 `ImportError`。

**修复方案**：
1. `requirements.txt` 中移除 `neo4j`、`redis`，添加 `click`、`rich`、`pygments`
2. `cache_service.py` 中将 `import redis` 改为可选依赖导入：

```python
# 文件：src/codeweaver/services/cache_service.py
try:
    import redis
    from redis.exceptions import RedisError
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    # 定义占位类型以避免 NameError
    class RedisError(Exception):  # type: ignore[no-redef]
        pass
```

3. 在 `CacheService.__init__` 中添加检查：

```python
if not REDIS_AVAILABLE:
    raise ImportError(
        "redis 包未安装。缓存功能需要可选依赖：pip install codenexus[cache]"
    )
```

4. 在 `pyproject.toml` 中添加可选依赖分组：

```toml
[project.optional-dependencies]
cache = ["redis>=4.5.0"]
```

### 3.5 .env.example 修正 + .gitignore 清理

**修复方案**：
1. `.env.example`: 移除 `NEO4J_*` 和 `REDIS_*` 配置项，添加 `DB_STORAGE_TYPE=memory`
2. `.gitignore`: 移除第 171-175 行的 Neo4j/Redis 残留条目（`neo4j/` 和 `dump.rdb`）

### 3.6 C# 解析器全链路初始化

**问题分析**：规格文档原版仅覆盖 `_setup_languages` 和 `_detect_language`，遗漏了 `parse_project` 扫描扩展名列表和 `_get_element_type` 节点类型映射两个必要环节。此外需要为 C# 添加独立的 try/except 块以避免单个语言初始化失败导致全部解析器不可用。

**修复方案**（全链路 5 个修改点）：

1. **导入**（第 13 行区域）：`import tree_sitter_c_sharp as tscsharp`

2. **`_setup_languages`**（独立 try/except 块）：
```python
# 设置C#语言（独立try/except，避免初始化失败影响其他语言）
try:
    csharp_lang = Language(tscsharp.language())
    csharp_parser = Parser(csharp_lang)
    self.languages["c_sharp"] = csharp_lang
    self.parsers["c_sharp"] = csharp_parser
except Exception as e:
    parser_logger.warning(f"C# 解析器初始化失败（可选依赖）: {e}")
```

3. **`_detect_language` 的 `extension_map`**：添加 `".cs": "c_sharp"`

4. **`parse_project` 的扫描扩展名列表**：添加 `".cs"`

5. **`_get_element_type` 的 `type_mapping`**：添加 C# 特有节点类型：
```python
# C#
"class_declaration": ElementType.CLASS,      # 注意: Java/JS 已有同名key, C# tree-sitter 节点类型相同
"struct_declaration": ElementType.STRUCT,
"enum_declaration": ElementType.ENUM,
"interface_declaration": ElementType.INTERFACE,
"method_declaration": ElementType.METHOD,
"field_declaration": ElementType.FIELD,
"namespace_declaration": ElementType.NAMESPACE,
"constructor_declaration": ElementType.METHOD,
"destructor_declaration": ElementType.METHOD,
"property_declaration": ElementType.FIELD,
"event_declaration": ElementType.FIELD,
"delegate_declaration": ElementType.CLASS,
"record_declaration": ElementType.CLASS,
```

注意：`_get_element_type` 的 `type_mapping` 中 Java/JS 与 C# 存在同名节点类型（如 `class_declaration`、`method_declaration`）。由于当前映射是按节点类型字符串直接匹配，同名类型共享同一个 `ElementType` 映射，这是正确的——tree-sitter 各语言绑定使用相同的节点类型名称约定。

### 3.7 CLI analyze 命令替换 Mock（含返回类型适配）

**问题分析**：替换 Mock 后面临三个关键问题：
1. `ImpactAnalyzer.__init__` 需要 `GraphQueryService` 实例，`GraphQueryService.__init__` 需要 `database` 实例
2. CLI 当前无加载知识图谱的逻辑
3. `ImpactAnalysisResult` 的字段（`affected_nodes: List[ImpactNode]`、`impact_summary: Dict[ImpactLevel, int]`、`critical_paths`）与 `MockImpactResult` 的字段（`affected_files`、`affected_functions`、`affected_classes`、`risk_level`）完全不同，下游显示逻辑需要完全重写

**修复方案**：
1. 复用 `qa` 命令中已有的知识图谱加载逻辑（搜索项目路径下的 `.json` 图谱文件）
2. 创建 `MockGraphDatabase`（或 `InMemoryDatabase`）实例 → 加载图谱数据 → 创建 `GraphQueryService` → 创建 `ImpactAnalyzer`
3. 根据 `--file` 参数在图谱中查找对应的节点 ID
4. 调用 `analyzer.analyze_impact(graph_name, node_id, change_type=ChangeType.MODIFY, max_depth=depth)`
5. 完全重写下游显示逻辑以适配 `ImpactAnalysisResult`：
   - `affected_nodes` → 显示每个 `ImpactNode` 的 `node_name`、`node_type`、`impact_level`、`impact_score`、`distance_from_change`
   - `impact_summary` → 按 `ImpactLevel` 统计受影响节点数
   - `critical_paths` → 显示关键影响路径
   - 移除对 `affected_files`、`affected_functions`、`affected_classes`、`risk_level` 的所有引用

### 3.8 CI/CD 配置

**修复方案**：
- 创建 `.github/workflows/ci.yml`
- 定义 Jobs：lint（black + isort + flake8 + mypy）、test（pytest）、build（包构建验证）
- 触发条件：push to main、PR to main
- Python 版本矩阵：3.9、3.10、3.11、3.12

### 3.9 .flake8 配置

**修复方案**：
- 创建 `.flake8` 文件，与 black 的 line-length=88 保持一致
- 排除 `__pycache__`、`.git`、`.eggs`、`build`、`dist` 目录

---

## 4. Concrete Actions (具体执行步骤)

### Phase 1: P0 — 必须修复（阻止正常使用）

#### 步骤 1.1: 完全重写 CodeGraph.remove_node/remove_edge/get_neighbors

文件：`D:\SmartCode\src\codeweaver\models\core.py`

操作：替换第 214-265 行的三个方法。参见第 3.1 节的完整代码。关键变更：
- `remove_node`: 移除 `node_id not in self.nodes`（List 不支持 `in` 字典语义）、`del self.nodes[node_id]`、`node.incoming_edges`/`node.outgoing_edges`（不存在）、`self.metadata.total_nodes`（应为 `node_count`）
- `remove_edge`: 移除 `edge_id not in self.edges`、`del self.edges[edge_id]`、`edge.source_node_id`/`edge.target_id`（应为 `source_id`/`target_id`）、`node.remove_outgoing_edge()`/`remove_incoming_edge()`（不存在）、`self.metadata.total_edges`（应为 `edge_count`）
- `get_neighbors`: 移除 `node_id not in self.nodes`、`self.nodes[node_id]`、`node.outgoing_edges`/`node.incoming_edges`（不存在）、`edge.target_node_id`/`edge.source_node_id`（应为 `target_id`/`source_id`）

#### 步骤 1.2: 创建 .gitignore（含清理 Neo4j/Redis 残留）

文件：`D:\SmartCode\.gitignore`

操作：
1. 如果文件已存在，移除第 171-175 行的 Neo4j/Redis 残留条目（`neo4j/` 和 `dump.rdb`）
2. 确保覆盖：`__pycache__/`、`*.pyc`、`*.egg-info/`、`.eggs/`、`build/`、`dist/`、`.mypy_cache/`、`.pytest_cache/`、`.coverage`、`htmlcov/`、`.env`、`.venv/`、`*.log`、`.idea/`、`.vscode/`

#### 步骤 1.3: 创建 LICENSE

文件：`D:\SmartCode\LICENSE`

内容：MIT License，copyright holder 为 "codenexus Team"（与 pyproject.toml authors 一致）。

#### 步骤 1.4: 创建 README.md

文件：`D:\SmartCode\README.md`

内容结构：
- 项目名称 + 一句话描述
- 功能特性（代码解析、知识图谱、影响分析、智能问答、文档生成）
- 快速开始（pip install、环境变量配置、CLI 使用示例）
- 支持语言（Python、Java、JavaScript、C#）
- 开发指南（安装 dev 依赖、运行测试、代码格式化）
- API 文档入口（FastAPI Swagger）
- 许可证

#### 步骤 1.5: 统一依赖声明 + cache_service.py redis 处理

文件：`D:\SmartCode\requirements.txt`、`D:\SmartCode\src\codeweaver\services\cache_service.py`、`D:\SmartCode\pyproject.toml`

操作：
1. `requirements.txt` 中移除 `neo4j>=5.0.0`、`redis>=4.5.0`，添加 `click>=8.0.0`、`rich>=13.0.0`、`pygments>=2.15.0`
2. `cache_service.py` 中将硬依赖 `import redis` 改为 try/except 可选导入（参见第 3.4 节代码）
3. `CacheService.__init__` 中添加 `REDIS_AVAILABLE` 检查
4. `pyproject.toml` 中添加 `[project.optional-dependencies].cache = ["redis>=4.5.0"]`

#### 步骤 1.6: 修正 .env.example

文件：`D:\SmartCode\.env.example`

操作：
1. 删除 `NEO4J_URI`、`NEO4J_USER`、`NEO4J_PASSWORD` 三行
2. 删除 `REDIS_HOST`、`REDIS_PORT`、`REDIS_DB` 三行
3. 在顶部添加 `# 数据库配置（内存模式，无需外部数据库）` 和 `DB_STORAGE_TYPE=memory`
4. 保留 AI、Parser、Server 配置项不变

#### 步骤 1.7: 创建 CI/CD 工作流

文件：`D:\SmartCode\.github\workflows\ci.yml`

定义三个 Job：
1. **lint** — 运行 black --check、isort --check、flake8、mypy
2. **test** — 运行 pytest（矩阵：Python 3.9/3.10/3.11/3.12）
3. **build** — 验证 `python -m build` 能成功生成 sdist 和 wheel

---

### Phase 2: P1 — 应该补全（影响功能完整性）

#### 步骤 2.1: C# 解析器全链路初始化

文件：`D:\SmartCode\src\codeweaver\parser\tree_sitter_parser.py`

操作（5 个修改点）：
1. 第 13 行区域添加 `import tree_sitter_c_sharp as tscsharp`
2. `_setup_languages` 末尾添加 C# 语言注册（独立 try/except 块，失败仅 warning 不影响其他语言）
3. `_detect_language` 的 `extension_map` 添加 `".cs": "c_sharp"`
4. `parse_project` 的扫描扩展名列表添加 `".cs"`
5. `_get_element_type` 的 `type_mapping` 添加 C# 特有节点类型（`struct_declaration`、`namespace_declaration`、`constructor_declaration`、`property_declaration`、`record_declaration` 等）

#### 步骤 2.2: CLI analyze 命令接入真实 ImpactAnalyzer

文件：`D:\SmartCode\src\codeweaver\cli.py`（第 346-426 行）

操作：
1. 移除 `MockImpactResult` 内联类定义（第 373-380 行）
2. 加载知识图谱文件（复用 qa 命令中的图谱加载逻辑）
3. 创建 `MockGraphDatabase`/`InMemoryDatabase` 实例并加载图谱数据
4. 创建 `GraphQueryService(database)` → `ImpactAnalyzer(query_service)`
5. 根据 `--file` 参数在图谱中查找对应的图节点 ID
6. 调用 `analyzer.analyze_impact(graph_name, node_id, change_type=ChangeType.MODIFY, max_depth=depth)`
7. **完全重写**显示逻辑以适配 `ImpactAnalysisResult`：
   - 替换 `affected_files` 显示为 `affected_nodes` 列表（显示 `node_name`、`node_type`、`impact_level`、`impact_score`、`distance_from_change`）
   - 替换 `risk_level` 为 `impact_summary`（按 `ImpactLevel` 统计）
   - 添加 `critical_paths` 显示
   - 移除对 `affected_functions`、`affected_classes` 的引用

#### 步骤 2.3: 修正 conftest.py 及全部测试文件导入路径

文件：`D:\SmartCode\conftest.py`（移至 `tests/conftest.py`）+ 37 个测试文件

操作：
1. 将根目录 `conftest.py` 移动到 `tests/conftest.py`
2. 在 `tests/conftest.py` 中修正 `sample_code_graph` fixture 的所有字段（参见第 3.2 节）
3. 全局替换 37 个测试文件中 124 处 `from src.codenexus.` → `from src.codeweaver.`
4. 同步修正 `import src.codenexus.` → `import src.codeweaver.`（如有）

#### 步骤 2.4: 创建 .flake8 配置

文件：`D:\SmartCode\.flake8`

```ini
[flake8]
max-line-length = 88
extend-ignore = E203, W503
exclude =
    __pycache__,
    .git,
    .eggs,
    build,
    dist,
    .mypy_cache,
    .venv
```

---

### Phase 3: P2 — 建议补全（提升工程体验）

#### 步骤 3.1: 创建 Dockerfile

文件：`D:\SmartCode\Dockerfile`

基于 `python:3.11-slim`，多阶段构建：
- builder 阶段：安装依赖
- runtime 阶段：仅复制运行时必需文件
- 暴露 8000 端口，CMD 为 uvicorn 启动命令

#### 步骤 3.2: 创建 docker-compose.yml

文件：`D:\SmartCode\docker-compose.yml`

定义 codenexus 服务，挂载 `.env` 文件，映射端口。

#### 步骤 3.3: 创建 .pre-commit-config.yaml

文件：`D:\SmartCode\.pre-commit-config.yaml`

hooks：black、isort、flake8、mypy（与 pyproject.toml 配置一致）。

#### 步骤 3.4: GraphML 导出实现

文件：`D:\SmartCode\src\codeweaver\cli.py`（graph_export 命令）

操作：
1. 在 `format == 'graphml'` 分支中实现 GraphML XML 生成
2. 使用标准 XML 库（无需额外依赖）构建 GraphML 结构
3. 映射 GraphNode 和 GraphEdge 到 GraphML 的 node 和 edge 元素

#### 步骤 3.5: 测试运行验证

操作：
1. 运行 `pytest tests/ -v --tb=short` 获取完整测试报告
2. 确认步骤 2.3 的导入路径替换后测试通过率提升
3. 修复剩余因 fixture 字段不匹配导致的测试失败
4. 对因环境依赖（如 tree-sitter-c-sharp 未安装）失败的测试标记 `@pytest.mark.skip`

#### 步骤 3.6: mypy 类型检查收敛（分级目标）

操作：
1. 运行 `mypy src/codeweaver/ --ignore-missing-imports` 获取错误列表
2. 优先修复 `error` 级别的类型错误（预计 core.py 重写后消除主要 error）
3. 对第三方库类型缺失使用 `# type: ignore[import-untyped]` 注释
4. **分级目标**：
   - 基线目标：`mypy src/codeweaver/ --ignore-missing-imports` 下 error 数量 < 30
   - 进阶目标：`mypy src/codeweaver/ --ignore-missing-imports` 下 error 数量 < 15
   - 严格目标（可选）：`mypy src/codeweaver/ --strict` 下 error 数量 < 50

---

## 5. Success Criteria (成功标准)

### P0 验收标准

| 编号 | 验收条件 | 验证方法 |
|:---|:---|:---|
| SC-01 | `CodeGraph.remove_node()` 在添加节点后删除不抛异常 | 运行 `python -c "from src.codeweaver.models.core import CodeGraph, GraphNode; g = CodeGraph(); g.add_node(GraphNode(id='n1', label='A', type='class')); g.remove_node('n1'); assert len(g.nodes) == 0"` |
| SC-02 | `CodeGraph.remove_edge()` 在添加边后删除不抛异常 | 同上模式，添加边后删除 |
| SC-03 | `CodeGraph.get_neighbors()` 返回正确的邻居列表 | 添加节点和边后调用 `get_neighbors` 验证返回值 |
| SC-04 | `.gitignore` 存在且不含 Neo4j/Redis 条目 | `grep -c "neo4j\|redis\|dump\.rdb" .gitignore` 返回 0（忽略大小写） |
| SC-05 | `.gitignore` 存在且覆盖 __pycache__ | `git status` 中不出现 `__pycache__` 文件 |
| SC-06 | LICENSE 文件存在且为 MIT | 文件存在且包含 "MIT License" |
| SC-07 | README.md 存在且包含快速开始 | 文件存在且包含 "Quick Start" 或 "快速开始" |
| SC-08 | requirements.txt 不含 neo4j/redis | `grep -c "neo4j\|redis" requirements.txt` 返回 0 |
| SC-09 | cache_service.py 的 redis 导入为可选 | `python -c "from src.codeweaver.services.cache_service import REDIS_AVAILABLE; print(REDIS_AVAILABLE)"` 不抛 ImportError |
| SC-10 | .env.example 不含 NEO4J/REDIS | `grep -c "NEO4J\|REDIS" .env.example` 返回 0 |
| SC-11 | CI workflow 语法正确 | `act -n` 或 GitHub Actions linter 验证 |

### P1 验收标准

| 编号 | 验收条件 | 验证方法 |
|:---|:---|:---|
| SC-12 | C# 文件可被解析 | `python -c "from src.codeweaver.parser.tree_sitter_parser import TreeSitterParser; p = TreeSitterParser(); assert 'c_sharp' in p.get_supported_languages()"` |
| SC-13 | C# 扩展名映射正确 | `_detect_language('test.cs')` 返回 `'c_sharp'` |
| SC-14 | CLI analyze 不使用 Mock | 代码审查确认无 MockImpactResult 引用 |
| SC-15 | CLI analyze 显示 ImpactAnalysisResult 字段 | 代码审查确认显示 `affected_nodes`、`impact_summary` 而非 `affected_files`、`affected_functions` |
| SC-16 | flake8 配置存在 | `.flake8` 文件存在 |
| SC-17 | conftest.py 存在且字段正确 | `tests/conftest.py` 存在，fixture 中无 `element=`、`relationship=`、`source_node_id=`、`project_name=` |
| SC-18 | 测试文件导入路径正确 | `grep -r "from src.codenexus" tests/` 返回 0 匹配 |

### P2 验收标准

| 编号 | 验收条件 | 验证方法 |
|:---|:---|:---|
| SC-19 | Docker 镜像可构建 | `docker build -t codenexus .` 成功 |
| SC-20 | pre-commit hooks 可安装 | `pre-commit install` 成功 |
| SC-21 | 测试通过率提升 | `pytest tests/` 输出 summary，通过率相比基线有提升 |
| SC-22 | mypy error 数量收敛 | `mypy src/codeweaver/ --ignore-missing-imports` error 数量 < 30 |

---

## 6. Contingency (回滚策略)

### 通用回滚原则

所有修改基于 Git 分支进行。每个 Phase 创建独立分支，合并前必须通过该 Phase 的验收标准。

### 分支策略

```
main
 └── fix/codenexus-p0-infrastructure   (Phase 1)
 └── feat/codenexus-p1-completion      (Phase 2)
 └── feat/codenexus-p2-polish          (Phase 3)
```

### 具体回滚方案

| 场景 | 回滚操作 |
|:---|:---|
| CodeGraph 重写引入回归 | `git revert` 对应 commit，恢复原始实现（虽然有 bug，但现有调用方可能已规避） |
| CI workflow 语法错误 | 删除 `.github/workflows/ci.yml`，重新提交修正版本 |
| 依赖统一导致安装失败 | 恢复原始 requirements.txt，仅在 pyproject.toml 中修正 |
| cache_service.py 改动导致缓存功能异常 | 恢复原始硬依赖导入，在 pyproject.toml 和 requirements.txt 中恢复 redis 依赖 |
| C# 解析器初始化失败（tree-sitter-c-sharp 版本不兼容） | 已在方案中用 try/except 包裹，失败仅 warning 不影响其他语言 |
| CLI analyze 真实调用失败 | 保留 Mock 作为 fallback，添加 `--mock` flag 用于离线演示 |
| 测试导入路径替换引入错误 | 使用 `git diff` 检查替换结果，对误替换用 `git checkout` 恢复单个文件 |
| 测试修复过程中发现更多问题 | 仅修复与本次变更直接相关的测试，其余标记 `@pytest.mark.skip(reason="待后续修复")` |

### 数据安全

- 本次变更不涉及数据库迁移或数据格式变更
- 知识图谱 JSON 格式保持不变
- API 接口签名保持不变

---

## 附录：文件变更清单

| 操作 | 文件路径 | Phase | 变更说明 |
|:---|:---|:---|:---|
| 完全重写 | `src/codeweaver/models/core.py` | P0 | 重写 remove_node/remove_edge/get_neighbors 三个方法 |
| 创建/修改 | `.gitignore` | P0 | 创建或清理 Neo4j/Redis 残留条目 |
| 创建 | `LICENSE` | P0 | MIT License |
| 创建 | `README.md` | P0 | 项目文档 |
| 修改 | `requirements.txt` | P0 | 移除 neo4j/redis，添加 click/rich/pygments |
| 修改 | `src/codeweaver/services/cache_service.py` | P0 | redis 硬依赖改为可选导入 |
| 修改 | `pyproject.toml` | P0 | 添加 `[project.optional-dependencies].cache` |
| 修改 | `.env.example` | P0 | 移除 NEO4J/REDIS，添加 DB_STORAGE_TYPE=memory |
| 创建 | `.github/workflows/ci.yml` | P0 | CI/CD 工作流 |
| 修改 | `src/codeweaver/parser/tree_sitter_parser.py` | P1 | C# 全链路初始化（5 个修改点） |
| 完全重写 | `src/codeweaver/cli.py` (analyze 命令) | P1 | 替换 Mock + 重写显示逻辑 |
| 移动+重写 | `conftest.py` → `tests/conftest.py` | P1 | 修正 fixture 字段 |
| 批量替换 | `tests/` 下 37 个文件 | P1 | 124 处 `src.codenexus` → `src.codeweaver` |
| 创建 | `.flake8` | P1 | Lint 配置 |
| 创建 | `Dockerfile` | P2 | 多阶段构建 |
| 创建 | `docker-compose.yml` | P2 | 服务编排 |
| 创建 | `.pre-commit-config.yaml` | P2 | Git hooks |

---

## 附录：审查反馈变更摘要

| 反馈编号 | 严重程度 | 变更内容 |
|:---|:---|:---|
| #1 | 严重 | 将 remove_node/remove_edge 从"bug 修复"升级为"完全重写"，列出所有 6 个错误属性名及正确值 |
| #2 | 严重 | 新增 get_neighbors 方法到重写范围，列出其 4 个错误属性名 |
| #3 | 严重 | 新增 conftest.py fixture 字段不匹配的完整清单（3 个对象、7 个错误字段），提供正确 fixture 代码 |
| #4 | 严重 | 新增 cache_service.py redis 可选依赖处理方案（try/except + REDIS_AVAILABLE + pyproject.toml optional-dependencies） |
| #5 | 严重 | 扩展 CLI analyze 替换方案，明确说明图谱加载流程、database 实例创建、ImpactAnalysisResult 字段映射、显示逻辑完全重写 |
| #6 | 中等 | 将 C# 解析器从 3 个修改点扩展为 5 个，新增 parse_project 扫描和 _get_element_type 映射，添加独立 try/except |
| #7 | 中等 | 新增全部 37 个测试文件导入路径修正步骤（124 处替换），SC-18 新增导入路径验证 |
| #8 | 中等 | 将 mypy 目标从"< 10 error"降级为分级目标（< 30 / < 15 / < 50 三级） |
| #9 | 低 | 在步骤 1.2 中新增 .gitignore Neo4j/Redis 残留清理，SC-04 新增验证 |
| #10 | 低 | 修正 Contingency 分支命名：P3 → P2 |
