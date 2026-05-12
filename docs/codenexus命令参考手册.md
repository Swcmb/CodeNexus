## 安装与配置

```bash
# 安装项目
pip install -e .

# 配置AI API密钥（可选，用于AI相关功能）
$env:AI_MODEL_NAME="deepseek-v3-250324"
$env:AI_API_KEY="your_api_key_here"
$env:AI_API_BASE="https://ark.cn-beijing.volces.com/api/v3"
```

## 命令行工具

### 1. 系统健康检查

检查系统各组件状态，确认所有依赖项正常工作。

```bash
python -m src.codenexus health [--project-path, -p 项目路径]
```

**选项：**
- `--project-path`, `-p`: 项目路径（可选，默认为当前目录）

**示例：**
```bash
# 检查当前目录
python -m src.codenexus health

# 检查指定项目
python -m src.codenexus health -p sample_project
```

**功能说明：**
- 检查解析器是否正常
- 检查内存图数据库连接
- 检查AI配置状态

---

### 2. 代码解析

解析代码项目并构建知识图谱。

```bash
python -m src.codenexus parse [项目路径] -o [输出目录] [选项]
```

**选项：**
- `--output`, `-o`: 输出目录（必须）
- `--include`: 文件过滤模式（如: "*.py"）
- `--workers`, `-w`: 并行工作线程数（默认: 2）

**示例：**
```bash
# 解析当前目录下的Python项目
python -m src.codenexus parse . -o analysis

# 解析特定目录下的所有Python文件
python -m src.codenexus parse sample_project -o analysis
```

**功能说明：**
- 扫描项目中的代码文件
- 使用Tree-sitter解析器分析代码结构
- 构建知识图谱并保存到内存数据库
- 导出图谱数据和解析结果

---

### 3. 查看知识图谱信息

查看已构建的知识图谱统计信息。

```bash
python -m src.codenexus graph-info [--project-path, -p 项目路径]
```

**选项：**
- `--project-path`, `-p`: 项目路径（可选，默认为当前目录）

**示例：**
```bash
# 查看当前目录的图谱信息
python -m src.codenexus graph-info

# 查看指定项目的图谱信息
python -m src.codenexus graph-info -p sample_project
```

**输出说明：**
- 显示节点和边的数量
- 展示节点类型分布
- 提供图谱的概览统计

---

### 4. 生成文档

根据知识图谱生成项目文档。

```bash
python -m src.codenexus docs -o [输出目录] [选项]
```

**选项：**
- `--output`, `-o`: 输出目录（必须）
- `--project-path`, `-p`: 项目路径（可选，默认为当前目录）
- `--format`, `-f`: 输出格式（markdown 或 html，默认: markdown）
- `--include-private`: 包含私有成员（可选）

**示例：**
```bash
# 生成Markdown格式文档
python -m src.codenexus docs -o docs --format markdown -p sample_project 

# 生成HTML格式文档
python -m src.codenexus docs -o docs --format html -p sample_project

# 包含私有成员的文档
python -m src.codenexus docs -o docs --format markdown -p sample_project --include-private
```

**功能说明：**
- 从知识图谱提取代码结构信息
- 生成包含类和函数列表的文档
- 提供项目结构概览

---

### 5. 影响分析

分析代码变更对项目的影响。

```bash
python -m src.codenexus analyze -f [文件路径] -c [变更描述] [选项]
```

**选项：**
- `--file`, `-f`: 要分析的文件（必须）
- `--change`, `-c`: 变更描述（必须）
- `--project-path`, `-p`: 项目路径（可选，默认为当前目录）
- `--depth`, `-d`: 分析深度（默认: 3）

**示例：**
```bash
# 分析主函数修改的影响
python -m src.codenexus analyze -f sample_project/src/main.py -c "修改主函数入口" --depth 3
```

**功能说明：**
- 识别受变更影响的文件
- 评估风险等级
- 显示受影响的函数和类

---

### 6. 智能问答

基于代码库进行智能问答。

```bash
python -m src.codenexus qa -q [问题] [选项]
```

**选项：**
- `--question`, `-q`: 问题（必须）
- `--project-path`, `-p`: 项目路径（可选，默认为当前目录）

**示例：**
```bash
# 询问关于项目功能的问题
python -m src.codenexus qa -q "这个项目的主要功能是什么？"

# 询问关于特定函数的问题
python -m src.codenexus qa -q "create_user函数是如何工作的？"

# 询问类的用途
python -m src.codenexus qa -q "User模型类有什么属性和方法？"
```

**功能说明：**
- 使用AI模型理解问题
- 搜索知识图谱中的相关信息
- 提供基于代码的智能回答
- 显示相关代码片段

---

### 7. 导出知识图谱

将知识图谱导出为文件。

```bash
python -m src.codenexus graph-export -o [输出文件] [选项]
```

**选项：**
- `--output`, `-o`: 输出文件路径（必须）
- `--project-path`, `-p`: 项目路径（可选，默认为当前目录）
- `--format`, `-f`: 导出格式（json 或 graphml，默认: json）

**示例：**
```bash
# 导出为JSON格式
python -m src.codenexus graph-export -o knowledge_graph.json --format json -p sample_project

# 导出为GraphML格式
python -m src.codenexus graph-export -o knowledge_graph.graphml --format graphml -p sample_project
```

**功能说明：**
- 将知识图谱数据导出为文件
- 支持多种格式以便后续处理
- 便于备份和分享图谱数据

---

## API服务器

### 启动API服务器

```powershell
# Windows PowerShell中使用uvicorn启动
uvicorn src.codenexus.api.app:create_app --reload --host 0.0.0.0 --port 8000

# 或者使用Python模块方式启动
python -m src.codenexus.api.main
```

服务器将在 http://localhost:8000 上运行。

### API端点

所有API端点都使用 `/api/v1` 前缀。

#### 1. 健康检查 ✅

```powershell
# 基本健康检查
Invoke-WebRequest -Uri http://localhost:8000/api/v1/health -Method GET

# 详细健康检查
Invoke-WebRequest -Uri http://localhost:8000/api/v1/health/detailed -Method GET
```

#### 2. 解析器 ✅

```powershell
# 获取支持的语言列表
Invoke-WebRequest -Uri http://localhost:8000/api/v1/parser/languages -Method GET

# 解析项目（需要认证）
Invoke-WebRequest -Uri http://localhost:8000/api/v1/parser/project -Method POST -ContentType "application/json" -Body '{"project_path": "sample_project", "include_pattern": "**/*.py", "workers": 2}'

# 解析单个文件（需要认证）
Invoke-WebRequest -Uri http://localhost:8000/api/v1/parser/file -Method POST -ContentType "application/json" -Body '{"file_path": "sample_project/src/main.py"}'
```


---

## 完整使用示例

以下是一个使用sample_project的完整工作流程：

```bash
# 1. 检查系统健康状态
python -m src.codenexus health

# 2. 解析sample_project项目
python -m src.codenexus parse sample_project -o analysis

# 3. 查看图谱信息
python -m src.codenexus graph-info -p sample_project

# 4. 生成文档
python -m src.codenexus docs -o docs --format markdown -p sample_project

# 5. 进行智能问答
python -m src.codenexus qa -q "这个项目的主要功能是什么？" -p sample_project

# 6. 影响分析
python -m src.codenexus analyze -f sample_project/src/main.py -c "修改主函数入口" --depth 3

# 7. 导出知识图谱
python -m src.codenexus graph-export -o knowledge_graph.json -p sample_project --format json
```

---

## 环境变量

- `AI_API_KEY`: AI服务的API密钥（可选）
- `AI_MODEL_NAME`: 使用的AI模型名称（可选，默认: gpt-3.5-turbo）
- `AI_API_BASE`: AI服务的API基础URL（可选）
- `NEO4J_URI`: Neo4j数据库URI（可选，用于图数据库持久化）
- `NEO4J_USER`: Neo4j用户名（可选）
- `NEO4J_PASSWORD`: Neo4j密码（可选）
- `REDIS_HOST`: Redis服务器主机（可选，用于缓存）
- `REDIS_PORT`: Redis服务器端口（可选）
- `SERVER_HOST`: API服务器主机（可选，默认: 0.0.0.0）
- `SERVER_PORT`: API服务器端口（可选，默认: 8000）
- `SERVER_DEBUG`: 调试模式（可选，默认: false）

---

## 常见问题

### Q: 如何处理解析大型项目时的内存不足问题？
A: 可以通过以下方式优化：
- 减少并行工作线程数：`--workers 1`
- 使用文件过滤：`--include "**/*.py"`
- 分批解析：先解析核心模块，再解析其他模块

### Q: AI问答功能返回的结果不准确怎么办？
A: 可以尝试以下方法：
- 检查知识图谱是否完整构建
- 确认AI模型配置是否正确
- 提供更具体的问题描述
- 使用`--project-path`指定正确的项目路径

### Q: 如何备份和恢复知识图谱？
A: 使用以下命令：
```bash
# 导出图谱
python -m src.codenexus graph-export -o backup.json --format json

# 恢复图谱（将备份文件复制到项目目录）
cp backup.json .codenexus/knowledge_graph.json
```

---

## API端点状态说明

### ✅ 正常工作的端点
- 健康检查（基本和详细）
- 解析器（语言列表、项目解析、文件解析）
- 文档模板获取

### ❌ 需要数据库服务的端点
- 知识图谱统计和查询
- 文档生成
- 智能问答

### 解决方案
1. 启动Neo4j数据库服务
2. 检查数据库连接配置
3. 确保AI服务配置正确
4. 重新加载知识图谱数据

### PowerShell命令格式说明
本手册中的API命令已更新为PowerShell格式，适用于Windows环境。如果您使用Linux或macOS，可以将`Invoke-WebRequest`替换为相应的curl命令。

---

## 注意事项

1. 所有CLI命令都使用 `python -m src.codenexus` 前缀
2. API端点都需要 `/api/v1` 前缀
3. 部分API端点需要用户认证
4. 大型项目可能需要更多内存和处理时间
5. 建议在虚拟环境中运行以避免依赖冲突