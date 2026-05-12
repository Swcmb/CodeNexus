# codenexus AI智能层

AI智能层是codenexus系统的核心组件之一，提供基于大语言模型的智能代码分析、文档生成、问答和风险检测功能。

## 功能特性

- **智能文档生成**: 基于代码结构和上下文自动生成高质量的技术文档
- **自然语言问答**: 回答关于代码结构、功能和实现的问题
- **代码质量分析**: 评估代码质量并提供改进建议
- **风险检测**: 识别潜在的安全风险和架构问题
- **多模型支持**: 支持DeepSeek-Coder、Qwen-Coder等多种大语言模型

## 快速开始

### 1. 配置AI层

```python
from codenexus.config import Config, AIConfig
from codenexus.ai import create_ai_layer

# 创建配置
config = Config()
config.ai = AIConfig(
    model_name="deepseek-coder",
    api_key="your-api-key",
    api_base="https://api.deepseek.com/v1",
    max_tokens=4000,
    temperature=0.1
)

# 创建AI层实例
ai_layer = create_ai_layer(config)
```

### 2. 初始化AI层

```python
# 异步初始化
await ai_layer.initialize()

# 或使用工厂函数直接创建已初始化的实例
from codenexus.ai import create_and_initialize_ai_layer
ai_layer = await create_and_initialize_ai_layer(config)
```

### 3. 生成文档

```python
from codenexus.models.core import CodeElement, ElementType

# 创建代码元素
code_element = CodeElement(
    name="calculate_sum",
    type=ElementType.FUNCTION,
    file_path="/src/utils.py",
    line_number=10,
    complexity=3,
    metadata={
        "parameters": ["a: int", "b: int"],
        "returns": "int",
        "description": "计算两个数的和"
    }
)

# 生成文档
context = {
    "code_element": code_element,
    "related_elements": [],
    "graph_context": {"module": "utils"}
}

documentation = await ai_layer.generate_documentation(context)
print(documentation)
```

### 4. 问答功能

```python
# 提问
question = "这个函数的作用是什么？"
context = {
    "relevant_elements": [code_element],
    "call_chain": ["main", "process", "calculate_sum"]
}

answer = await ai_layer.answer_question(question, context)
print(f"问题: {question}")
print(f"回答: {answer}")
```

### 5. 代码质量分析

```python
# 分析代码质量
quality_result = await ai_layer.analyze_code_quality(code_element)

print(f"质量评分: {quality_result['score']}")
print(f"发现的问题: {quality_result['issues']}")
print(f"改进建议: {quality_result['suggestions']}")
```

### 6. 清理资源

```python
# 清理资源
await ai_layer.cleanup()
```

## 配置选项

### AIConfig参数

- `model_name`: 模型名称（如 "deepseek-coder", "qwen-coder"）
- `api_key`: API密钥
- `api_base`: API基础URL
- `max_tokens`: 最大token数（默认4000）
- `temperature`: 温度参数，控制输出随机性（默认0.1）
- `timeout`: 请求超时时间（默认30秒）

### 环境变量配置

可以通过环境变量配置AI层：

```bash
export AI_MODEL_NAME="deepseek-coder"
export AI_API_KEY="your-api-key"
export AI_API_BASE="https://api.deepseek.com/v1"
export AI_MAX_TOKENS="4000"
export AI_TEMPERATURE="0.1"
export AI_TIMEOUT="30"
```

## 支持的模型

### DeepSeek-Coder
- 专门针对代码理解和生成优化
- 支持多种编程语言
- 配置示例：
  ```python
  config.ai.model_name = "deepseek-coder"
  config.ai.api_base = "https://api.deepseek.com/v1"
  ```

### Qwen-Coder
- 阿里云通义千问代码模型
- 强大的中文代码理解能力
- 配置示例：
  ```python
  config.ai.model_name = "qwen-coder"
  config.ai.api_base = "https://dashscope.aliyuncs.com/compatible-mode/v1"
  ```

### 其他OpenAI兼容模型
- 支持任何兼容OpenAI API格式的模型
- 只需配置正确的`api_base`和`model_name`

## 错误处理

AI层提供了完善的错误处理机制：

```python
from codenexus.exceptions import AILayerError, ConfigurationError

try:
    await ai_layer.initialize()
except ConfigurationError as e:
    print(f"配置错误: {e}")
except AILayerError as e:
    print(f"AI层错误: {e}")
```

## 最佳实践

1. **资源管理**: 始终在使用完毕后调用`cleanup()`方法
2. **错误处理**: 捕获并处理可能的异常
3. **配置安全**: 不要在代码中硬编码API密钥，使用环境变量
4. **上下文优化**: 提供尽可能详细的上下文信息以获得更好的结果
5. **批量处理**: 对于大量请求，考虑实现批量处理和限流

## 示例

查看 `examples/ai_layer_demo.py` 获取完整的使用示例。

## 故障排除

### 常见问题

1. **API密钥错误**
   - 检查API密钥是否正确设置
   - 确认API密钥有足够的权限

2. **网络连接问题**
   - 检查网络连接
   - 确认API基础URL是否正确

3. **模型响应异常**
   - 检查请求参数是否合理
   - 尝试调整temperature和max_tokens参数

4. **内存使用过高**
   - 及时调用cleanup()方法
   - 考虑分批处理大量请求

### 调试模式

启用详细日志以便调试：

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 贡献

欢迎提交问题和改进建议！请确保：

1. 遵循代码风格规范
2. 添加适当的测试
3. 更新相关文档
4. 提供清晰的提交信息