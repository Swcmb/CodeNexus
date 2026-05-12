"""
问答服务演示

展示如何使用QAService处理自然语言问题并定位相关代码。
"""

import asyncio
import logging
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from codenexus.ai.ai_layer import AILayer
from codenexus.config import get_settings
from codenexus.database.graph_database import GraphDatabase
from codenexus.graph.graph_builder import GraphBuilder
from codenexus.models.core import CodeElement, CodeGraph, GraphNode, GraphEdge, ElementType, RelationType
from codenexus.parser.tree_sitter_parser import TreeSitterParser
from codenexus.services.qa_service import QAService


# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def create_sample_graph() -> CodeGraph:
    """创建示例代码图谱"""
    # 创建示例代码元素
    elements = [
        CodeElement(
            name="UserService",
            type=ElementType.CLASS,
            file_path="src/services/user_service.py",
            line_number=10,
            complexity=5,
            metadata={"description": "用户服务类，处理用户相关操作"}
        ),
        CodeElement(
            name="create_user",
            type=ElementType.METHOD,
            file_path="src/services/user_service.py",
            line_number=20,
            complexity=3,
            metadata={"description": "创建新用户"}
        ),
        CodeElement(
            name="get_user",
            type=ElementType.METHOD,
            file_path="src/services/user_service.py",
            line_number=35,
            complexity=2,
            metadata={"description": "获取用户信息"}
        ),
        CodeElement(
            name="DatabaseConnection",
            type=ElementType.CLASS,
            file_path="src/database/connection.py",
            line_number=5,
            complexity=4,
            metadata={"description": "数据库连接类"}
        ),
        CodeElement(
            name="execute_query",
            type=ElementType.METHOD,
            file_path="src/database/connection.py",
            line_number=15,
            complexity=3,
            metadata={"description": "执行数据库查询"}
        )
    ]
    
    # 创建图节点
    nodes = [GraphNode(id=f"node_{i}", label=elem.name, type=elem.type.value, properties={"element": elem.__dict__}) for i, elem in enumerate(elements)]
    
    # 创建图边（关系）
    edges = [
        GraphEdge(
            source_id=nodes[1].id,  # create_user
            target_id=nodes[4].id,  # execute_query
            type=RelationType.CALLS.value,
            properties={"description": "create_user调用execute_query"}
        ),
        GraphEdge(
            source_id=nodes[2].id,  # get_user
            target_id=nodes[4].id,  # execute_query
            type=RelationType.CALLS.value,
            properties={"description": "get_user调用execute_query"}
        )
    ]
    
    # 创建代码图谱
    graph = CodeGraph(nodes=nodes, edges=edges)
    
    return graph


async def demo_basic_qa():
    """演示基本问答功能"""
    logger.info("=== 演示基本问答功能 ===")
    
    # 创建配置
    settings = get_settings()
    
    # 创建AI层
    ai_layer = AILayer(config=settings)
    
    # 创建图数据库
    graph_db = GraphDatabase()
    
    # 创建问答服务
    qa_service = QAService(ai_layer, graph_db)
    
    # 创建示例图谱
    graph = await create_sample_graph()
    
    # 测试问题列表
    questions = [
        "UserService类在哪里？",
        "如何创建用户？",
        "create_user方法调用了哪些函数？",
        "数据库连接是如何实现的？",
        "get_user方法的作用是什么？"
    ]
    
    for question in questions:
        logger.info(f"\n问题: {question}")
        
        try:
            # 处理问题
            result = await qa_service.process_question(question, graph)
            
            logger.info(f"问题类型: {result['question_type']}")
            logger.info(f"关键词: {result['keywords']}")
            logger.info(f"找到 {len(result['relevant_code'])} 个相关代码元素")
            
            if result['relevant_code']:
                logger.info("相关代码:")
                for code in result['relevant_code'][:3]:  # 只显示前3个
                    logger.info(f"  - {code['name']} ({code['type']}) in {code['file_path']}")
            
            if result['call_chains']:
                logger.info("调用链:")
                for chain in result['call_chains'][:2]:  # 只显示前2个
                    logger.info(f"  - {' -> '.join(chain)}")
            
            logger.info(f"置信度: {result['confidence']:.2f}")
            logger.info(f"答案: {result['answer'][:200]}...")  # 只显示前200个字符
            
        except Exception as e:
            logger.error(f"处理问题失败: {e}")
    
    # 清理资源
    # 图数据库会自动清理
    # AI层会自动清理


async def demo_code_location():
    """演示代码定位功能"""
    logger.info("\n=== 演示代码定位功能 ===")
    
    # 创建配置
    settings = get_settings()
    
    # 创建AI层
    ai_layer = await create_and_initialize_ai_layer(config)
    
    # 创建图数据库
    graph_db = MockGraphDatabase(config)
    await graph_db.connect()
    
    # 创建问答服务
    qa_service = QAService(ai_layer, graph_db)
    
    # 创建示例图谱
    graph = await create_sample_graph()
    
    # 测试代码定位
    test_questions = [
        "UserService",
        "create_user方法",
        "数据库查询"
    ]
    
    for question in test_questions:
        logger.info(f"\n查询: {question}")
        
        try:
            # 定位相关代码
            relevant_code = await qa_service.locate_relevant_code(question, graph)
            
            logger.info(f"找到 {len(relevant_code)} 个相关代码元素:")
            for code in relevant_code:
                logger.info(f"  - {code.name} ({code.type}) in {code.file_path}:{code.line_number}")
                logger.info(f"    复杂度: {code.complexity}")
                if code.metadata:
                    logger.info(f"    描述: {code.metadata.get('description', 'N/A')}")
        
        except Exception as e:
            logger.error(f"代码定位失败: {e}")
    
    # 清理资源
    await graph_db.disconnect()
    await ai_layer.cleanup()


async def demo_answer_generation():
    """演示答案生成功能"""
    logger.info("\n=== 演示答案生成功能 ===")
    
    # 创建配置
    config = Config()
    
    # 创建AI层
    ai_layer = await create_and_initialize_ai_layer(config)
    
    # 创建图数据库
    graph_db = MockGraphDatabase(config)
    await graph_db.connect()
    
    # 创建问答服务
    qa_service = QAService(ai_layer, graph_db)
    
    # 创建示例图谱
    graph = await create_sample_graph()
    
    # 测试问题
    question = "UserService类的主要功能是什么？"
    
    logger.info(f"问题: {question}")
    
    try:
        # 定位相关代码
        relevant_code = await qa_service.locate_relevant_code(question, graph)
        
        logger.info(f"找到 {len(relevant_code)} 个相关代码元素")
        
        # 生成答案
        answer = await qa_service.generate_answer(question, relevant_code)
        
        logger.info(f"\n答案:\n{answer}")
    
    except Exception as e:
        logger.error(f"答案生成失败: {e}")
    
    # 清理资源
    await graph_db.disconnect()
    await ai_layer.cleanup()


async def main():
    """主函数"""
    try:
        # 运行演示
        await demo_basic_qa()
        await demo_code_location()
        await demo_answer_generation()
        
        logger.info("\n=== 演示完成 ===")
    
    except Exception as e:
        logger.error(f"演示失败: {e}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(main())
