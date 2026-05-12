# DocumentationGenerator 使用指南

DocumentationGenerator 是 codenexus 系统中的智能文档生成器，能够基于代码上下文和知识图谱信息生成高质量的技术文档。

## 功能特性

- **API文档生成**: 为函数、方法生成包含签名、参数、返回值和使用示例的详细文档
- **模块文档生成**: 为模块生成包含概述、架构设计、主要功能的综合文档
- **类文档生成**: 为类生成包含构造函数、方法、属性的完整文档
- **HTML转换**: 将Markdown文档转换为格式化的HTML文档
- **智能格式化**: 自动添加缺失的文档章节和结构化信息

## 快速开始

### 1. 创建文档生成器

```python
from codenexus.ai import create_and_initialize_documentation_generator
from codenexus.config import Config

# 配置AI层
config = Config()
config.ai.api_key = "your-api-key"
config.ai.api_base = "https://api.deepseek.com/v1"
config.ai.model_name = "deepseek-coder"

# 创建并初始化文档生成器
doc_generator = await create_and_initialize_documentation_generator(config)
```

### 2. 生成API文档

```python
from codenexus.models.core import CodeElement, ElementType

# 创建代码元素
code_element = CodeElement(
    name="calculate_fibonacci",
    type=ElementType.FUNCTION,
    file_path="src/math_utils.py",
    line_number=15,
    parameters=["n: int"],
    return_type="int",
    docstring="计算斐波那契数列的第n项",
    complexity=3
)

# 生成API文档
api_doc = await doc_generator.generate_api_documentation(
    code_element=code_element,
    related_elements=[],
    graph_context={"callers": ["main", "test_fibonacci"]}
)

print(api_doc)
```

### 3. 生成模块文档

```python
# 创建模块元素列表
module_elements = [
    CodeElement(name="MathUtils", type=ElementType.CLASS, file_path="src/math_utils.py"),
    CodeElement(name="calculate_fibonacci", type=ElementType.FUNCTION, file_path="src/math_utils.py"),
    CodeElement(name="calculate_factorial", type=ElementType.FUNCTION, file_path="src/math_utils.py")
]

# 生成模块文档
module_doc = await doc_generator.generate_module_documentation(
    module_elements=module_elements,
    module_name="math_utils",
    graph=None  # 可选：传入代码知识图谱
)

print(module_doc)
```

### 4. 生成类文档

```python
# 创建类元素
class_element = CodeElement(
    name="Calculator",
    type=ElementType.CLASS,
    file_path="src/calculator.py",
    docstring="计算器类，提供基本数学运算功能"
)

# 创建方法和字段列表
methods = [
    CodeElement(name="__init__", type=ElementType.METHOD, docstring="初始化计算器"),
    CodeElement(name="add", type=ElementType.METHOD, docstring="加法运算"),
    CodeElement(name="multiply", type=ElementType.METHOD, docstring="乘法运算")
]

fields = [
    CodeElement(name="precision", type=ElementType.FIELD, docstring="计算精度")
]

# 生成类文档
class_doc = await doc_generator.generate_class_documentation(
    class_element=class_element,
    methods=methods,
    fields=fields,
    graph_context={"inheritance": [], "interfaces": []}
)

print(class_doc)
```

### 5. 转换为HTML

```python
# 将Markdown文档转换为HTML
html_doc = doc_generator.convert_to_html(api_doc)

# 保存HTML文档
with open("api_documentation.html", "w", encoding="utf-8") as f:
    f.write(html_doc)
```

## 文档结构

### API文档结构

生成的API文档包含以下章节：

- **文档头部**: 包含元素名称、类型、文件路径、生成时间等信息
- **函数签名**: 自动生成的函数或方法签名（如适用）
- **概述**: 功能描述和用途说明
- **参数**: 参数列表和类型说明
- **返回值**: 返回值类型和描述
- **使用示例**: 代码使用示例
- **依赖关系**: 相关依赖和调用关系
- **注意事项**: 使用注意事项和限制

### 模块文档结构

生成的模块文档包含以下章节：

- **文档头部**: 模块名称、元素数量、生成时间
- **概述**: 模块功能和用途概述
- **主要功能**: 模块提供的主要功能列表
- **架构设计**: 模块的架构设计说明
- **使用指南**: 模块使用方法和最佳实践
- **API参考**: 模块中类和函数的索引

### 类文档结构

生成的类文档包含以下章节：

- **文档头部**: 类名称、文件信息、方法和字段数量
- **概述**: 类的功能和用途描述
- **构造函数**: 构造函数说明
- **方法**: 类方法的详细说明
- **属性**: 类属性和字段说明
- **使用示例**: 类的使用示例

## 配置选项

DocumentationGenerator 支持以下配置选项：

### AI层配置

```python
config.ai.api_key = "your-api-key"          # AI服务API密钥
config.ai.api_base = "https://api.xxx.com"  # AI服务API基础URL
config.ai.model_name = "deepseek-coder"     # 使用的模型名称
config.ai.max_tokens = 4000                 # 最大token数
config.ai.temperature = 0.1                 # 温度参数
config.ai.timeout = 30                      # 请求超时时间
```

## 错误处理

DocumentationGenerator 提供完善的错误处理机制：

```python
from codenexus.exceptions import DocumentationError

try:
    doc = await doc_generator.generate_api_documentation(code_element)
except DocumentationError as e:
    print(f"文档生成失败: {e}")
    # 处理错误...
```

## 最佳实践

1. **提供完整的代码元素信息**: 包含docstring、参数类型、返回类型等信息能够生成更高质量的文档

2. **使用图谱上下文**: 提供相关元素和图谱上下文信息能够生成更准确的依赖关系说明

3. **批量处理**: 对于大量文档生成任务，建议使用异步处理和适当的并发控制

4. **缓存结果**: 对于不经常变化的代码，可以缓存生成的文档以提高性能

5. **定期更新**: 当代码发生变化时，及时更新相关文档以保持一致性

## 示例项目

查看 `examples/documentation_generator_demo.py` 获取完整的使用示例。

## 注意事项

- DocumentationGenerator 需要有效的AI API配置才能正常工作
- 生成的文档质量依赖于提供的代码上下文信息的完整性
- HTML转换功能需要安装 `markdown` 依赖包
- 大型项目的文档生成可能需要较长时间，建议使用异步处理