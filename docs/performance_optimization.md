# 性能优化和缓存使用指南

本文档介绍codenexus系统的性能优化和缓存功能。

## 功能概述

codenexus实现了以下性能优化功能：

1. **Redis缓存层** - 缓存查询结果，提高响应速度
2. **智能缓存策略** - 根据查询类型和结果大小自动调整缓存策略
3. **批处理和并行解析** - 优化大型项目的处理性能
4. **内存优化图构建** - 针对大型项目优化内存使用
5. **性能监控和自动调优** - 实时监控系统性能并提供优化建议

## 1. 缓存服务使用

### 1.1 基本配置

```python
from src.codenexus.services.cache_service import CacheService

# 初始化缓存服务
cache_service = CacheService(
    host="localhost",
    port=6379,
    db=0,
    password=None,  # 如果Redis设置了密码
    default_ttl=3600  # 默认缓存1小时
)

# 检查缓存是否可用
if cache_service.is_enabled():
    print("缓存服务已启用")
else:
    print("缓存服务未启用（Redis不可用）")
```

### 1.2 基本操作

```python
# 设置缓存
cache_service.set("my_key", {"data": "value"}, ttl=1800)  # 缓存30分钟

# 获取缓存
result = cache_service.get("my_key")
if result:
    print("缓存命中:", result)
else:
    print("缓存未命中")

# 删除缓存
cache_service.delete("my_key")

# 批量删除（使用模式匹配）
cache_service.delete_pattern("graph_query:*")

# 获取缓存统计信息
stats = cache_service.get_stats()
print(f"缓存命中率: {stats['hit_rate']:.2%}")
```

### 1.3 智能缓存策略

```python
from src.codenexus.services.cache_service import SmartCacheStrategy

# 初始化智能缓存策略
strategy = SmartCacheStrategy(cache_service)

# 获取查询类型的TTL
ttl = strategy.get_ttl("graph_query", result_size=500)

# 判断是否应该缓存结果
should_cache = strategy.should_cache("qa_answer", result)

# 使相关缓存失效
strategy.invalidate_related_cache("graph_id", ["node1", "node2"])
```

## 2. 批处理和并行解析

### 2.1 基本配置

```python
from src.codenexus.services.batch_processor import BatchProcessor, BatchConfig

# 配置批处理器
config = BatchConfig(
    batch_size=50,  # 每批处理50个文件
    max_workers=4,  # 使用4个工作进程
    memory_limit_mb=2048,  # 内存限制2GB
    timeout_seconds=300,  # 单个文件处理超时5分钟
    enable_gc=True,  # 启用垃圾回收优化
    chunk_size=10  # 每个工作进程处理10个文件
)

# 初始化批处理器
processor = BatchProcessor(config)
```

### 2.2 并行处理项目

```python
import asyncio

async def process_large_project():
    # 定义进度回调
    def progress_callback(processed, total):
        print(f"进度: {processed}/{total} ({processed/total*100:.1f}%)")
    
    # 并行处理项目
    results = await processor.process_project_parallel(
        project_path="/path/to/large/project",
        progress_callback=progress_callback
    )
    
    print(f"处理完成，共解析 {len(results)} 个文件")
    
    # 获取处理统计信息
    stats = processor.get_processing_stats()
    print(f"总耗时: {stats.total_time:.2f}秒")
    print(f"平均每文件: {stats.avg_time_per_file:.3f}秒")
    print(f"内存使用: {stats.memory_usage_mb:.1f}MB")

# 运行
asyncio.run(process_large_project())
```

### 2.3 流式处理（超大型项目）

```python
from src.codenexus.services.batch_processor import StreamingProcessor

# 定义结果处理函数
def handle_result(parse_result):
    # 立即处理结果，不在内存中累积
    print(f"处理文件: {parse_result.file_path}")
    # 可以直接存储到数据库或文件

# 初始化流式处理器
streaming_processor = StreamingProcessor(batch_size=10)

# 流式处理项目
async def stream_process():
    await streaming_processor.process_project_streaming(
        project_path="/path/to/huge/project",
        result_handler=handle_result,
        progress_callback=lambda p, t: print(f"{p}/{t}")
    )

asyncio.run(stream_process())
```

## 3. 内存优化图构建

### 3.1 使用内存优化图构建器

```python
from src.codenexus.graph.memory_optimized_builder import MemoryOptimizedGraphBuilder

# 初始化内存优化图构建器
builder = MemoryOptimizedGraphBuilder(memory_limit_mb=1024)

# 增量构建图谱
def parse_results_generator():
    # 生成解析结果的迭代器
    for result in results:
        yield result

graph = builder.build_graph_incremental(
    parse_results=parse_results_generator(),
    chunk_size=100  # 每次处理100个结果
)

# 获取构建统计信息
stats = builder.get_build_stats()
print(f"创建节点数: {stats['nodes_created']}")
print(f"创建边数: {stats['edges_created']}")
print(f"触发GC次数: {stats['gc_triggered']}")
```

### 3.2 流式图构建

```python
from src.codenexus.graph.memory_optimized_builder import GraphStreamBuilder

# 定义图谱片段处理函数
def handle_graph_fragment(graph_fragment):
    # 处理图谱片段，例如存储到数据库
    print(f"处理图谱片段: {len(graph_fragment.nodes)} 节点")

# 初始化流式图构建器
stream_builder = GraphStreamBuilder(output_handler=handle_graph_fragment)

# 添加解析结果
for result in parse_results:
    stream_builder.add_parse_result(result)

# 完成处理
stream_builder.finalize()
```

## 4. 性能监控和优化

### 4.1 启动性能监控

```python
from src.codenexus.services.performance_manager import (
    PerformanceManager, PerformanceThresholds
)

# 配置性能阈值
thresholds = PerformanceThresholds(
    cpu_warning=80.0,
    cpu_critical=95.0,
    memory_warning=80.0,
    memory_critical=95.0,
    response_time_warning=5.0,
    response_time_critical=10.0
)

# 初始化性能管理器
perf_manager = PerformanceManager(
    thresholds=thresholds,
    monitoring_interval=5.0  # 每5秒监控一次
)

# 启动监控
perf_manager.start_monitoring()

# ... 运行应用程序 ...

# 停止监控
perf_manager.stop_monitoring()
```

### 4.2 获取性能摘要

```python
# 获取性能摘要
summary = perf_manager.get_performance_summary()
print(f"状态: {summary['status']}")
print(f"平均CPU: {summary['summary']['avg_cpu_percent']}%")
print(f"平均内存: {summary['summary']['avg_memory_mb']}MB")
```

### 4.3 获取优化建议

```python
# 获取优化建议
suggestions = perf_manager.get_optimization_suggestions()

for suggestion in suggestions:
    print(f"[{suggestion.priority}] {suggestion.title}")
    print(f"  {suggestion.description}")
    
    # 应用优化（如果有可执行的动作）
    if suggestion.action:
        perf_manager.apply_optimization(suggestion)
```

### 4.4 监控异步操作

```python
from src.codenexus.services.performance_manager import AsyncPerformanceManager

# 初始化异步性能管理器
async_perf = AsyncPerformanceManager(perf_manager)

# 监控异步操作
async def my_operation():
    # 执行一些操作
    await asyncio.sleep(1)
    return "result"

result = await async_perf.monitor_async_operation(
    operation_name="my_operation",
    operation_coro=my_operation()
)
```

## 5. 集成示例

### 5.1 完整的优化配置

```python
from src.codenexus.services.cache_service import CacheService
from src.codenexus.services.batch_processor import BatchProcessor, BatchConfig
from src.codenexus.services.performance_manager import PerformanceManager
from src.codenexus.database.query_service import GraphQueryService
from src.codenexus.services.qa_service import QAService

# 1. 初始化缓存服务
cache_service = CacheService(
    host="localhost",
    port=6379,
    default_ttl=3600
)

# 2. 初始化查询服务（带缓存）
query_service = GraphQueryService(
    database=graph_database,
    cache_service=cache_service
)

# 3. 初始化QA服务（带缓存）
qa_service = QAService(
    ai_layer=ai_layer,
    graph_db=graph_database,
    cache_service=cache_service
)

# 4. 初始化批处理器
batch_config = BatchConfig(
    batch_size=50,
    max_workers=4,
    memory_limit_mb=2048
)
batch_processor = BatchProcessor(batch_config)

# 5. 启动性能监控
perf_manager = PerformanceManager()
perf_manager.start_monitoring()

# 6. 处理大型项目
async def process_and_analyze():
    # 并行解析项目
    results = await batch_processor.process_project_parallel(
        project_path="/path/to/project"
    )
    
    # 构建图谱（使用内存优化）
    from src.codenexus.graph.memory_optimized_builder import MemoryOptimizedGraphBuilder
    builder = MemoryOptimizedGraphBuilder()
    graph = builder.build_graph_incremental(iter(results))
    
    # 存储到数据库
    graph_database.store_graph(graph)
    
    # 执行查询（自动使用缓存）
    impact_result = query_service.analyze_impact(
        graph_id=graph.id,
        changed_node_ids=["node1"]
    )
    
    # 获取性能摘要
    summary = perf_manager.get_performance_summary()
    print(f"性能状态: {summary['status']}")

asyncio.run(process_and_analyze())
```

## 6. 最佳实践

### 6.1 缓存策略

- 对于频繁查询的数据，使用较长的TTL（1-2小时）
- 对于实时性要求高的数据，使用较短的TTL（5-15分钟）
- 当代码发生变更时，及时清除相关缓存
- 定期监控缓存命中率，调整缓存策略

### 6.2 批处理优化

- 根据系统资源调整`max_workers`和`batch_size`
- 对于超大型项目（>10万文件），使用流式处理
- 设置合理的内存限制，避免OOM
- 使用进度回调监控处理进度

### 6.3 内存管理

- 对于大型项目，使用内存优化图构建器
- 定期触发垃圾回收，释放内存
- 监控内存使用情况，及时调整配置
- 使用流式处理避免内存累积

### 6.4 性能监控

- 始终启用性能监控，及时发现问题
- 定期查看优化建议，应用高优先级优化
- 监控关键操作的响应时间
- 设置合理的性能阈值

## 7. 故障排查

### 7.1 缓存问题

**问题**: 缓存服务未启用
- 检查Redis是否正常运行
- 验证连接配置（host、port、password）
- 查看日志中的错误信息

**问题**: 缓存命中率低
- 检查TTL设置是否合理
- 验证缓存键生成逻辑
- 分析查询模式，调整缓存策略

### 7.2 性能问题

**问题**: 内存使用过高
- 减少批处理大小
- 使用流式处理
- 增加垃圾回收频率
- 使用内存优化图构建器

**问题**: CPU使用率过高
- 减少并发工作进程数
- 优化算法复杂度
- 使用缓存减少重复计算

**问题**: 处理速度慢
- 增加并发工作进程数
- 使用批处理和并行解析
- 启用缓存
- 优化数据库查询

## 8. 配置参考

### 8.1 推荐配置（小型项目 <1000文件）

```python
cache_config = {
    "default_ttl": 1800,  # 30分钟
}

batch_config = BatchConfig(
    batch_size=20,
    max_workers=2,
    memory_limit_mb=512
)
```

### 8.2 推荐配置（中型项目 1000-10000文件）

```python
cache_config = {
    "default_ttl": 3600,  # 1小时
}

batch_config = BatchConfig(
    batch_size=50,
    max_workers=4,
    memory_limit_mb=2048
)
```

### 8.3 推荐配置（大型项目 >10000文件）

```python
cache_config = {
    "default_ttl": 7200,  # 2小时
}

batch_config = BatchConfig(
    batch_size=100,
    max_workers=8,
    memory_limit_mb=4096
)

# 使用流式处理
use_streaming = True
```

## 总结

codenexus的性能优化和缓存功能为处理大型项目提供了强大的支持。通过合理配置和使用这些功能，可以显著提高系统的性能和响应速度。建议根据实际项目规模和系统资源，选择合适的配置和策略。