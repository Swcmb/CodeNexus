"""
风险检测服务

实现代码风险检测功能，包括安全漏洞检测、架构坏味检测和代码质量分析。
"""

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set
from ..interfaces import RiskDetectionServiceInterface, AILayerInterface
from ..models.core import CodeGraph, CodeElement, ElementType, RelationType, GraphNode


class RiskLevel(Enum):
    """风险等级枚举"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RiskCategory(Enum):
    """风险类别枚举"""
    SECURITY = "security"
    ARCHITECTURE = "architecture"
    QUALITY = "quality"
    PERFORMANCE = "performance"
    MAINTAINABILITY = "maintainability"


@dataclass
class RiskIssue:
    """风险问题数据模型"""
    id: str
    title: str
    description: str
    category: RiskCategory
    level: RiskLevel
    file_path: str
    line_number: int
    element_id: Optional[str] = None
    suggestion: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SecurityRule:
    """安全规则数据模型"""
    id: str
    name: str
    description: str
    pattern: str
    level: RiskLevel
    suggestion: str
    category: str = "security"


@dataclass
class ArchitectureRule:
    """架构规则数据模型"""
    id: str
    name: str
    description: str
    level: RiskLevel
    suggestion: str


class RiskDetectionService(RiskDetectionServiceInterface):
    """风险检测服务实现"""
    
    def __init__(self, ai_layer: Optional[AILayerInterface] = None):
        """初始化风险检测服务
        
        Args:
            ai_layer: AI智能层实例，用于增强风险分析
        """
        self.ai_layer = ai_layer
        self.security_rules = self._load_security_rules()
        self.architecture_rules = self._load_architecture_rules()
        self.quality_thresholds = self._load_quality_thresholds()
    
    def _load_security_rules(self) -> List[SecurityRule]:
        """加载安全检测规则"""
        return [
            SecurityRule(
                id="sql_injection",
                name="SQL注入风险",
                description="检测可能的SQL注入漏洞",
                pattern=r"(SELECT|INSERT|UPDATE|DELETE).*\+",
                level=RiskLevel.HIGH,
                suggestion="使用参数化查询或ORM框架避免SQL注入",
                category="injection"
            ),
            SecurityRule(
                id="xss_risk",
                name="XSS跨站脚本风险",
                description="检测可能的XSS漏洞",
                pattern=r"innerHTML\s*=\s*.*\+|document\.write\s*\(.*\+",
                level=RiskLevel.MEDIUM,
                suggestion="对用户输入进行HTML转义处理",
                category="xss"
            ),
            SecurityRule(
                id="hardcoded_password",
                name="硬编码密码",
                description="检测硬编码的密码或密钥",
                pattern=r"(password|pwd|secret|key)\s*=\s*['\"].{4,}['\"]",
                level=RiskLevel.CRITICAL,
                suggestion="将敏感信息存储在配置文件或环境变量中",
                category="credentials"
            ),
            SecurityRule(
                id="weak_crypto",
                name="弱加密算法",
                description="检测使用弱加密算法",
                pattern=r"(MD5|SHA1|DES)\s*\(",
                level=RiskLevel.MEDIUM,
                suggestion="使用更强的加密算法如SHA-256或AES",
                category="crypto"
            ),
            SecurityRule(
                id="path_traversal",
                name="路径遍历风险",
                description="检测可能的路径遍历漏洞",
                pattern=r"\.\.[\\/]|\.\.%2[fF]|\.\.%5[cC]",
                level=RiskLevel.HIGH,
                suggestion="验证和规范化文件路径，禁止使用相对路径",
                category="path_traversal"
            ),
            SecurityRule(
                id="command_injection",
                name="命令注入风险",
                description="检测可能的命令注入漏洞",
                pattern=r"(exec|system|eval|Runtime\.getRuntime)\s*\(.*\+",
                level=RiskLevel.CRITICAL,
                suggestion="避免动态构造系统命令，使用白名单验证输入",
                category="injection"
            )
        ]
    
    def _load_architecture_rules(self) -> List[ArchitectureRule]:
        """加载架构检测规则"""
        return [
            ArchitectureRule(
                id="circular_dependency",
                name="循环依赖",
                description="检测模块间的循环依赖",
                level=RiskLevel.HIGH,
                suggestion="重构代码结构，消除循环依赖"
            ),
            ArchitectureRule(
                id="deep_inheritance",
                name="过深继承层次",
                description="检测过深的继承层次结构",
                level=RiskLevel.MEDIUM,
                suggestion="考虑使用组合替代继承，减少继承层次"
            ),
            ArchitectureRule(
                id="god_class",
                name="上帝类",
                description="检测职责过多的大类",
                level=RiskLevel.MEDIUM,
                suggestion="将大类拆分为多个职责单一的小类"
            ),
            ArchitectureRule(
                id="feature_envy",
                name="特性嫉妒",
                description="检测过度依赖其他类的方法",
                level=RiskLevel.LOW,
                suggestion="考虑将方法移动到更合适的类中"
            ),
            ArchitectureRule(
                id="shotgun_surgery",
                name="散弹式修改",
                description="检测修改时需要同时修改多个类的情况",
                level=RiskLevel.MEDIUM,
                suggestion="重构代码，将相关功能集中到一个类中"
            )
        ]
    
    def _load_quality_thresholds(self) -> Dict[str, Any]:
        """加载代码质量阈值"""
        return {
            "max_method_complexity": 10,
            "max_class_methods": 20,
            "max_method_lines": 50,
            "max_class_lines": 500,
            "max_parameters": 5,
            "min_test_coverage": 0.8
        }
    
    async def scan_security_risks(self, graph: CodeGraph) -> List[Dict[str, Any]]:
        """扫描安全风险"""
        risks = []
        
        for node in graph.nodes:
            # 检查所有类型的节点，因为任何节点都可能包含代码内容
            # 检查节点属性中的代码内容
            code_content = node.get_property("docstring", "")
            if not code_content:
                # 如果没有docstring，尝试其他可能包含代码的属性
                code_content = str(node.get_property("code", ""))
            
            if code_content:
                element = self._node_to_element(node)
                if element:
                    # 检查代码内容中的安全风险
                    security_risks = self._check_security_patterns(code_content, element)
                    risks.extend(security_risks)
        
        return risks
    
    def _check_security_patterns(self, code_content: str, element: CodeElement) -> List[Dict[str, Any]]:
        """检查安全模式"""
        risks = []
        
        for rule in self.security_rules:
            # 使用DOTALL标志让.匹配换行符
            matches = re.finditer(rule.pattern, code_content, re.IGNORECASE | re.DOTALL)
            for match in matches:
                risk = {
                    "id": f"{rule.id}_{element.id}_{match.start()}",
                    "title": rule.name,
                    "description": rule.description,
                    "category": RiskCategory.SECURITY.value,
                    "level": rule.level.value,
                    "file_path": element.file_path,
                    "line_number": element.line_number + code_content[:match.start()].count('\n'),
                    "element_id": element.id,
                    "suggestion": rule.suggestion,
                    "matched_text": match.group(),
                    "metadata": {
                        "rule_id": rule.id,
                        "pattern": rule.pattern,
                        "match_position": match.start()
                    }
                }
                risks.append(risk)
        
        return risks
    
    async def detect_architecture_smells(self, graph: CodeGraph) -> List[Dict[str, Any]]:
        """检测架构坏味"""
        smells = []
        
        # 检测循环依赖
        circular_deps = self._detect_circular_dependencies(graph)
        smells.extend(circular_deps)
        
        # 检测过深继承
        deep_inheritance = self._detect_deep_inheritance(graph)
        smells.extend(deep_inheritance)
        
        # 检测上帝类
        god_classes = self._detect_god_classes(graph)
        smells.extend(god_classes)
        
        # 检测特性嫉妒
        feature_envy = self._detect_feature_envy(graph)
        smells.extend(feature_envy)
        
        return smells
    
    def _detect_circular_dependencies(self, graph: CodeGraph) -> List[Dict[str, Any]]:
        """检测循环依赖"""
        cycles = []
        visited = set()
        rec_stack = set()
        
        def dfs(node_id: str, path: List[str]) -> None:
            if node_id in rec_stack:
                # 找到循环
                cycle_start = path.index(node_id)
                cycle_path = path[cycle_start:] + [node_id]
                cycles.append(cycle_path)
                return
            
            if node_id in visited:
                return
            
            visited.add(node_id)
            rec_stack.add(node_id)
            
            # 获取依赖的节点
            for edge in graph.edges:
                if edge.source_id == node_id and edge.type in ["depends", "imports"]:
                    dfs(edge.target_id, path + [node_id])
            
            rec_stack.remove(node_id)
        
        # 对所有节点执行DFS
        for node in graph.nodes:
            if node.id not in visited:
                dfs(node.id, [])
        
        # 转换为风险报告格式
        risks = []
        for i, cycle in enumerate(cycles):
            if len(cycle) > 2:  # 至少3个节点才构成有意义的循环
                risk = {
                    "id": f"circular_dependency_{i}",
                    "title": "循环依赖",
                    "description": f"检测到循环依赖: {' -> '.join(cycle)}",
                    "category": RiskCategory.ARCHITECTURE.value,
                    "level": RiskLevel.HIGH.value,
                    "file_path": "",
                    "line_number": 0,
                    "suggestion": "重构代码结构，消除循环依赖",
                    "metadata": {
                        "cycle_path": cycle,
                        "cycle_length": len(cycle) - 1
                    }
                }
                risks.append(risk)
        
        return risks
    
    def _detect_deep_inheritance(self, graph: CodeGraph) -> List[Dict[str, Any]]:
        """检测过深继承"""
        risks = []
        max_depth = 5  # 最大继承深度阈值
        
        def calculate_inheritance_depth(node_id: str, visited: Set[str] = None) -> int:
            if visited is None:
                visited = set()
            
            if node_id in visited:
                return 0  # 避免循环继承
            
            visited.add(node_id)
            max_parent_depth = 0
            
            # 查找父类
            for edge in graph.edges:
                if edge.source_id == node_id and edge.type == "inherits":
                    parent_depth = calculate_inheritance_depth(edge.target_id, visited.copy())
                    max_parent_depth = max(max_parent_depth, parent_depth)
            
            return max_parent_depth + 1
        
        # 检查所有类节点
        for node in graph.nodes:
            if node.type == "class":
                depth = calculate_inheritance_depth(node.id)
                if depth > max_depth:
                    element = self._node_to_element(node)
                    risk = {
                        "id": f"deep_inheritance_{node.id}",
                        "title": "过深继承层次",
                        "description": f"类 {node.label} 的继承深度为 {depth}，超过推荐的 {max_depth} 层",
                        "category": RiskCategory.ARCHITECTURE.value,
                        "level": RiskLevel.MEDIUM.value,
                        "file_path": element.file_path if element else "",
                        "line_number": element.line_number if element else 0,
                        "element_id": node.id,
                        "suggestion": "考虑使用组合替代继承，减少继承层次",
                        "metadata": {
                            "inheritance_depth": depth,
                            "max_allowed_depth": max_depth
                        }
                    }
                    risks.append(risk)
        
        return risks
    
    def _detect_god_classes(self, graph: CodeGraph) -> List[Dict[str, Any]]:
        """检测上帝类"""
        risks = []
        max_methods = self.quality_thresholds["max_class_methods"]
        
        # 统计每个类的方法数量
        class_methods = {}
        for edge in graph.edges:
            if edge.type == "defines":
                source_node = graph.get_node_by_id(edge.source_id)
                target_node = graph.get_node_by_id(edge.target_id)
                
                if source_node and target_node and source_node.type == "class" and target_node.type == "method":
                    if edge.source_id not in class_methods:
                        class_methods[edge.source_id] = 0
                    class_methods[edge.source_id] += 1
        
        # 检查是否超过阈值
        for class_id, method_count in class_methods.items():
            if method_count > max_methods:
                class_node = graph.get_node_by_id(class_id)
                element = self._node_to_element(class_node)
                
                risk = {
                    "id": f"god_class_{class_id}",
                    "title": "上帝类",
                    "description": f"类 {class_node.label} 包含 {method_count} 个方法，超过推荐的 {max_methods} 个",
                    "category": RiskCategory.ARCHITECTURE.value,
                    "level": RiskLevel.MEDIUM.value,
                    "file_path": element.file_path if element else "",
                    "line_number": element.line_number if element else 0,
                    "element_id": class_id,
                    "suggestion": "将大类拆分为多个职责单一的小类",
                    "metadata": {
                        "method_count": method_count,
                        "max_allowed_methods": max_methods
                    }
                }
                risks.append(risk)
        
        return risks
    
    def _detect_feature_envy(self, graph: CodeGraph) -> List[Dict[str, Any]]:
        """检测特性嫉妒"""
        risks = []
        
        # 统计每个方法对外部类的调用次数
        method_external_calls = {}
        
        for edge in graph.edges:
            if edge.type == "calls":
                source_node = graph.get_node_by_id(edge.source_id)
                target_node = graph.get_node_by_id(edge.target_id)
                
                if source_node and target_node and source_node.type == "method" and target_node.type == "method":
                    # 获取方法所属的类
                    source_class = self._get_method_class(graph, edge.source_id)
                    target_class = self._get_method_class(graph, edge.target_id)
                    
                    if source_class and target_class and source_class != target_class:
                        if edge.source_id not in method_external_calls:
                            method_external_calls[edge.source_id] = {}
                        
                        if target_class not in method_external_calls[edge.source_id]:
                            method_external_calls[edge.source_id][target_class] = 0
                        
                        method_external_calls[edge.source_id][target_class] += 1
        
        # 检查是否存在特性嫉妒
        for method_id, external_calls in method_external_calls.items():
            total_external_calls = sum(external_calls.values())
            if total_external_calls > 5:  # 阈值：超过5次外部调用
                most_called_class = max(external_calls, key=external_calls.get)
                most_calls = external_calls[most_called_class]
                
                if most_calls / total_external_calls > 0.6:  # 60%以上的调用集中在一个类
                    method_node = graph.get_node_by_id(method_id)
                    element = self._node_to_element(method_node)
                    
                    risk = {
                        "id": f"feature_envy_{method_id}",
                        "title": "特性嫉妒",
                        "description": f"方法 {method_node.label} 过度依赖类 {most_called_class}",
                        "category": RiskCategory.ARCHITECTURE.value,
                        "level": RiskLevel.LOW.value,
                        "file_path": element.file_path if element else "",
                        "line_number": element.line_number if element else 0,
                        "element_id": method_id,
                        "suggestion": "考虑将方法移动到更合适的类中",
                        "metadata": {
                            "external_calls": external_calls,
                            "most_called_class": most_called_class,
                            "call_ratio": most_calls / total_external_calls
                        }
                    }
                    risks.append(risk)
        
        return risks
    
    def _get_method_class(self, graph: CodeGraph, method_id: str) -> Optional[str]:
        """获取方法所属的类"""
        for edge in graph.edges:
            if edge.target_id == method_id and edge.type == "defines":
                source_node = graph.get_node_by_id(edge.source_id)
                if source_node and source_node.type == "class":
                    return edge.source_id
        return None
    
    async def analyze_code_quality(self, graph: CodeGraph) -> Dict[str, Any]:
        """分析代码质量"""
        quality_metrics = {
            "total_elements": len(graph.nodes),
            "complexity_distribution": {},
            "quality_issues": [],
            "quality_score": 0.0,
            "recommendations": []
        }
        
        complexity_sum = 0
        complexity_count = 0
        high_complexity_methods = []
        
        # 分析复杂度分布
        for node in graph.nodes:
            if node.type in ["method", "function"]:
                complexity = node.get_property("complexity", 0)
                if complexity > 0:
                    complexity_sum += complexity
                    complexity_count += 1
                    
                    if complexity > self.quality_thresholds["max_method_complexity"]:
                        high_complexity_methods.append({
                            "id": node.id,
                            "name": node.label,
                            "complexity": complexity,
                            "file_path": node.get_property("file_path", ""),
                            "line_number": node.get_property("line_number", 0)
                        })
        
        # 计算平均复杂度
        avg_complexity = complexity_sum / complexity_count if complexity_count > 0 else 0
        quality_metrics["complexity_distribution"] = {
            "average": avg_complexity,
            "high_complexity_methods": high_complexity_methods
        }
        
        # 生成质量问题
        for method in high_complexity_methods:
            quality_metrics["quality_issues"].append({
                "id": f"high_complexity_{method['id']}",
                "title": "高复杂度方法",
                "description": f"方法 {method['name']} 的复杂度为 {method['complexity']}，超过推荐值 {self.quality_thresholds['max_method_complexity']}",
                "category": RiskCategory.QUALITY.value,
                "level": RiskLevel.MEDIUM.value,
                "file_path": method["file_path"],
                "line_number": method["line_number"],
                "suggestion": "考虑将复杂方法拆分为多个简单方法"
            })
        
        # 计算质量分数 (0-100)
        base_score = 100
        complexity_penalty = min(len(high_complexity_methods) * 5, 30)  # 最多扣30分
        quality_metrics["quality_score"] = max(base_score - complexity_penalty, 0)
        
        # 生成建议
        if high_complexity_methods:
            quality_metrics["recommendations"].append("降低方法复杂度，提高代码可读性")
        if avg_complexity > 8:
            quality_metrics["recommendations"].append("整体代码复杂度偏高，建议重构")
        
        return quality_metrics
    
    async def generate_risk_report(self, risks: List[Dict[str, Any]]) -> str:
        """生成风险报告"""
        if not risks:
            return "# 风险检测报告\n\n✅ 未发现任何风险问题。"
        
        # 按风险等级分组
        risk_by_level = {
            RiskLevel.CRITICAL.value: [],
            RiskLevel.HIGH.value: [],
            RiskLevel.MEDIUM.value: [],
            RiskLevel.LOW.value: []
        }
        
        for risk in risks:
            level = risk.get("level", RiskLevel.LOW.value)
            # 验证风险等级是否有效
            if level in risk_by_level:
                risk_by_level[level].append(risk)
            else:
                # 如果等级无效，归类为低风险
                risk_by_level[RiskLevel.LOW.value].append(risk)
        
        # 生成报告
        report = ["# 风险检测报告\n"]
        
        # 总览
        total_risks = len(risks)
        critical_count = len(risk_by_level[RiskLevel.CRITICAL.value])
        high_count = len(risk_by_level[RiskLevel.HIGH.value])
        medium_count = len(risk_by_level[RiskLevel.MEDIUM.value])
        low_count = len(risk_by_level[RiskLevel.LOW.value])
        
        report.append("## 风险总览\n")
        report.append(f"- 总计风险: {total_risks}")
        report.append(f"- 🔴 严重: {critical_count}")
        report.append(f"- 🟠 高风险: {high_count}")
        report.append(f"- 🟡 中风险: {medium_count}")
        report.append(f"- 🟢 低风险: {low_count}\n")
        
        # 详细风险列表
        for level in [RiskLevel.CRITICAL.value, RiskLevel.HIGH.value, RiskLevel.MEDIUM.value, RiskLevel.LOW.value]:
            level_risks = risk_by_level[level]
            if level_risks:
                level_emoji = {
                    RiskLevel.CRITICAL.value: "🔴",
                    RiskLevel.HIGH.value: "🟠",
                    RiskLevel.MEDIUM.value: "🟡",
                    RiskLevel.LOW.value: "🟢"
                }
                
                report.append(f"## {level_emoji[level]} {level.upper()} 风险\n")
                
                for risk in level_risks:
                    report.append(f"### {risk['title']}")
                    report.append(f"**描述**: {risk['description']}")
                    report.append(f"**类别**: {risk['category']}")
                    if risk.get('file_path'):
                        report.append(f"**文件**: {risk['file_path']}:{risk.get('line_number', 0)}")
                    if risk.get('suggestion'):
                        report.append(f"**建议**: {risk['suggestion']}")
                    report.append("")
        
        return "\n".join(report)
    
    async def analyze_with_ai(self, graph: CodeGraph) -> List[Dict[str, Any]]:
        """使用AI进行深度风险分析
        
        Args:
            graph: 代码知识图谱
            
        Returns:
            AI分析的风险列表
        """
        if not self.ai_layer:
            return []
        
        try:
            # 使用AI层进行风险检测
            ai_risks = await self.ai_layer.detect_risks(graph)
            
            # 转换AI检测结果为标准格式
            standardized_risks = []
            for risk in ai_risks:
                standardized_risk = self._standardize_ai_risk(risk)
                if standardized_risk:
                    standardized_risks.append(standardized_risk)
            
            return standardized_risks
            
        except Exception as e:
            # AI分析失败时记录错误但不影响其他分析
            print(f"AI风险分析失败: {e}")
            return []
    
    def _standardize_ai_risk(self, ai_risk: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """标准化AI检测的风险格式
        
        Args:
            ai_risk: AI返回的风险信息
            
        Returns:
            标准化的风险信息
        """
        try:
            # 映射AI风险等级到标准等级
            severity_mapping = {
                "critical": RiskLevel.CRITICAL.value,
                "high": RiskLevel.HIGH.value,
                "medium": RiskLevel.MEDIUM.value,
                "low": RiskLevel.LOW.value,
                "info": RiskLevel.LOW.value
            }
            
            # 映射AI风险类型到标准类别
            type_mapping = {
                "security": RiskCategory.SECURITY.value,
                "architecture": RiskCategory.ARCHITECTURE.value,
                "quality": RiskCategory.QUALITY.value,
                "performance": RiskCategory.PERFORMANCE.value,
                "maintainability": RiskCategory.MAINTAINABILITY.value
            }
            
            severity = ai_risk.get("severity", "low")
            risk_type = ai_risk.get("type", "quality")
            
            return {
                "id": f"ai_risk_{hash(str(ai_risk))}",
                "title": ai_risk.get("title", f"AI检测风险: {risk_type}"),
                "description": ai_risk.get("description", "AI检测到的潜在风险"),
                "category": type_mapping.get(risk_type, RiskCategory.QUALITY.value),
                "level": severity_mapping.get(severity, RiskLevel.LOW.value),
                "file_path": ai_risk.get("location", ""),
                "line_number": ai_risk.get("line_number", 0),
                "suggestion": ai_risk.get("suggestion", "请根据具体情况进行修复"),
                "metadata": {
                    "ai_generated": True,
                    "confidence": ai_risk.get("confidence", 0.5),
                    "original_ai_response": ai_risk
                }
            }
            
        except Exception as e:
            print(f"标准化AI风险失败: {e}")
            return None
    
    async def enhanced_security_analysis(self, graph: CodeGraph) -> List[Dict[str, Any]]:
        """AI增强的安全分析
        
        Args:
            graph: 代码知识图谱
            
        Returns:
            增强的安全风险列表
        """
        # 先进行基础的静态分析
        static_risks = await self.scan_security_risks(graph)
        
        # 如果有AI层，进行深度分析
        if self.ai_layer:
            try:
                # 构建安全分析上下文
                security_context = self._build_security_context(graph, static_risks)
                
                # 使用AI进行深度安全分析
                ai_analysis = await self.ai_layer.analyze_code_quality(
                    self._graph_to_code_element(graph)
                )
                
                # 提取安全相关的AI建议
                ai_security_risks = self._extract_security_risks_from_ai(ai_analysis)
                
                # 合并静态分析和AI分析结果
                return static_risks + ai_security_risks
                
            except Exception as e:
                print(f"AI安全分析失败: {e}")
                return static_risks
        
        return static_risks
    
    def _build_security_context(self, graph: CodeGraph, static_risks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """构建安全分析上下文
        
        Args:
            graph: 代码知识图谱
            static_risks: 静态分析发现的风险
            
        Returns:
            安全分析上下文
        """
        return {
            "graph_summary": {
                "total_nodes": len(graph.nodes),
                "total_edges": len(graph.edges),
                "node_types": self._count_node_types(graph),
                "edge_types": self._count_edge_types(graph)
            },
            "static_risks_count": len(static_risks),
            "high_risk_files": self._identify_high_risk_files(static_risks),
            "security_patterns": self._identify_security_patterns(graph)
        }
    
    def _count_node_types(self, graph: CodeGraph) -> Dict[str, int]:
        """统计节点类型"""
        node_types = {}
        for node in graph.nodes:
            node_type = getattr(node, 'type', 'unknown')
            node_types[node_type] = node_types.get(node_type, 0) + 1
        return node_types
    
    def _count_edge_types(self, graph: CodeGraph) -> Dict[str, int]:
        """统计边类型"""
        edge_types = {}
        for edge in graph.edges:
            edge_type = getattr(edge, 'type', 'unknown')
            edge_types[edge_type] = edge_types.get(edge_type, 0) + 1
        return edge_types
    
    def _identify_high_risk_files(self, risks: List[Dict[str, Any]]) -> List[str]:
        """识别高风险文件"""
        file_risk_count = {}
        for risk in risks:
            file_path = risk.get("file_path", "")
            if file_path:
                file_risk_count[file_path] = file_risk_count.get(file_path, 0) + 1
        
        # 返回风险数量最多的前5个文件
        sorted_files = sorted(file_risk_count.items(), key=lambda x: x[1], reverse=True)
        return [file_path for file_path, _ in sorted_files[:5]]
    
    def _identify_security_patterns(self, graph: CodeGraph) -> List[str]:
        """识别安全相关的模式"""
        patterns = []
        
        # 检查是否有认证相关的类或方法
        auth_keywords = ["auth", "login", "password", "token", "session"]
        for node in graph.nodes:
            node_name = getattr(node, 'label', '').lower()
            if any(keyword in node_name for keyword in auth_keywords):
                patterns.append(f"认证相关组件: {node.label}")
        
        # 检查是否有数据库相关的操作
        db_keywords = ["database", "sql", "query", "connection"]
        for node in graph.nodes:
            node_name = getattr(node, 'label', '').lower()
            if any(keyword in node_name for keyword in db_keywords):
                patterns.append(f"数据库相关组件: {node.label}")
        
        return patterns
    
    def _graph_to_code_element(self, graph: CodeGraph) -> CodeElement:
        """将图谱转换为代码元素用于AI分析"""
        # 创建一个虚拟的代码元素来表示整个图谱
        return CodeElement(
            id="graph_summary",
            name="CodeGraph",
            type=ElementType.MODULE,
            file_path="",
            line_number=0,
            metadata={
                "node_count": len(graph.nodes),
                "edge_count": len(graph.edges),
                "node_types": self._count_node_types(graph),
                "edge_types": self._count_edge_types(graph)
            }
        )
    
    def _extract_security_risks_from_ai(self, ai_analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """从AI分析结果中提取安全风险"""
        risks = []
        
        # 从AI分析的问题列表中提取安全相关问题
        issues = ai_analysis.get("issues", [])
        for issue in issues:
            if isinstance(issue, dict):
                issue_type = issue.get("type", "").lower()
                if any(keyword in issue_type for keyword in ["security", "auth", "sql", "xss", "injection"]):
                    risk = {
                        "id": f"ai_security_{hash(str(issue))}",
                        "title": f"AI检测安全风险: {issue.get('type', '未知')}",
                        "description": issue.get("description", "AI检测到的安全相关问题"),
                        "category": RiskCategory.SECURITY.value,
                        "level": self._map_ai_severity_to_risk_level(issue.get("severity", "medium")),
                        "file_path": issue.get("file_path", ""),
                        "line_number": issue.get("line_number", 0),
                        "suggestion": issue.get("suggestion", "请根据AI建议进行安全加固"),
                        "metadata": {
                            "ai_generated": True,
                            "ai_confidence": issue.get("confidence", 0.7),
                            "original_issue": issue
                        }
                    }
                    risks.append(risk)
        
        return risks
    
    def _map_ai_severity_to_risk_level(self, ai_severity: str) -> str:
        """将AI严重程度映射到风险等级"""
        severity_mapping = {
            "critical": RiskLevel.CRITICAL.value,
            "high": RiskLevel.HIGH.value,
            "medium": RiskLevel.MEDIUM.value,
            "low": RiskLevel.LOW.value
        }
        return severity_mapping.get(ai_severity.lower(), RiskLevel.MEDIUM.value)
    
    async def generate_enhanced_risk_report(self, graph: CodeGraph) -> str:
        """生成AI增强的风险报告
        
        Args:
            graph: 代码知识图谱
            
        Returns:
            增强的风险报告
        """
        # 收集所有类型的风险
        all_risks = []
        
        # 静态安全分析
        security_risks = await self.scan_security_risks(graph)
        all_risks.extend(security_risks)
        
        # 架构坏味检测
        architecture_smells = await self.detect_architecture_smells(graph)
        all_risks.extend(architecture_smells)
        
        # 代码质量分析
        quality_analysis = await self.analyze_code_quality(graph)
        quality_risks = quality_analysis.get("quality_issues", [])
        all_risks.extend(quality_risks)
        
        # AI增强分析
        if self.ai_layer:
            ai_risks = await self.analyze_with_ai(graph)
            all_risks.extend(ai_risks)
        
        # 生成综合报告
        base_report = await self.generate_risk_report(all_risks)
        
        # 添加AI增强的洞察
        if self.ai_layer:
            ai_insights = await self._generate_ai_insights(graph, all_risks)
            enhanced_report = base_report + "\n\n" + ai_insights
            return enhanced_report
        
        return base_report
    
    async def _generate_ai_insights(self, graph: CodeGraph, risks: List[Dict[str, Any]]) -> str:
        """生成AI洞察"""
        try:
            # 构建洞察生成的上下文
            context = {
                "graph_summary": self._build_security_context(graph, risks),
                "risk_summary": {
                    "total_risks": len(risks),
                    "risk_categories": self._categorize_risks(risks),
                    "high_priority_risks": [r for r in risks if r.get("level") in ["critical", "high"]]
                }
            }
            
            # 使用AI生成洞察
            insights_prompt = f"""
基于以下代码分析结果，请提供深度洞察和建议：

图谱信息：
{context['graph_summary']}

风险摘要：
{context['risk_summary']}

请提供：
1. 整体安全态势评估
2. 主要风险趋势分析
3. 优先修复建议
4. 长期改进策略
"""
            
            ai_response = await self.ai_layer.answer_question(
                insights_prompt, 
                context
            )
            
            return f"## 🤖 AI深度洞察\n\n{ai_response}"
            
        except Exception as e:
            return f"## 🤖 AI深度洞察\n\n⚠️ AI洞察生成失败: {e}"
    
    def _categorize_risks(self, risks: List[Dict[str, Any]]) -> Dict[str, int]:
        """按类别统计风险"""
        categories = {}
        for risk in risks:
            category = risk.get("category", "unknown")
            categories[category] = categories.get(category, 0) + 1
        return categories
    
    def _node_to_element(self, node: GraphNode) -> Optional[CodeElement]:
        """将图节点转换为代码元素"""
        if not node:
            return None
        
        try:
            element_type = ElementType(node.type)
        except ValueError:
            element_type = ElementType.CLASS
        
        return CodeElement(
            id=node.id,
            name=node.label,
            type=element_type,
            file_path=node.get_property("file_path", ""),
            line_number=node.get_property("line_number", 0),
            complexity=node.get_property("complexity", 0),
            docstring=node.get_property("docstring", "")
        )