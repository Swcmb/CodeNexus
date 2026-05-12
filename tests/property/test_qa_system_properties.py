"""
问答系统属性测试

**Feature: code-weaver, Property 7: 问答系统准确性**
**验证需求: 需求 5.1, 5.2, 5.3, 5.4**

对于任意自然语言问题，系统应该正确理解问题意图，定位到相关的代码区域，
并生成包含准确代码引用和完整调用链路的答案。
"""

import asyncio
import pytest
from hypothesis import given, strategies as st, settings, assume, HealthCheck
from unittest.mock import AsyncMock, MagicMock

from src.codenexus.ai.ai_layer import AILayer
from src.codenexus.config import Config
from src.codenexus.database.mock_database import MockGraphDatabase
from src.codenexus.models.core import CodeElement, CodeGraph, GraphNode, GraphEdge
from src.codenexus.services.qa_service import QAService


class TestQASystemPropertiesSync:
    """问答系统属性测试类（同步版本）"""
    
    @pytest.fixture
    def config(self):
        """创建测试配置"""
        return Config()
    
    @pytest.fixture
    def mock_ai_layer(self):
        """创建模拟AI层"""
        ai_layer = AsyncMock(spec=AILayer)
        ai_layer.answer_question.return_value = "这是一个测试答案，包含了相关的代码引用和调用链路信息。"
        return ai_layer
    
    @pytest.fixture
    def mock_graph_db(self):
        """创建模拟图数据库"""
        return MockGraphDatabase()
    
    @pytest.fixture
    def qa_service(self, mock_ai_layer, mock_graph_db):
        """创建问答服务实例"""
        return QAService(mock_ai_layer, mock_graph_db)
    
    @given(code_graph_strategy(), question_strategy())
    @settings(max_examples=10, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_qa_system_accuracy_property_sync(self, qa_service, graph, question):
        """
        **Feature: code-weaver, Property 7: 问答系统准确性**
        **验证需求: 需求 5.1, 5.2, 5.3, 5.4**
        
        属性：对于任意问题和图谱，问答系统应该返回包含相关代码引用的答案。
        """
        # 确保图谱不为空
        assume(len(graph.nodes) > 0)
        assume(len(question.strip()) > 0)
        
        async def run_test():
            # 处理问题
            result = await qa_service.process_question(question, graph)
            
            # 验证结果结构
            assert isinstance(result, dict)
            assert "answer" in result
            assert "relevant_code" in result
            assert "confidence" in result
            
            # 验证答案不为空
            assert len(result["answer"]) > 0
            
            # 验证置信度在合理范围内
            assert 0.0 <= result["confidence"] <= 1.0
        
        # 运行异步测试
        asyncio.run(run_test())
    
    @given(code_graph_strategy())
    @settings(max_examples=10, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_code_location_completeness_property_sync(self, qa_service, graph):
        """
        **Feature: code-weaver, Property 7: 问答系统准确性**
        **验证需求: 需求 5.1, 5.2**
        
        属性：代码定位应该完整 - 能找到图谱中存在的代码元素。
        """
        # 确保图谱不为空
        assume(len(graph.nodes) > 0)
        
        async def run_test():
            # 选择一个存在的节点
            target_node = graph.nodes[0]
            element = target_node.get_property("element")
            if element:
                question = f"{element.name}在哪里？"
                
                # 定位相关代码
                relevant_code = await qa_service.locate_relevant_code(question, graph)
                
                # 应该能找到目标元素
                found_names = [elem.name for elem in relevant_code]
                assert element.name in found_names, f"应该能找到元素 {element.name}"
        
        # 运行异步测试
        asyncio.run(run_test())
    
    @given(code_graph_strategy(), st.lists(st.text(min_size=1, max_size=10), min_size=1, max_size=5))
    @settings(max_examples=10, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_keyword_extraction_consistency_property_sync(self, qa_service, graph, keywords):
        """
        **Feature: code-weaver, Property 7: 问答系统准确性**
        **验证需求: 需求 5.1**
        
        属性：关键词提取应该一致 - 相同的问题应该提取出相同的关键词。
        """
        # 构造包含关键词的问题
        question = f"请告诉我关于 {' '.join(keywords)} 的信息"
        
        # 多次提取关键词
        extracted1 = qa_service._extract_keywords(question)
        extracted2 = qa_service._extract_keywords(question)
        
        # 结果应该一致
        assert extracted1 == extracted2
        
        # 应该包含原始关键词中的一些
        for keyword in keywords:
            if len(keyword) > 1:  # 过滤太短的关键词
                assert keyword in extracted1 or any(keyword in ext for ext in extracted1)
    
    @given(code_graph_strategy())
    @settings(max_examples=10, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_question_type_classification_property_sync(self, qa_service, graph):
        """
        **Feature: code-weaver, Property 7: 问答系统准确性**
        **验证需求: 需求 5.1**
        
        属性：问题类型分类应该准确 - 特定模式的问题应该被正确分类。
        """
        test_cases = [
            ("如何调用UserService的方法？", "function_call"),
            ("UserClass继承了哪些类？", "inheritance"),
            ("模块A依赖哪些模块？", "dependency"),
            ("UserService的实现在哪里？", "implementation"),
            ("系统的架构是什么样的？", "structure"),
            ("UserClass在哪个文件？", "location")
        ]
        
        for question, expected_type in test_cases:
            classified_type = qa_service._analyze_question_type(question)
            assert classified_type == expected_type, \
                f"问题 '{question}' 应该被分类为 '{expected_type}'，但得到 '{classified_type}'"
    
    @given(code_graph_strategy())
    @settings(max_examples=10, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_confidence_calculation_property_sync(self, qa_service, graph):
        """
        **Feature: code-weaver, Property 7: 问答系统准确性**
        **验证需求: 需求 5.4**
        
        属性：置信度计算应该合理 - 更多相关代码应该产生更高的置信度。
        """
        # 确保图谱不为空
        assume(len(graph.nodes) > 0)
        
        # 测试不同数量的相关代码对置信度的影响
        keywords = ["test"]
        
        # 空的相关代码应该产生0置信度
        confidence_empty = qa_service._calculate_confidence([], keywords)
        assert confidence_empty == 0.0
        
        # 有相关代码应该产生正的置信度
        if graph.nodes:
            element = graph.nodes[0].get_property("element")
            if element:
                confidence_with_code = qa_service._calculate_confidence([element], keywords)
                assert 0.0 <= confidence_with_code <= 1.0
    
    @given(code_graph_strategy())
    @settings(max_examples=10, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_answer_generation_completeness_property_sync(self, qa_service, graph):
        """
        **Feature: code-weaver, Property 7: 问答系统准确性**
        **验证需求: 需求 5.2, 5.3**
        
        属性：答案生成应该完整 - 包含调用链路和代码引用。
        """
        # 确保图谱不为空
        assume(len(graph.nodes) > 0)
        
        async def run_test():
            question = "这个系统是如何工作的？"
            
            # 生成答案
            relevant_code = []
            if graph.nodes:
                element = graph.nodes[0].get_property("element")
                if element:
                    relevant_code = [element]
            
            answer = await qa_service.generate_answer(question, relevant_code)
            
            # 答案应该不为空
            assert isinstance(answer, str)
            assert len(answer) > 0
            
            # 如果有相关代码，答案应该足够详细
            if relevant_code:
                assert len(answer) >= 10
        
        # 运行异步测试
        asyncio.run(run_test())
    """问答系统属性测试类"""
    
    @pytest.fixture
    def config(self):
        """创建测试配置"""
        return Config()
    
    @pytest.fixture
    def mock_ai_layer(self):
        """创建模拟AI层"""
        ai_layer = AsyncMock(spec=AILayer)
        ai_layer.answer_question.return_value = "这是一个测试答案，包含了相关的代码引用和调用链路信息。"
        return ai_layer
    
    @pytest.fixture
    def mock_graph_db(self):
        """创建模拟图数据库"""
        return MockGraphDatabase()
    
    @pytest.fixture
    def qa_service(self, mock_ai_layer, mock_graph_db):
        """创建问答服务实例"""
        return QAService(mock_ai_layer, mock_graph_db)
    
    # 生成策略
    @st.composite
    def code_element_strategy(draw):
        """生成代码元素的策略"""
        element_types = ["class", "method", "function", "variable", "interface", "module"]
        
        name = draw(st.text(
            alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd"), min_codepoint=65, max_codepoint=122),
            min_size=3,
            max_size=20
        ).filter(lambda x: x.isidentifier()))
        
        element_type = draw(st.sampled_from(element_types))
        file_path = draw(st.text(min_size=5, max_size=50).map(lambda x: f"src/{x.replace(' ', '_')}.py"))
        line_number = draw(st.integers(min_value=1, max_value=1000))
        complexity = draw(st.integers(min_value=1, max_value=20))
        
        return CodeElement(
            name=name,
            type=element_type,
            file_path=file_path,
            line_number=line_number,
            complexity=complexity,
            metadata={"description": f"{element_type} {name}"}
        )
    
    @st.composite
    def code_graph_strategy(draw):
        """生成代码图谱的策略"""
        # 生成1-10个代码元素
        num_elements = draw(st.integers(min_value=1, max_value=10))
        elements = draw(st.lists(
            TestQASystemProperties.code_element_strategy(),
            min_size=num_elements,
            max_size=num_elements,
            unique_by=lambda x: (x.name, x.file_path, x.line_number)
        ))
        
        # 创建图节点
        nodes = []
        for i, elem in enumerate(elements):
            node = GraphNode(id=f"node_{i}", label=elem.name, type=elem.type)
            node.set_property("element", elem)
            nodes.append(node)
        
        # 生成一些边（关系）
        edges = []
        if len(nodes) > 1:
            num_edges = draw(st.integers(min_value=0, max_value=min(5, len(nodes) - 1)))
            for i in range(num_edges):
                source_idx = draw(st.integers(min_value=0, max_value=len(nodes) - 1))
                target_idx = draw(st.integers(min_value=0, max_value=len(nodes) - 1))
                
                if source_idx != target_idx:  # 避免自环
                    edge_type = draw(st.sampled_from(["calls", "inherits", "depends", "uses"]))
                    edge = GraphEdge(
                        id=f"edge_{i}",
                        source_id=nodes[source_idx].id,
                        target_id=nodes[target_idx].id,
                        type=edge_type
                    )
                    edges.append(edge)
        
        return CodeGraph(nodes=nodes, edges=edges)
    
    @st.composite
    def question_strategy(draw):
        """生成自然语言问题的策略"""
        question_templates = [
            "{name}类在哪里？",
            "{name}方法的作用是什么？",
            "如何调用{name}函数？",
            "{name}的实现在哪个文件？",
            "哪些类继承了{name}？",
            "{name}依赖哪些模块？",
            "What is the purpose of {name}?",
            "How to use {name} method?",
            "Where is {name} implemented?",
            "What does {name} function do?"
        ]
        
        template = draw(st.sampled_from(question_templates))
        # 生成一个合理的标识符作为名称
        name = draw(st.text(
            alphabet=st.characters(whitelist_categories=("Lu", "Ll"), min_codepoint=65, max_codepoint=122),
            min_size=3,
            max_size=15
        ).filter(lambda x: x.isalpha()))
        
        return template.format(name=name)
    
    @given(code_graph_strategy(), question_strategy())
    @settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    async def test_qa_system_accuracy_property(self, qa_service, graph, question):
        """
        **Feature: code-weaver, Property 7: 问答系统准确性**
        **验证需求: 需求 5.1, 5.2, 5.3, 5.4**
        
        属性：对于任意自然语言问题和代码图谱，问答系统应该：
        1. 正确理解问题意图并分类
        2. 定位到相关的代码区域
        3. 生成包含准确代码引用的答案
        4. 提供合理的置信度评估
        """
        # 确保图谱不为空
        assume(len(graph.nodes) > 0)
        
        try:
            # 处理问题
            result = await qa_service.process_question(question, graph)
            
            # 验证返回结果的结构完整性
            assert isinstance(result, dict)
            assert "question" in result
            assert "question_type" in result
            assert "keywords" in result
            assert "relevant_code" in result
            assert "answer" in result
            assert "confidence" in result
            
            # 验证问题理解准确性
            assert result["question"] == question
            assert isinstance(result["question_type"], str)
            assert len(result["question_type"]) > 0
            
            # 验证关键词提取
            assert isinstance(result["keywords"], list)
            # 关键词应该从问题中提取出来
            if result["keywords"]:
                # 至少有一个关键词应该在原问题中出现
                question_lower = question.lower()
                keyword_found = any(kw.lower() in question_lower for kw in result["keywords"])
                assert keyword_found, f"关键词 {result['keywords']} 应该在问题 '{question}' 中出现"
            
            # 验证代码定位准确性
            assert isinstance(result["relevant_code"], list)
            for code_elem in result["relevant_code"]:
                assert isinstance(code_elem, dict)
                assert "name" in code_elem
                assert "type" in code_elem
                assert "file_path" in code_elem
                assert "line_number" in code_elem
            
            # 验证答案生成
            assert isinstance(result["answer"], str)
            assert len(result["answer"]) > 0
            
            # 验证置信度合理性
            assert isinstance(result["confidence"], (int, float))
            assert 0.0 <= result["confidence"] <= 1.0
            
            # 如果找到了相关代码，置信度应该大于0
            if result["relevant_code"]:
                assert result["confidence"] > 0.0
            
        except Exception as e:
            pytest.fail(f"问答系统处理失败: {e}")
    
    @given(code_graph_strategy())
    @settings(max_examples=30, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    async def test_code_location_completeness_property(self, qa_service, graph):
        """
        **Feature: code-weaver, Property 7: 问答系统准确性**
        **验证需求: 需求 5.1, 5.2**
        
        属性：当问题中包含图谱中存在的代码元素名称时，
        系统应该能够准确定位到该代码元素。
        """
        assume(len(graph.nodes) > 0)
        
        # 从图谱中选择一个代码元素
        target_node = graph.nodes[0]
        target_element = target_node.get_property("element")
        assume(target_element is not None)
        
        # 构造包含该元素名称的问题
        question = f"{target_element.name}在哪里？"
        
        try:
            relevant_code = await qa_service.locate_relevant_code(question, graph)
            
            # 验证能够找到目标元素
            found_target = False
            for code_elem in relevant_code:
                if code_elem.name == target_element.name:
                    found_target = True
                    break
            
            assert found_target, f"应该能够定位到代码元素 '{target_element.name}'"
            
        except Exception as e:
            pytest.fail(f"代码定位失败: {e}")
    
    @given(code_graph_strategy(), st.lists(st.text(min_size=1, max_size=10), min_size=1, max_size=5))
    @settings(max_examples=30, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    async def test_keyword_extraction_consistency_property(self, qa_service, graph, keywords):
        """
        **Feature: code-weaver, Property 7: 问答系统准确性**
        **验证需求: 需求 5.1**
        
        属性：关键词提取应该是一致的 - 相同的问题应该提取出相同的关键词。
        """
        # 过滤掉无效的关键词
        valid_keywords = [kw for kw in keywords if kw.strip() and kw.isalnum()]
        assume(len(valid_keywords) > 0)
        
        # 构造包含这些关键词的问题
        question = f"请告诉我关于 {' '.join(valid_keywords)} 的信息"
        
        try:
            # 多次提取关键词，结果应该一致
            extracted_1 = qa_service._extract_keywords(question)
            extracted_2 = qa_service._extract_keywords(question)
            
            assert extracted_1 == extracted_2, "相同问题的关键词提取结果应该一致"
            
            # 提取的关键词应该包含原始关键词的子集
            extracted_lower = [kw.lower() for kw in extracted_1]
            for original_kw in valid_keywords:
                if len(original_kw) > 1:  # 忽略单字符关键词
                    assert any(original_kw.lower() in ext_kw for ext_kw in extracted_lower), \
                        f"关键词 '{original_kw}' 应该被提取出来"
            
        except Exception as e:
            pytest.fail(f"关键词提取失败: {e}")
    
    @given(code_graph_strategy())
    @settings(max_examples=25, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    async def test_question_type_classification_property(self, qa_service, graph):
        """
        **Feature: code-weaver, Property 7: 问答系统准确性**
        **验证需求: 需求 5.1**
        
        属性：问题类型分类应该准确 - 特定模式的问题应该被正确分类。
        """
        test_cases = [
            ("如何调用UserService的方法？", "function_call"),
            ("UserClass继承了哪些类？", "inheritance"),
            ("模块A依赖哪些模块？", "dependency"),
            ("UserService的实现在哪里？", "implementation"),
            ("系统的架构是什么样的？", "structure"),
            ("UserClass在哪个文件？", "location"),
            ("How to call the function?", "function_call"),
            ("What class inherits from Base?", "inheritance")
        ]
        
        for question, expected_type in test_cases:
            try:
                classified_type = qa_service._analyze_question_type(question)
                assert classified_type == expected_type, \
                    f"问题 '{question}' 应该被分类为 '{expected_type}'，但得到 '{classified_type}'"
            except Exception as e:
                pytest.fail(f"问题类型分类失败: {e}")
    
    @given(code_graph_strategy())
    @settings(max_examples=20, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    async def test_confidence_calculation_property(self, qa_service, graph):
        """
        **Feature: code-weaver, Property 7: 问答系统准确性**
        **验证需求: 需求 5.4**
        
        属性：置信度计算应该合理 - 更好的匹配应该产生更高的置信度。
        """
        assume(len(graph.nodes) > 0)
        
        target_element = graph.nodes[0].get_property("element")
        assume(target_element is not None)
        
        try:
            # 完全匹配的情况
            exact_keywords = [target_element.name]
            exact_confidence = qa_service._calculate_confidence([target_element], exact_keywords)
            
            # 部分匹配的情况
            partial_keywords = [target_element.name[:3]] if len(target_element.name) > 3 else ["partial"]
            partial_confidence = qa_service._calculate_confidence([target_element], partial_keywords)
            
            # 无匹配的情况
            no_match_keywords = ["不存在的关键词"]
            no_match_confidence = qa_service._calculate_confidence([target_element], no_match_keywords)
            
            # 验证置信度的合理性
            assert 0.0 <= exact_confidence <= 1.0
            assert 0.0 <= partial_confidence <= 1.0
            assert 0.0 <= no_match_confidence <= 1.0
            
            # 完全匹配应该比部分匹配有更高的置信度
            if len(target_element.name) > 3:
                assert exact_confidence >= partial_confidence, \
                    f"完全匹配的置信度 ({exact_confidence}) 应该不低于部分匹配 ({partial_confidence})"
            
            # 无匹配应该是最低置信度
            assert no_match_confidence == 0.0, "无匹配情况的置信度应该为0"
            
        except Exception as e:
            pytest.fail(f"置信度计算失败: {e}")
    
    @given(code_graph_strategy())
    @settings(max_examples=15, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    async def test_answer_generation_completeness_property(self, qa_service, graph):
        """
        **Feature: code-weaver, Property 7: 问答系统准确性**
        **验证需求: 需求 5.2, 5.3, 5.4**
        
        属性：当找到相关代码时，生成的答案应该包含有用信息；
        当没有找到相关代码时，应该给出合适的提示。
        """
        assume(len(graph.nodes) > 0)
        
        target_element = graph.nodes[0].get_property("element")
        assume(target_element is not None)
        
        try:
            # 有相关代码的情况
            question_with_code = f"{target_element.name}的作用是什么？"
            answer_with_code = await qa_service.generate_answer(question_with_code, [target_element])
            
            assert isinstance(answer_with_code, str)
            assert len(answer_with_code) > 0
            # 答案不应该是"抱歉"开头的错误信息
            assert not answer_with_code.startswith("抱歉")
            
            # 无相关代码的情况
            question_no_code = "不存在的代码元素"
            answer_no_code = await qa_service.generate_answer(question_no_code, [])
            
            assert isinstance(answer_no_code, str)
            assert len(answer_no_code) > 0
            # 应该包含适当的提示信息
            assert "抱歉" in answer_no_code or "没有找到" in answer_no_code
            
        except Exception as e:
            pytest.fail(f"答案生成失败: {e}")


# 运行异步测试的辅助函数
def run_async_test(coro):
    """运行异步测试的辅助函数"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# 将异步测试方法包装为同步方法
class TestQASystemPropertiesSync(TestQASystemProperties):
    """问答系统属性测试类（同步版本）"""
    
    @given(TestQASystemProperties.code_graph_strategy(), TestQASystemProperties.question_strategy())
    @settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_qa_system_accuracy_property_sync(self, qa_service, graph, question):
        """同步版本的问答系统准确性属性测试"""
        async def async_test():
            return await super(TestQASystemPropertiesSync, self).test_qa_system_accuracy_property(qa_service, graph, question)
        run_async_test(async_test())
    
    @given(TestQASystemProperties.code_graph_strategy())
    @settings(max_examples=30, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_code_location_completeness_property_sync(self, qa_service, graph):
        """同步版本的代码定位完整性属性测试"""
        async def async_test():
            return await super(TestQASystemPropertiesSync, self).test_code_location_completeness_property(qa_service, graph)
        run_async_test(async_test())
    
    @given(TestQASystemProperties.code_graph_strategy(), st.lists(st.text(min_size=1, max_size=10), min_size=1, max_size=5))
    @settings(max_examples=30, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_keyword_extraction_consistency_property_sync(self, qa_service, graph, keywords):
        """同步版本的关键词提取一致性属性测试"""
        async def async_test():
            return await super(TestQASystemPropertiesSync, self).test_keyword_extraction_consistency_property(qa_service, graph, keywords)
        run_async_test(async_test())
    
    @given(TestQASystemProperties.code_graph_strategy())
    @settings(max_examples=25, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_question_type_classification_property_sync(self, qa_service, graph):
        """同步版本的问题类型分类属性测试"""
        async def async_test():
            return await super(TestQASystemPropertiesSync, self).test_question_type_classification_property(qa_service, graph)
        run_async_test(async_test())
    
    @given(TestQASystemProperties.code_graph_strategy())
    @settings(max_examples=20, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_confidence_calculation_property_sync(self, qa_service, graph):
        """同步版本的置信度计算属性测试"""
        async def async_test():
            return await super(TestQASystemPropertiesSync, self).test_confidence_calculation_property(qa_service, graph)
        run_async_test(async_test())
    
    @given(TestQASystemProperties.code_graph_strategy())
    @settings(max_examples=15, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_answer_generation_completeness_property_sync(self, qa_service, graph):
        """同步版本的答案生成完整性属性测试"""
        async def async_test():
            return await super(TestQASystemPropertiesSync, self).test_answer_generation_completeness_property(qa_service, graph)
        run_async_test(async_test())
  