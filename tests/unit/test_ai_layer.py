"""
AI层单元测试

测试AI层的基本功能和错误处理。
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.codenexus.ai import AILayer, create_ai_layer
from src.codenexus.config import Config, AIConfig
from src.codenexus.exceptions import AILayerError, ConfigurationError
from src.codenexus.models.core import CodeElement, CodeGraph, GraphNode


class TestAILayer:
    """AI层测试类"""
    
    @pytest.fixture
    def config(self):
        """测试配置"""
        config = Config()
        config.ai = AIConfig(
            model_name="test-model",
            api_key="test-key",
            api_base="https://api.test.com/v1",
            max_tokens=1000,
            temperature=0.1,
            timeout=30
        )
        return config
    
    @pytest.fixture
    def ai_layer(self, config):
        """AI层实例"""
        return AILayer(config)
    
    @pytest.fixture
    def sample_code_element(self):
        """示例代码元素"""
        return CodeElement(
            id="test_func_1",
            name="test_function",
            type="function",
            file_path="/test/file.py",
            line_number=10,
            complexity=5,
            metadata={"parameters": ["arg1", "arg2"], "returns": "str"}
        )
    
    def test_ai_layer_creation(self, config):
        """测试AI层创建"""
        ai_layer = AILayer(config)
        assert ai_layer.config == config
        assert not ai_layer._initialized
    
    def test_create_ai_layer_factory(self, config):
        """测试AI层工厂函数"""
        ai_layer = create_ai_layer(config)
        assert isinstance(ai_layer, AILayer)
        assert ai_layer.config == config
    
    @pytest.mark.asyncio
    async def test_initialization_success(self, ai_layer):
        """测试成功初始化"""
        with patch('src.codenexus.ai.ai_layer.AsyncOpenAI') as mock_openai:
            mock_client = AsyncMock()
            mock_openai.return_value = mock_client
            
            await ai_layer.initialize()
            
            assert ai_layer._initialized
            # 检查客户端是否被设置为mock对象
            assert ai_layer._client == mock_client
            mock_openai.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_initialization_missing_api_key(self):
        """测试缺少API密钥的初始化"""
        config = Config()
        config.ai.api_key = None
        ai_layer = AILayer(config)
        
        with pytest.raises(AILayerError, match="AI层初始化失败"):
            await ai_layer.initialize()
    
    @pytest.mark.asyncio
    async def test_cleanup(self, ai_layer):
        """测试资源清理"""
        # 模拟已初始化状态
        ai_layer._initialized = True
        ai_layer._http_client = AsyncMock()
        
        await ai_layer.cleanup()
        
        assert not ai_layer._initialized
        ai_layer._http_client.aclose.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_call_model_success(self, ai_layer):
        """测试成功调用模型"""
        # 模拟初始化
        ai_layer._initialized = True
        mock_client = AsyncMock()
        ai_layer._client = mock_client
        
        # 模拟响应
        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = "测试响应内容"
        mock_response.choices = [mock_choice]
        mock_client.chat.completions.create.return_value = mock_response
        
        messages = [{"role": "user", "content": "测试消息"}]
        result = await ai_layer._call_model(messages)
        
        assert result == "测试响应内容"
        mock_client.chat.completions.create.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_call_model_empty_response(self, ai_layer):
        """测试模型返回空响应"""
        ai_layer._initialized = True
        mock_client = AsyncMock()
        ai_layer._client = mock_client
        
        # 模拟空响应
        mock_response = MagicMock()
        mock_response.choices = []
        mock_client.chat.completions.create.return_value = mock_response
        
        messages = [{"role": "user", "content": "测试消息"}]
        
        with pytest.raises(AILayerError, match="模型返回空响应"):
            await ai_layer._call_model(messages)
    
    @pytest.mark.asyncio
    async def test_generate_documentation(self, ai_layer, sample_code_element):
        """测试文档生成"""
        ai_layer._initialized = True
        
        with patch.object(ai_layer, '_call_model') as mock_call:
            mock_call.return_value = "# 测试函数文档\n\n这是一个测试函数。"
            
            context = {
                "code_element": sample_code_element,
                "related_elements": [],
                "graph_context": {}
            }
            
            result = await ai_layer.generate_documentation(context)
            
            assert "测试函数文档" in result
            mock_call.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_generate_documentation_missing_element(self, ai_layer):
        """测试缺少代码元素的文档生成"""
        context = {}
        
        with pytest.raises(AILayerError, match="缺少代码元素信息"):
            await ai_layer.generate_documentation(context)
    
    @pytest.mark.asyncio
    async def test_answer_question(self, ai_layer):
        """测试问答功能"""
        ai_layer._initialized = True
        
        with patch.object(ai_layer, '_call_model') as mock_call:
            mock_call.return_value = "这个函数用于处理用户输入。"
            
            context = {"relevant_elements": []}
            result = await ai_layer.answer_question("这个函数是做什么的？", context)
            
            assert "处理用户输入" in result
            mock_call.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_analyze_code_quality_json_response(self, ai_layer, sample_code_element):
        """测试代码质量分析（JSON响应）"""
        ai_layer._initialized = True
        
        quality_result = {
            "score": 85.0,
            "issues": ["复杂度较高"],
            "suggestions": ["考虑拆分函数"],
            "analysis": "整体质量良好"
        }
        
        with patch.object(ai_layer, '_call_model') as mock_call:
            mock_call.return_value = json.dumps(quality_result, ensure_ascii=False)
            
            result = await ai_layer.analyze_code_quality(sample_code_element)
            
            assert result["score"] == 85.0
            assert "复杂度较高" in result["issues"]
            mock_call.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_analyze_code_quality_text_response(self, ai_layer, sample_code_element):
        """测试代码质量分析（文本响应）"""
        ai_layer._initialized = True
        
        with patch.object(ai_layer, '_call_model') as mock_call:
            mock_call.return_value = "代码质量分析：函数复杂度适中，建议添加注释。"
            
            result = await ai_layer.analyze_code_quality(sample_code_element)
            
            assert "analysis" in result
            assert "函数复杂度适中" in result["analysis"]
            assert result["score"] == 0.0  # 默认值
            mock_call.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_suggest_improvements(self, ai_layer):
        """测试改进建议"""
        ai_layer._initialized = True
        
        issues = [
            {"type": "complexity", "description": "函数复杂度过高"},
            {"type": "naming", "description": "变量命名不清晰"}
        ]
        
        with patch.object(ai_layer, '_call_model') as mock_call:
            mock_call.return_value = "1. 拆分复杂函数\n2. 使用更清晰的变量名\n3. 添加类型注解"
            
            result = await ai_layer.suggest_improvements(issues)
            
            assert len(result) == 3
            assert "拆分复杂函数" in result[0]
            assert "更清晰的变量名" in result[1]
            mock_call.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_suggest_improvements_empty_issues(self, ai_layer):
        """测试空问题列表的改进建议"""
        result = await ai_layer.suggest_improvements([])
        assert result == []
    
    @pytest.mark.asyncio
    async def test_detect_risks_json_response(self, ai_layer):
        """测试风险检测（JSON响应）"""
        ai_layer._initialized = True
        
        # 创建简单的图谱
        nodes = [GraphNode(id="node1", label="test", type="function")]
        graph = CodeGraph(nodes=nodes, edges=[], metadata=None)
        
        risks = [
            {
                "type": "security",
                "severity": "high",
                "description": "潜在的SQL注入风险",
                "location": "database.py:45"
            }
        ]
        
        with patch.object(ai_layer, '_call_model') as mock_call:
            mock_call.return_value = json.dumps(risks, ensure_ascii=False)
            
            result = await ai_layer.detect_risks(graph)
            
            assert len(result) == 1
            assert result[0]["type"] == "security"
            assert result[0]["severity"] == "high"
            mock_call.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_detect_risks_text_response(self, ai_layer):
        """测试风险检测（文本响应）"""
        ai_layer._initialized = True
        
        nodes = [GraphNode(id="node1", label="test", type="function")]
        graph = CodeGraph(nodes=nodes, edges=[], metadata=None)
        
        with patch.object(ai_layer, '_call_model') as mock_call:
            mock_call.return_value = "发现潜在的安全风险：未验证的用户输入"
            
            result = await ai_layer.detect_risks(graph)
            
            assert len(result) == 1
            assert result[0]["type"] == "analysis"
            assert "安全风险" in result[0]["description"]
            mock_call.assert_called_once()
    
    def test_build_documentation_prompt(self, ai_layer, sample_code_element):
        """测试文档生成提示词构建"""
        related_elements = [
            CodeElement(
                id="related_1",
                name="helper_function",
                type="function",
                file_path="/test/helper.py",
                line_number=5,
                complexity=2,
                metadata={}
            )
        ]
        
        graph_context = {"dependencies": ["module1", "module2"]}
        
        prompt = ai_layer._build_documentation_prompt(
            sample_code_element, related_elements, graph_context
        )
        
        assert "test_function" in prompt
        assert "function" in prompt
        assert "/test/file.py" in prompt
        assert "helper_function" in prompt
        assert "dependencies" in prompt
    
    def test_build_qa_context(self, ai_layer, sample_code_element):
        """测试问答上下文构建"""
        context = {
            "relevant_elements": [sample_code_element],
            "call_chain": ["main", "process", "test_function"],
            "graph_info": {"node_count": 10, "edge_count": 15}
        }
        
        result = ai_layer._build_qa_context(context)
        
        assert "test_function" in result
        assert "main -> process -> test_function" in result
        assert "node_count" in result
    
    def test_build_qa_context_empty(self, ai_layer):
        """测试空上下文构建"""
        result = ai_layer._build_qa_context({})
        assert result == "无特定上下文信息"
    
    def test_build_quality_analysis_prompt(self, ai_layer, sample_code_element):
        """测试质量分析提示词构建"""
        prompt = ai_layer._build_quality_analysis_prompt(sample_code_element)
        
        assert "test_function" in prompt
        assert "复杂度" in prompt
        assert "可读性" in prompt
        assert "JSON格式" in prompt
    
    def test_build_graph_summary(self, ai_layer):
        """测试图谱摘要构建"""
        nodes = [
            GraphNode(id="node1", label="func1", type="function"),
            GraphNode(id="node2", label="class1", type="class")
        ]
        edges = [
            MagicMock(type="calls"),
            MagicMock(type="inherits")
        ]
        
        graph = CodeGraph(nodes=nodes, edges=edges, metadata=None)
        
        summary = ai_layer._build_graph_summary(graph)
        
        assert "节点数量: 2" in summary
        assert "边数量: 2" in summary
        assert "function: 1" in summary
        assert "class: 1" in summary
        assert "calls: 1" in summary
        assert "inherits: 1" in summary