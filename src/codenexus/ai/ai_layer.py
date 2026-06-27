"""
AI智能层实现

集成大语言模型，提供智能分析和生成能力。
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional

from openai import OpenAI

from ..config import Config
from ..exceptions import AILayerError, ConfigurationError
from ..interfaces import AILayerInterface
from ..models.core import CodeElement, CodeGraph
from ..utils.error_handler import error_handler, with_circuit_breaker


logger = logging.getLogger(__name__)


class AILayer(AILayerInterface):
    """AI智能层实现类
    
    集成DeepSeek-Coder等大语言模型，提供智能代码分析、文档生成、
    问答和风险检测等功能。
    """
    
    def __init__(self, config: Config):
        """初始化AI层
        
        Args:
            config: 系统配置对象
        """
        self.config = config
        self._client: Optional[OpenAI] = None
        self._initialized = False
        
    def initialize(self) -> None:
        """初始化AI客户端"""
        if self._initialized:
            return
            
        try:
            # 验证配置
            if not self.config.ai.api_key:
                raise ConfigurationError("AI API密钥未配置")
                
            # 初始化OpenAI兼容客户端（支持火山引擎）
            self._client = OpenAI(
                api_key=self.config.ai.api_key,
                base_url=self.config.ai.api_base,
                timeout=self.config.ai.timeout
            )
            
            self._initialized = True
            logger.info(f"AI层初始化成功，使用模型: {self.config.ai.model_name}")
            
        except Exception as e:
            logger.error(f"AI层初始化失败: {e}")
            raise AILayerError(f"AI层初始化失败: {e}")
    
    def _ensure_initialized(self) -> None:
        """确保AI层已初始化"""
        if not self._initialized:
            self.initialize()
    
    def _call_model(
        self, 
        messages: List[Dict[str, str]], 
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None
    ) -> str:
        """调用大语言模型
        
        Args:
            messages: 对话消息列表
            max_tokens: 最大token数
            temperature: 温度参数
            
        Returns:
            模型响应文本
            
        Raises:
            AILayerError: 模型调用失败
        """
        self._ensure_initialized()
        
        try:
            # 使用OpenAI客户端调用API
            response = self._client.chat.completions.create(
                model=self.config.ai.model_name,
                messages=messages,
                max_tokens=max_tokens or self.config.ai.max_tokens,
                temperature=temperature or self.config.ai.temperature
            )
            
            if not response.choices:
                raise AILayerError("模型返回空响应")
                
            content = response.choices[0].message.content
            if not content:
                raise AILayerError("模型返回空内容")
                
            return content.strip()
            
        except Exception as e:
            logger.error(f"模型调用失败: {e}")
            raise AILayerError(f"模型调用失败: {e}")
    
    def generate_documentation(self, context: Dict[str, Any]) -> str:
        """生成代码文档
        
        Args:
            context: 代码上下文信息，包含：
                - code_element: CodeElement对象
                - related_elements: 相关代码元素列表
                - graph_context: 图谱上下文信息
                
        Returns:
            生成的Markdown格式文档
        """
        try:
            code_element = context.get("code_element")
            related_elements = context.get("related_elements", [])
            graph_context = context.get("graph_context", {})
            
            if not code_element:
                raise AILayerError("缺少代码元素信息")
            
            # 构建提示词
            prompt = self._build_documentation_prompt(
                code_element, related_elements, graph_context
            )
            
            messages = [
                {
                    "role": "system",
                    "content": "你是一个专业的代码文档生成助手。请根据提供的代码信息生成高质量的技术文档，使用Markdown格式。"
                },
                {
                    "role": "user", 
                    "content": prompt
                }
            ]
            
            return self._call_model(messages)
            
        except Exception as e:
            logger.error(f"文档生成失败: {e}")
            raise AILayerError(f"文档生成失败: {e}")
    
    def answer_question(self, question: str, context: Dict[str, Any]) -> str:
        """回答代码相关问题
        
        Args:
            question: 用户问题
            context: 代码上下文信息
            
        Returns:
            问题答案
        """
        try:
            # 构建上下文信息
            context_info = self._build_qa_context(context)
            
            messages = [
                {
                    "role": "system",
                    "content": "你是一个专业的代码分析助手。请根据提供的代码上下文信息回答用户的问题，提供准确、详细的解释。"
                },
                {
                    "role": "user",
                    "content": f"代码上下文：\n{context_info}\n\n问题：{question}"
                }
            ]
            
            return self._call_model(messages)
            
        except Exception as e:
            logger.error(f"问答处理失败: {e}")
            raise AILayerError(f"问答处理失败: {e}")
    
    async def analyze_code_quality(self, code: CodeElement) -> Dict[str, Any]:
        """分析代码质量
        
        Args:
            code: 代码元素
            
        Returns:
            代码质量分析结果
        """
        try:
            # 构建代码质量分析提示词
            prompt = self._build_quality_analysis_prompt(code)
            
            messages = [
                {
                    "role": "system",
                    "content": "你是一个专业的代码质量分析师。请分析提供的代码，评估其质量并提供改进建议。返回JSON格式的分析结果。"
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ]
            
            response = await self._call_model(messages)
            
            # 尝试解析JSON响应
            try:
                return json.loads(response)
            except json.JSONDecodeError:
                # 如果不是有效JSON，返回文本分析结果
                return {
                    "analysis": response,
                    "score": 0.0,
                    "issues": [],
                    "suggestions": []
                }
                
        except Exception as e:
            logger.error(f"代码质量分析失败: {e}")
            raise AILayerError(f"代码质量分析失败: {e}")
    
    async def suggest_improvements(self, issues: List[Dict[str, Any]]) -> List[str]:
        """建议代码改进
        
        Args:
            issues: 代码问题列表
            
        Returns:
            改进建议列表
        """
        try:
            if not issues:
                return []
            
            # 构建问题描述
            issues_text = "\n".join([
                f"- {issue.get('type', '未知')}: {issue.get('description', '无描述')}"
                for issue in issues
            ])
            
            messages = [
                {
                    "role": "system",
                    "content": "你是一个专业的代码改进顾问。请根据提供的代码问题列表，提供具体的改进建议。"
                },
                {
                    "role": "user",
                    "content": f"代码问题：\n{issues_text}\n\n请提供改进建议："
                }
            ]
            
            response = await self._call_model(messages)
            
            # 将响应分割为建议列表
            suggestions = [
                line.strip().lstrip("- ").lstrip("* ").lstrip("1. ").lstrip("2. ").lstrip("3. ")
                for line in response.split("\n")
                if line.strip() and not line.strip().startswith("#")
            ]
            
            return suggestions
            
        except Exception as e:
            logger.error(f"改进建议生成失败: {e}")
            raise AILayerError(f"改进建议生成失败: {e}")
    
    async def detect_risks(self, graph: CodeGraph) -> List[Dict[str, Any]]:
        """检测代码风险
        
        Args:
            graph: 代码知识图谱
            
        Returns:
            风险检测结果列表
        """
        try:
            # 构建图谱摘要信息
            graph_summary = self._build_graph_summary(graph)
            
            messages = [
                {
                    "role": "system",
                    "content": "你是一个专业的代码安全和架构分析师。请分析提供的代码图谱信息，识别潜在的安全风险和架构问题。返回JSON格式的风险列表。"
                },
                {
                    "role": "user",
                    "content": f"代码图谱信息：\n{graph_summary}\n\n请分析潜在风险："
                }
            ]
            
            response = await self._call_model(messages)
            
            # 尝试解析JSON响应
            try:
                risks = json.loads(response)
                if isinstance(risks, list):
                    return risks
                elif isinstance(risks, dict) and "risks" in risks:
                    return risks["risks"]
                else:
                    return []
            except json.JSONDecodeError:
                # 如果不是有效JSON，返回文本分析结果
                return [{
                    "type": "analysis",
                    "severity": "info",
                    "description": response,
                    "location": "general"
                }]
                
        except Exception as e:
            logger.error(f"风险检测失败: {e}")
            raise AILayerError(f"风险检测失败: {e}")
    
    def _build_documentation_prompt(
        self, 
        code_element: CodeElement, 
        related_elements: List[CodeElement],
        graph_context: Dict[str, Any]
    ) -> str:
        """构建文档生成提示词"""
        prompt_parts = [
            f"请为以下代码元素生成详细的技术文档：",
            f"",
            f"## 主要代码元素",
            f"- 名称: {code_element.name}",
            f"- 类型: {code_element.type}",
            f"- 文件: {code_element.file_path}",
            f"- 行号: {code_element.line_number}",
            f"- 复杂度: {code_element.complexity}",
        ]
        
        if code_element.metadata:
            prompt_parts.extend([
                f"- 元数据: {json.dumps(code_element.metadata, ensure_ascii=False, indent=2)}"
            ])
        
        if related_elements:
            prompt_parts.extend([
                f"",
                f"## 相关代码元素",
            ])
            for elem in related_elements[:5]:  # 限制数量
                prompt_parts.append(f"- {elem.name} ({elem.type})")
        
        if graph_context:
            prompt_parts.extend([
                f"",
                f"## 图谱上下文",
                f"{json.dumps(graph_context, ensure_ascii=False, indent=2)}"
            ])
        
        prompt_parts.extend([
            f"",
            f"请生成包含以下内容的Markdown文档：",
            f"1. 概述和功能描述",
            f"2. 参数说明（如适用）",
            f"3. 返回值说明（如适用）",
            f"4. 使用示例",
            f"5. 依赖关系",
            f"6. 注意事项"
        ])
        
        return "\n".join(prompt_parts)
    
    def _build_qa_context(self, context: Dict[str, Any]) -> str:
        """构建问答上下文信息"""
        context_parts = []
        
        if "relevant_elements" in context:
            context_parts.append("相关代码元素：")
            for elem in context["relevant_elements"]:
                if isinstance(elem, CodeElement):
                    context_parts.append(f"- {elem.name} ({elem.type}) in {elem.file_path}")
                else:
                    context_parts.append(f"- {elem}")
        
        if "call_chain" in context:
            context_parts.extend([
                "",
                "调用链路：",
                " -> ".join(context["call_chain"])
            ])
        
        if "graph_info" in context:
            context_parts.extend([
                "",
                "图谱信息：",
                json.dumps(context["graph_info"], ensure_ascii=False, indent=2)
            ])
        
        return "\n".join(context_parts) if context_parts else "无特定上下文信息"
    
    def _build_quality_analysis_prompt(self, code: CodeElement) -> str:
        """构建代码质量分析提示词"""
        return f"""
请分析以下代码元素的质量：

名称: {code.name}
类型: {code.type}
文件: {code.file_path}
行号: {code.line_number}
复杂度: {code.complexity}
元数据: {json.dumps(code.metadata, ensure_ascii=False, indent=2)}

请从以下维度进行分析：
1. 代码复杂度
2. 可读性
3. 可维护性
4. 性能考虑
5. 安全性
6. 最佳实践遵循

请返回JSON格式的分析结果，包含：
- score: 总体质量评分 (0-100)
- issues: 发现的问题列表
- suggestions: 改进建议列表
- analysis: 详细分析文本
"""
    
    def _build_graph_summary(self, graph: CodeGraph) -> str:
        """构建图谱摘要信息"""
        summary_parts = [
            f"图谱统计信息：",
            f"- 节点数量: {len(graph.nodes)}",
            f"- 边数量: {len(graph.edges)}",
        ]
        
        # 统计节点类型
        node_types = {}
        for node in graph.nodes:
            node_type = getattr(node, 'type', 'unknown')
            node_types[node_type] = node_types.get(node_type, 0) + 1
        
        if node_types:
            summary_parts.append("- 节点类型分布:")
            for node_type, count in node_types.items():
                summary_parts.append(f"  - {node_type}: {count}")
        
        # 统计边类型
        edge_types = {}
        for edge in graph.edges:
            edge_type = getattr(edge, 'type', 'unknown')
            edge_types[edge_type] = edge_types.get(edge_type, 0) + 1
        
        if edge_types:
            summary_parts.append("- 关系类型分布:")
            for edge_type, count in edge_types.items():
                summary_parts.append(f"  - {edge_type}: {count}")
        
        # 添加元数据信息
        if hasattr(graph, 'metadata') and graph.metadata:
            summary_parts.extend([
                "- 图谱元数据:",
                f"  {json.dumps(graph.metadata.__dict__ if hasattr(graph.metadata, '__dict__') else graph.metadata, ensure_ascii=False, indent=2)}"
            ])
        
        return "\n".join(summary_parts)