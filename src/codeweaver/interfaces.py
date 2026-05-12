"""
核心接口定义

定义codenexus系统各组件的抽象接口。
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from .models.core import (
    CodeElement,
    CodeGraph,
    FileParseResult,
    GraphNode,
    ParseResult,
    Relationship,
)


class CodeParserInterface(ABC):
    """代码解析器接口"""
    
    @abstractmethod
    def parse_project(self, project_path: str) -> List[ParseResult]:
        """解析整个项目"""
        pass
    
    @abstractmethod
    def parse_file(self, file_path: str) -> FileParseResult:
        """解析单个文件"""
        pass
    
    @abstractmethod
    def extract_elements(self, ast: Any) -> List[CodeElement]:
        """从AST提取代码元素"""
        pass
    
    @abstractmethod
    def extract_relationships(self, ast: Any, elements: List[CodeElement]) -> List[Relationship]:
        """从AST提取关系"""
        pass
    
    @abstractmethod
    def get_supported_languages(self) -> List[str]:
        """获取支持的编程语言列表"""
        pass


class GraphBuilderInterface(ABC):
    """图构建器接口"""
    
    @abstractmethod
    def build_graph(self, parse_results: List[ParseResult]) -> CodeGraph:
        """构建代码知识图谱"""
        pass
    
    @abstractmethod
    def create_nodes(self, elements: List[CodeElement]) -> List[GraphNode]:
        """创建图节点"""
        pass
    
    @abstractmethod
    def create_edges(self, relationships: List[Relationship]) -> List[tuple]:
        """创建图边"""
        pass
    
    @abstractmethod
    def optimize_graph(self, graph: CodeGraph) -> CodeGraph:
        """优化图结构"""
        pass
    
    @abstractmethod
    def merge_graphs(self, graphs: List[CodeGraph]) -> CodeGraph:
        """合并多个图"""
        pass


class GraphDatabaseInterface(ABC):
    """图数据库接口"""
    
    @abstractmethod
    async def connect(self) -> bool:
        """连接数据库"""
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """断开数据库连接"""
        pass
    
    @abstractmethod
    async def store_graph(self, graph: CodeGraph) -> bool:
        """存储图到数据库"""
        pass
    
    @abstractmethod
    async def query_nodes(self, query: Dict[str, Any]) -> List[GraphNode]:
        """查询节点"""
        pass
    
    @abstractmethod
    async def query_edges(self, query: Dict[str, Any]) -> List[tuple]:
        """查询边"""
        pass
    
    @abstractmethod
    async def find_paths(self, start_id: str, end_id: str, max_depth: int = 10) -> List[List[str]]:
        """查找路径"""
        pass
    
    @abstractmethod
    async def analyze_impact(self, node_id: str) -> Dict[str, Any]:
        """影响分析"""
        pass
    
    @abstractmethod
    async def get_graph_statistics(self) -> Dict[str, Any]:
        """获取图统计信息"""
        pass


class AILayerInterface(ABC):
    """AI智能层接口"""
    
    @abstractmethod
    async def generate_documentation(self, context: Dict[str, Any]) -> str:
        """生成文档"""
        pass
    
    @abstractmethod
    async def answer_question(self, question: str, context: Dict[str, Any]) -> str:
        """回答问题"""
        pass
    
    @abstractmethod
    async def analyze_code_quality(self, code: CodeElement) -> Dict[str, Any]:
        """分析代码质量"""
        pass
    
    @abstractmethod
    async def suggest_improvements(self, issues: List[Dict[str, Any]]) -> List[str]:
        """建议改进"""
        pass
    
    @abstractmethod
    async def detect_risks(self, graph: CodeGraph) -> List[Dict[str, Any]]:
        """检测风险"""
        pass


class VisualizationServiceInterface(ABC):
    """可视化服务接口"""
    
    @abstractmethod
    async def generate_graph_data(self, graph: CodeGraph, filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """生成图可视化数据"""
        pass
    
    @abstractmethod
    async def generate_impact_visualization(self, impact_data: Dict[str, Any]) -> Dict[str, Any]:
        """生成影响分析可视化数据"""
        pass
    
    @abstractmethod
    async def apply_layout(self, graph_data: Dict[str, Any], layout_type: str = "force") -> Dict[str, Any]:
        """应用布局算法"""
        pass


class DocumentationServiceInterface(ABC):
    """文档生成服务接口"""
    
    @abstractmethod
    async def generate_api_documentation(self, elements: List[CodeElement]) -> str:
        """生成API文档"""
        pass
    
    @abstractmethod
    async def generate_module_documentation(self, module_elements: List[CodeElement]) -> str:
        """生成模块文档"""
        pass
    
    @abstractmethod
    async def export_documentation(self, content: str, format_type: str = "markdown") -> bytes:
        """导出文档"""
        pass


class QAServiceInterface(ABC):
    """问答服务接口"""
    
    @abstractmethod
    async def process_question(self, question: str, graph: CodeGraph) -> Dict[str, Any]:
        """处理问题"""
        pass
    
    @abstractmethod
    async def locate_relevant_code(self, question: str, graph: CodeGraph) -> List[CodeElement]:
        """定位相关代码"""
        pass
    
    @abstractmethod
    async def generate_answer(self, question: str, relevant_code: List[CodeElement]) -> str:
        """生成答案"""
        pass


class RiskDetectionServiceInterface(ABC):
    """风险检测服务接口"""
    
    @abstractmethod
    async def scan_security_risks(self, graph: CodeGraph) -> List[Dict[str, Any]]:
        """扫描安全风险"""
        pass
    
    @abstractmethod
    async def detect_architecture_smells(self, graph: CodeGraph) -> List[Dict[str, Any]]:
        """检测架构坏味"""
        pass
    
    @abstractmethod
    async def analyze_code_quality(self, graph: CodeGraph) -> Dict[str, Any]:
        """分析代码质量"""
        pass
    
    @abstractmethod
    async def generate_risk_report(self, risks: List[Dict[str, Any]]) -> str:
        """生成风险报告"""
        pass


class ImpactAnalyzerInterface(ABC):
    """影响分析器接口"""
    
    @abstractmethod
    async def analyze_change_impact(self, node_id: str, graph: CodeGraph) -> Dict[str, Any]:
        """分析变更影响"""
        pass
    
    @abstractmethod
    async def calculate_impact_metrics(self, impact_data: Dict[str, Any]) -> Dict[str, float]:
        """计算影响指标"""
        pass
    
    @abstractmethod
    async def rank_impact_severity(self, impacts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """按影响严重程度排序"""
        pass