"""
问答服务实现

处理自然语言查询，定位相关代码并生成准确答案。
"""

import asyncio
import logging
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from ..ai.ai_layer import AILayer
from ..database.graph_database import GraphDatabase
from ..exceptions import QAServiceError
from ..interfaces import QAServiceInterface
from ..models.core import CodeElement, CodeGraph, GraphNode
from ..services.cache_service import CacheService, SmartCacheStrategy


logger = logging.getLogger(__name__)


class QAService(QAServiceInterface):
    """问答服务实现类
    
    处理自然语言问题，通过图谱查询定位相关代码，
    并使用AI层生成准确的答案。
    """
    
    def __init__(self, ai_layer: AILayer, graph_db: GraphDatabase, cache_service: Optional[CacheService] = None):
        """初始化问答服务
        
        Args:
            ai_layer: AI智能层实例
            graph_db: 图数据库实例
            cache_service: 缓存服务实例（可选）
        """
        self.ai_layer = ai_layer
        self.graph_db = graph_db
        self.cache_service = cache_service
        self.cache_strategy = SmartCacheStrategy(cache_service) if cache_service else None
        self._question_patterns = self._build_question_patterns()
        
    def _build_question_patterns(self) -> Dict[str, List[str]]:
        """构建问题模式匹配规则
        
        Returns:
            问题类型到关键词模式的映射
        """
        return {
            "function_call": [
                r"调用.*?函数",
                r"使用.*?方法",
                r".*?怎么调用",
                r".*?如何调用",
                r".*?如何使用",
                r".*?的用法",
                r"call.*?function",
                r"use.*?method",
                r"how to call",
                r"how to use"
            ],
            "inheritance": [
                r"继承.*?类",
                r".*?的父类",
                r".*?的子类",
                r".*?继承关系",
                r"inherit.*?class",
                r"parent.*?class",
                r"child.*?class",
                r".*?inherits.*?from",
                r"what.*?class.*?inherit",
                r"inheritance"
            ],
            "dependency": [
                r"依赖.*?模块",
                r".*?的依赖",
                r".*?依赖关系",
                r"import.*?module",
                r"depend.*?on",
                r"dependency"
            ],
            "implementation": [
                r".*?的实现",
                r"如何实现.*?",
                r"实现.*?功能",
                r".*?implementation",
                r"how.*?implement",
                r"implement.*?feature"
            ],
            "structure": [
                r".*?的结构",
                r".*?架构",
                r".*?组织",
                r".*?structure",
                r".*?architecture",
                r".*?organization"
            ],
            "location": [
                r".*?在哪里",
                r".*?在哪个文件",
                r".*?位置",
                r"找到.*?",
                r"where.*?is",
                r"location.*?of",
                r"find.*?",
                r".*?在.*?文件"
            ]
        }
    
    async def process_question(self, question: str, graph: CodeGraph) -> Dict[str, Any]:
        """处理问题并返回完整答案
        
        Args:
            question: 用户问题
            graph: 代码知识图谱
            
        Returns:
            包含答案、相关代码和调用链的字典
            
        Raises:
            QAServiceError: 问题处理失败
        """
        try:
            logger.info(f"处理问题: {question}")
            
            # 尝试从缓存获取结果
            if self.cache_service:
                cache_key = CacheService.generate_cache_key(
                    "qa_answer", question, graph_id=getattr(graph, 'id', 'default')
                )
                cached_result = self.cache_service.get(cache_key)
                if cached_result:
                    logger.debug("从缓存返回问答结果")
                    return cached_result
            
            # 1. 分析问题类型
            question_type = self._analyze_question_type(question)
            logger.debug(f"问题类型: {question_type}")
            
            # 2. 提取关键词
            keywords = self._extract_keywords(question)
            logger.debug(f"提取的关键词: {keywords}")
            
            # 3. 定位相关代码
            relevant_code = await self.locate_relevant_code(question, graph)
            logger.debug(f"找到 {len(relevant_code)} 个相关代码元素")
            
            # 4. 构建调用链路
            call_chains = await self._build_call_chains(relevant_code, graph)
            
            # 5. 生成答案
            answer = await self.generate_answer(question, relevant_code)
            
            result = {
                "question": question,
                "question_type": question_type,
                "keywords": keywords,
                "relevant_code": [self._serialize_code_element(elem) for elem in relevant_code],
                "call_chains": call_chains,
                "answer": answer,
                "confidence": self._calculate_confidence(relevant_code, keywords)
            }
            
            # 缓存结果
            if self.cache_service and self.cache_strategy:
                if self.cache_strategy.should_cache("qa_answer", result):
                    ttl = self.cache_strategy.get_ttl("qa_answer", len(relevant_code))
                    self.cache_service.set(cache_key, result, ttl)
            
            return result
            
        except Exception as e:
            logger.error(f"问题处理失败: {e}")
            raise QAServiceError(f"问题处理失败: {e}")
    
    async def locate_relevant_code(self, question: str, graph: CodeGraph) -> List[CodeElement]:
        """定位与问题相关的代码元素
        
        Args:
            question: 用户问题
            graph: 代码知识图谱
            
        Returns:
            相关代码元素列表
        """
        try:
            # 提取关键词
            keywords = self._extract_keywords(question)
            question_type = self._analyze_question_type(question)
            
            relevant_elements = []
            
            # 1. 基于名称匹配查找
            name_matches = await self._find_by_name_matching(keywords, graph)
            relevant_elements.extend(name_matches)
            
            # 2. 基于问题类型的特定查询
            type_matches = await self._find_by_question_type(question_type, keywords, graph)
            relevant_elements.extend(type_matches)
            
            # 3. 基于语义相似度查找（如果有足够的元数据）
            semantic_matches = await self._find_by_semantic_similarity(question, graph)
            relevant_elements.extend(semantic_matches)
            
            # 去重并按相关性排序
            unique_elements = self._deduplicate_and_rank(relevant_elements, keywords)
            
            # 限制返回数量，避免信息过载
            return unique_elements[:20]
            
        except Exception as e:
            logger.error(f"代码定位失败: {e}")
            raise QAServiceError(f"代码定位失败: {e}")
    
    async def generate_answer(self, question: str, relevant_code: List[CodeElement]) -> str:
        """生成问题答案
        
        Args:
            question: 用户问题
            relevant_code: 相关代码元素列表
            
        Returns:
            生成的答案
        """
        try:
            if not relevant_code:
                return "抱歉，我没有找到与您问题相关的代码信息。请尝试使用更具体的关键词或检查代码库是否已正确解析。"
            
            # 构建上下文信息
            context = {
                "relevant_elements": relevant_code,
                "question_type": self._analyze_question_type(question),
                "graph_info": await self._build_graph_context(relevant_code)
            }
            
            # 使用AI层生成答案
            answer = self.ai_layer.answer_question(question, context)
            
            return answer
            
        except Exception as e:
            logger.error(f"答案生成失败: {e}")
            raise QAServiceError(f"答案生成失败: {e}")
    
    def _analyze_question_type(self, question: str) -> str:
        """分析问题类型
        
        Args:
            question: 用户问题
            
        Returns:
            问题类型
        """
        question_lower = question.lower()
        
        for question_type, patterns in self._question_patterns.items():
            for pattern in patterns:
                if re.search(pattern, question_lower):
                    return question_type
        
        return "general"
    
    def _extract_keywords(self, question: str) -> List[str]:
        """从问题中提取关键词
        
        Args:
            question: 用户问题
            
        Returns:
            关键词列表
        """
        # 移除常见的停用词
        stop_words = {
            "的", "是", "在", "有", "和", "或", "但", "如何", "什么", "哪里", "为什么", "怎么",
            "这个", "那个", "一个", "这些", "那些", "可以", "能够", "应该", "需要", "想要",
            "the", "is", "in", "and", "or", "but", "how", "what", "where", "why", "to",
            "this", "that", "these", "those", "can", "could", "should", "need", "want"
        }
        
        # 使用更宽松的模式提取标识符（允许被非字母数字字符分隔）
        identifier_pattern = r'[a-zA-Z_][a-zA-Z0-9_]*'
        identifiers = re.findall(identifier_pattern, question)
        
        # 提取中文词汇，尝试分割常见词汇
        chinese_pattern = r'[\u4e00-\u9fff]+'
        chinese_words = re.findall(chinese_pattern, question)
        
        # 合并所有关键词
        all_keywords = identifiers + chinese_words
        
        # 过滤停用词和短词
        keywords = []
        for kw in all_keywords:
            if kw.lower() not in stop_words and len(kw) > 1:
                keywords.append(kw)
        
        # 尝试分割长中文词组
        additional_keywords = []
        for kw in keywords:
            if re.match(r'^[\u4e00-\u9fff]+$', kw):  # 纯中文
                # 简单的中文分割逻辑
                if len(kw) > 4:
                    # 尝试按常见词汇分割
                    common_words = ['项目', '功能', '主要', '系统', '代码', '类', '函数', '方法']
                    for word in common_words:
                        if word in kw and word not in keywords:
                            additional_keywords.append(word)
        
        keywords.extend(additional_keywords)
        
        return list(set(keywords))  # 去重
    
    async def _find_by_name_matching(self, keywords: List[str], graph: CodeGraph) -> List[CodeElement]:
        """基于名称匹配查找代码元素
        
        Args:
            keywords: 关键词列表
            graph: 代码知识图谱
            
        Returns:
            匹配的代码元素列表
        """
        matches = []
        
        for node in graph.nodes:
            element = node.get_property("element")
            if element and isinstance(element, CodeElement):
                element_name_lower = element.name.lower()
                
                # 检查完全匹配
                for keyword in keywords:
                    keyword_lower = keyword.lower()
                    if keyword_lower == element_name_lower:
                        matches.append((element, 1.0))  # 完全匹配，权重1.0
                    elif keyword_lower in element_name_lower:
                        matches.append((element, 0.8))  # 部分匹配，权重0.8
                    elif element_name_lower in keyword_lower:
                        matches.append((element, 0.6))  # 反向部分匹配，权重0.6
        
        # 按权重排序并返回元素
        matches.sort(key=lambda x: x[1], reverse=True)
        return [match[0] for match in matches]
    
    async def _find_by_question_type(self, question_type: str, keywords: List[str], graph: CodeGraph) -> List[CodeElement]:
        """基于问题类型查找相关代码
        
        Args:
            question_type: 问题类型
            keywords: 关键词列表
            graph: 代码知识图谱
            
        Returns:
            相关代码元素列表
        """
        matches = []
        
        if question_type == "function_call":
            # 查找函数和方法
            matches.extend(self._find_elements_by_type(graph, ["method", "function"]))
        elif question_type == "inheritance":
            # 查找类和接口
            matches.extend(self._find_elements_by_type(graph, ["class", "interface"]))
        elif question_type == "dependency":
            # 查找模块和导入
            matches.extend(self._find_elements_by_type(graph, ["module", "import"]))
        elif question_type == "implementation":
            # 查找类和方法的实现
            matches.extend(self._find_elements_by_type(graph, ["class", "method", "function"]))
        elif question_type == "structure":
            # 查找所有结构性元素
            matches.extend(self._find_elements_by_type(graph, ["class", "module", "namespace"]))
        elif question_type == "general":
            # 对于一般性问题，返回所有类和主要函数
            matches.extend(self._find_elements_by_type(graph, ["class"]))
            # 限制返回数量，避免信息过载
            matches = matches[:10]
        
        return matches
    
    def _find_elements_by_type(self, graph: CodeGraph, element_types: List[str]) -> List[CodeElement]:
        """根据元素类型查找代码元素
        
        Args:
            graph: 代码知识图谱
            element_types: 元素类型列表
            
        Returns:
            匹配的代码元素列表
        """
        matches = []
        
        for node in graph.nodes:
            element = node.get_property("element")
            if element and isinstance(element, CodeElement):
                if element.type.lower() in [t.lower() for t in element_types]:
                    matches.append(element)
        
        return matches
    
    async def _find_by_semantic_similarity(self, question: str, graph: CodeGraph) -> List[CodeElement]:
        """基于语义相似度查找代码元素
        
        Args:
            question: 用户问题
            graph: 代码知识图谱
            
        Returns:
            语义相似的代码元素列表
        """
        # 这里可以实现更复杂的语义匹配逻辑
        # 目前返回空列表，后续可以集成向量搜索等技术
        return []
    
    def _deduplicate_and_rank(self, elements: List[CodeElement], keywords: List[str]) -> List[CodeElement]:
        """去重并按相关性排序代码元素
        
        Args:
            elements: 代码元素列表
            keywords: 关键词列表
            
        Returns:
            去重并排序后的代码元素列表
        """
        # 去重
        unique_elements = []
        seen_ids = set()
        
        for element in elements:
            element_id = f"{element.file_path}:{element.line_number}:{element.name}"
            if element_id not in seen_ids:
                unique_elements.append(element)
                seen_ids.add(element_id)
        
        # 按相关性排序
        def calculate_relevance(element: CodeElement) -> float:
            score = 0.0
            element_name_lower = element.name.lower()
            
            for keyword in keywords:
                keyword_lower = keyword.lower()
                if keyword_lower == element_name_lower:
                    score += 2.0
                elif keyword_lower in element_name_lower:
                    score += 1.0
                elif element_name_lower in keyword_lower:
                    score += 0.5
            
            # 根据元素类型调整权重
            type_weights = {
                "class": 1.2,
                "method": 1.1,
                "function": 1.1,
                "interface": 1.0,
                "variable": 0.8,
                "field": 0.8
            }
            score *= type_weights.get(element.type.lower(), 1.0)
            
            return score
        
        unique_elements.sort(key=calculate_relevance, reverse=True)
        return unique_elements
    
    async def _build_call_chains(self, relevant_code: List[CodeElement], graph: CodeGraph) -> List[List[str]]:
        """构建调用链路
        
        Args:
            relevant_code: 相关代码元素列表
            graph: 代码知识图谱
            
        Returns:
            调用链路列表
        """
        call_chains = []
        
        try:
            # 为每个相关代码元素查找调用链
            for element in relevant_code[:5]:  # 限制数量避免过多查询
                # 查找调用该元素的路径
                callers = await self._find_callers(element, graph)
                if callers:
                    chain = [caller.name for caller in callers] + [element.name]
                    call_chains.append(chain)
                
                # 查找该元素调用的路径
                callees = await self._find_callees(element, graph)
                if callees:
                    chain = [element.name] + [callee.name for callee in callees]
                    call_chains.append(chain)
        
        except Exception as e:
            logger.warning(f"构建调用链失败: {e}")
        
        return call_chains
    
    async def _find_callers(self, element: CodeElement, graph: CodeGraph) -> List[CodeElement]:
        """查找调用指定元素的代码
        
        Args:
            element: 目标代码元素
            graph: 代码知识图谱
            
        Returns:
            调用者列表
        """
        callers = []
        
        # 找到目标元素对应的节点
        target_node = None
        for node in graph.nodes:
            node_element = node.get_property("element")
            if node_element == element:
                target_node = node
                break
        
        if not target_node:
            return callers
        
        # 在图中查找指向该节点的边
        for edge in graph.edges:
            if (edge.target_id == target_node.id and 
                edge.type.lower() in ['calls', 'uses', 'depends']):
                
                # 找到源节点
                for node in graph.nodes:
                    if node.id == edge.source_id:
                        source_element = node.get_property("element")
                        if source_element and isinstance(source_element, CodeElement):
                            callers.append(source_element)
                        break
        
        return callers[:10]  # 限制数量
    
    async def _find_callees(self, element: CodeElement, graph: CodeGraph) -> List[CodeElement]:
        """查找指定元素调用的代码
        
        Args:
            element: 源代码元素
            graph: 代码知识图谱
            
        Returns:
            被调用者列表
        """
        callees = []
        
        # 找到源元素对应的节点
        source_node = None
        for node in graph.nodes:
            node_element = node.get_property("element")
            if node_element == element:
                source_node = node
                break
        
        if not source_node:
            return callees
        
        # 在图中查找从该节点出发的边
        for edge in graph.edges:
            if (edge.source_id == source_node.id and 
                edge.type.lower() in ['calls', 'uses', 'depends']):
                
                # 找到目标节点
                for node in graph.nodes:
                    if node.id == edge.target_id:
                        target_element = node.get_property("element")
                        if target_element and isinstance(target_element, CodeElement):
                            callees.append(target_element)
                        break
        
        return callees[:10]  # 限制数量
    
    async def _build_graph_context(self, relevant_code: List[CodeElement]) -> Dict[str, Any]:
        """构建图谱上下文信息
        
        Args:
            relevant_code: 相关代码元素列表
            
        Returns:
            图谱上下文信息
        """
        context = {
            "element_count": len(relevant_code),
            "element_types": {},
            "files": set(),
            "complexity_stats": {
                "min": float('inf'),
                "max": 0,
                "avg": 0
            }
        }
        
        total_complexity = 0
        
        for element in relevant_code:
            # 统计元素类型
            element_type = element.type
            context["element_types"][element_type] = context["element_types"].get(element_type, 0) + 1
            
            # 收集文件信息
            context["files"].add(element.file_path)
            
            # 统计复杂度
            complexity = element.complexity
            context["complexity_stats"]["min"] = min(context["complexity_stats"]["min"], complexity)
            context["complexity_stats"]["max"] = max(context["complexity_stats"]["max"], complexity)
            total_complexity += complexity
        
        if relevant_code:
            context["complexity_stats"]["avg"] = total_complexity / len(relevant_code)
            if context["complexity_stats"]["min"] == float('inf'):
                context["complexity_stats"]["min"] = 0
        else:
            # 空列表的情况，重置所有统计值
            context["complexity_stats"]["min"] = 0
            context["complexity_stats"]["max"] = 0
            context["complexity_stats"]["avg"] = 0
        
        context["files"] = list(context["files"])
        
        return context
    
    def _serialize_code_element(self, element: CodeElement) -> Dict[str, Any]:
        """序列化代码元素为字典
        
        Args:
            element: 代码元素
            
        Returns:
            序列化后的字典
        """
        return {
            "name": element.name,
            "type": element.type,
            "file_path": element.file_path,
            "line_number": element.line_number,
            "complexity": element.complexity,
            "metadata": element.metadata
        }
    
    def _calculate_confidence(self, relevant_code: List[CodeElement], keywords: List[str]) -> float:
        """计算答案置信度
        
        Args:
            relevant_code: 相关代码元素列表
            keywords: 关键词列表
            
        Returns:
            置信度分数 (0-1)
        """
        if not relevant_code or not keywords:
            return 0.0
        
        # 基于匹配度计算置信度
        total_matches = 0
        total_possible = len(keywords) * len(relevant_code)
        
        for element in relevant_code:
            element_name_lower = element.name.lower()
            for keyword in keywords:
                keyword_lower = keyword.lower()
                if keyword_lower in element_name_lower:
                    total_matches += 1
        
        if total_possible == 0:
            return 0.0
        
        base_confidence = total_matches / total_possible
        
        # 根据找到的代码数量调整置信度
        if len(relevant_code) >= 3:
            base_confidence *= 1.2
        elif len(relevant_code) == 0:
            base_confidence = 0.0
        
        return min(base_confidence, 1.0)