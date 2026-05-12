"""
API端点集成测试

测试所有API端点的功能和错误处理，验证请求响应格式的正确性。
"""

import pytest
import asyncio
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch
import json
import tempfile
import os

from src.codenexus.api.app import create_app


@pytest.fixture
def client():
    """创建测试客户端"""
    app = create_app()
    return TestClient(app)


@pytest.fixture
def temp_project_dir():
    """创建临时项目目录用于测试"""
    with tempfile.TemporaryDirectory() as temp_dir:
        # 创建一个简单的Python文件用于测试
        test_file = os.path.join(temp_dir, "test.py")
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("""
def hello_world():
    '''简单的测试函数'''
    return "Hello, World!"

class TestClass:
    '''测试类'''
    def __init__(self):
        self.value = 42
    
    def get_value(self):
        return self.value
""")
        yield temp_dir


class TestHealthEndpoints:
    """健康检查端点测试"""
    
    def test_health_check(self, client):
        """测试基本健康检查"""
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        
        data = response.json()
        assert "status" in data
        assert "services" in data
        assert "timestamp" in data
        assert data["status"] in ["healthy", "degraded", "unhealthy"]
    
    def test_detailed_health_check(self, client):
        """测试详细健康检查"""
        response = client.get("/api/v1/health/detailed")
        assert response.status_code == 200
        
        data = response.json()
        assert "status" in data
        assert "system" in data
        assert "services" in data
        assert "uptime" in data
    
    def test_ping(self, client):
        """测试ping端点"""
        response = client.get("/api/v1/ping")
        assert response.status_code == 200
        
        data = response.json()
        assert data["message"] == "pong"
        assert "timestamp" in data


class TestParserEndpoints:
    """代码解析端点测试"""
    
    def test_parse_project_success(self, client, temp_project_dir):
        """测试成功解析项目"""
        request_data = {
            "project_path": temp_project_dir,
            "languages": ["python"],
            "include_tests": True
        }
        
        response = client.post("/api/v1/parser/project", json=request_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert "elements" in data
        assert "relationships" in data
        assert "statistics" in data
        assert isinstance(data["elements"], list)
        assert isinstance(data["relationships"], list)
    
    def test_parse_project_invalid_path(self, client):
        """测试解析不存在的项目路径"""
        request_data = {
            "project_path": "/nonexistent/path",
            "languages": ["python"]
        }
        
        response = client.post("/api/v1/parser/project", json=request_data)
        assert response.status_code == 404
        
        data = response.json()
        assert "error" in data
        assert "项目路径不存在" in data["detail"]
    
    def test_parse_file_success(self, client, temp_project_dir):
        """测试成功解析文件"""
        test_file = os.path.join(temp_project_dir, "test.py")
        
        request_data = {
            "file_path": test_file,
            "language": "python"
        }
        
        response = client.post("/api/v1/parser/file", json=request_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert "elements" in data
        assert "relationships" in data
        assert isinstance(data["elements"], list)
    
    def test_parse_file_invalid_path(self, client):
        """测试解析不存在的文件"""
        request_data = {
            "file_path": "/nonexistent/file.py",
            "language": "python"
        }
        
        response = client.post("/api/v1/parser/file", json=request_data)
        assert response.status_code == 404
    
    def test_get_supported_languages(self, client):
        """测试获取支持的编程语言"""
        response = client.get("/api/v1/parser/languages")
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert "languages" in data
        assert isinstance(data["languages"], list)
        assert len(data["languages"]) > 0
    
    def test_get_parser_status(self, client):
        """测试获取解析器状态"""
        response = client.get("/api/v1/parser/status")
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert data["status"] == "healthy"
        assert "capabilities" in data


class TestGraphEndpoints:
    """图查询端点测试"""
    
    def test_query_graph_nodes(self, client):
        """测试查询图节点"""
        request_data = {
            "query_type": "nodes",
            "parameters": {},
            "limit": 10
        }
        
        response = client.post("/api/v1/graph/query", json=request_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert "nodes" in data
        assert "edges" in data
        assert "total_count" in data
        assert isinstance(data["nodes"], list)
    
    def test_query_graph_invalid_type(self, client):
        """测试无效的查询类型"""
        request_data = {
            "query_type": "invalid_type",
            "parameters": {}
        }
        
        response = client.post("/api/v1/graph/query", json=request_data)
        assert response.status_code == 400
        
        data = response.json()
        assert "不支持的查询类型" in data["detail"]
    
    def test_get_node_nonexistent(self, client):
        """测试获取不存在的节点"""
        response = client.get("/api/v1/graph/nodes/nonexistent_id")
        assert response.status_code == 404
        
        data = response.json()
        assert "节点不存在" in data["detail"]
    
    def test_find_paths(self, client):
        """测试查找路径"""
        response = client.get("/api/v1/graph/paths/node1/node2?max_depth=3")
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert "paths" in data
        assert "count" in data
        assert isinstance(data["paths"], list)
    
    def test_impact_analysis(self, client):
        """测试影响分析"""
        request_data = {
            "node_id": "test_node",
            "max_depth": 3,
            "include_reverse": True
        }
        
        response = client.post("/api/v1/graph/impact-analysis", json=request_data)
        # 由于节点不存在，应该返回404
        assert response.status_code == 404
    
    def test_get_graph_statistics(self, client):
        """测试获取图统计信息"""
        response = client.get("/api/v1/graph/statistics")
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert "statistics" in data


class TestDocumentationEndpoints:
    """文档生成端点测试"""
    
    def test_generate_documentation(self, client):
        """测试生成文档"""
        request_data = {
            "target_type": "api",
            "target_ids": ["test_id"],
            "format_type": "markdown",
            "include_examples": True
        }
        
        response = client.post("/api/v1/docs/generate", json=request_data)
        # 由于目标不存在，应该返回404
        assert response.status_code == 404
    
    def test_export_documentation(self, client):
        """测试导出文档"""
        response = client.post(
            "/api/v1/docs/export?format_type=html",
            data="# Test Documentation\n\nThis is a test."
        )
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/html; charset=utf-8"
    
    def test_get_documentation_templates(self, client):
        """测试获取文档模板"""
        response = client.get("/api/v1/docs/templates")
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert "templates" in data
        assert isinstance(data["templates"], list)


class TestQAEndpoints:
    """问答端点测试"""
    
    def test_ask_question(self, client):
        """测试提问"""
        request_data = {
            "question": "这个项目的主要功能是什么？",
            "language": "zh"
        }
        
        response = client.post("/api/v1/qa/ask", json=request_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert "answer" in data
        assert "relevant_code" in data
        assert "confidence" in data
    
    def test_ask_empty_question(self, client):
        """测试空问题"""
        request_data = {
            "question": "",
            "language": "zh"
        }
        
        response = client.post("/api/v1/qa/ask", json=request_data)
        assert response.status_code == 422  # 验证错误
    
    def test_get_question_suggestions(self, client):
        """测试获取问题建议"""
        response = client.get("/api/v1/qa/suggestions?category=general")
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert "suggestions" in data
        assert isinstance(data["suggestions"], list)
    
    def test_get_question_history(self, client):
        """测试获取问题历史"""
        response = client.get("/api/v1/qa/history?limit=10")
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert "history" in data
        assert isinstance(data["history"], list)


class TestRiskEndpoints:
    """风险检测端点测试"""
    
    def test_scan_risks(self, client):
        """测试风险扫描"""
        request_data = {
            "scan_types": ["security", "quality"],
            "include_suggestions": True
        }
        
        response = client.post("/api/v1/risk/scan", json=request_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert "issues" in data
        assert "summary" in data
        assert isinstance(data["issues"], list)
    
    def test_get_issue_details(self, client):
        """测试获取风险问题详情"""
        response = client.get("/api/v1/risk/issues/test_issue_id")
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert "issue" in data
    
    def test_generate_risk_report(self, client):
        """测试生成风险报告"""
        response = client.post("/api/v1/risk/report?format_type=markdown")
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert "report" in data
    
    def test_get_detection_rules(self, client):
        """测试获取检测规则"""
        response = client.get("/api/v1/risk/rules")
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert "rules" in data
        assert isinstance(data["rules"], list)


class TestVisualizationEndpoints:
    """可视化端点测试"""
    
    def test_generate_graph_visualization(self, client):
        """测试生成图可视化"""
        request_data = {
            "graph_type": "full",
            "layout": "force",
            "max_nodes": 100
        }
        
        response = client.post("/api/v1/viz/graph", json=request_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert "nodes" in data
        assert "edges" in data
        assert isinstance(data["nodes"], list)
        assert isinstance(data["edges"], list)
    
    def test_generate_impact_visualization(self, client):
        """测试生成影响分析可视化"""
        response = client.post("/api/v1/viz/impact?node_id=test_node&max_depth=3")
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert "visualization" in data
    
    def test_get_available_layouts(self, client):
        """测试获取可用布局"""
        response = client.get("/api/v1/viz/layouts")
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert "layouts" in data
        assert isinstance(data["layouts"], list)
    
    def test_get_visualization_themes(self, client):
        """测试获取可视化主题"""
        response = client.get("/api/v1/viz/themes")
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert "themes" in data
        assert isinstance(data["themes"], list)


class TestErrorHandling:
    """错误处理测试"""
    
    def test_invalid_json(self, client):
        """测试无效JSON"""
        response = client.post(
            "/api/v1/parser/project",
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 422
    
    def test_missing_required_fields(self, client):
        """测试缺少必需字段"""
        response = client.post("/api/v1/parser/project", json={})
        assert response.status_code == 422
    
    def test_invalid_field_types(self, client):
        """测试无效字段类型"""
        request_data = {
            "project_path": 123,  # 应该是字符串
            "languages": "python"  # 应该是列表
        }
        
        response = client.post("/api/v1/parser/project", json=request_data)
        assert response.status_code == 422


class TestRequestValidation:
    """请求验证测试"""
    
    def test_project_path_validation(self, client):
        """测试项目路径验证"""
        # 空路径
        request_data = {"project_path": ""}
        response = client.post("/api/v1/parser/project", json=request_data)
        assert response.status_code == 422
        
        # 只有空格的路径
        request_data = {"project_path": "   "}
        response = client.post("/api/v1/parser/project", json=request_data)
        assert response.status_code == 422
    
    def test_question_validation(self, client):
        """测试问题验证"""
        # 空问题
        request_data = {"question": ""}
        response = client.post("/api/v1/qa/ask", json=request_data)
        assert response.status_code == 422
        
        # 过长问题
        long_question = "x" * 1001
        request_data = {"question": long_question}
        response = client.post("/api/v1/qa/ask", json=request_data)
        assert response.status_code == 422
    
    def test_pagination_validation(self, client):
        """测试分页参数验证"""
        # 无效的limit值
        response = client.post("/api/v1/graph/query", json={
            "query_type": "nodes",
            "limit": 0  # 应该 >= 1
        })
        assert response.status_code == 422
        
        # 过大的limit值
        response = client.post("/api/v1/graph/query", json={
            "query_type": "nodes",
            "limit": 2000  # 应该 <= 1000
        })
        assert response.status_code == 422


class TestResponseFormat:
    """响应格式测试"""
    
    def test_success_response_format(self, client):
        """测试成功响应格式"""
        response = client.get("/api/v1/parser/languages")
        assert response.status_code == 200
        
        data = response.json()
        # 检查基础响应字段
        assert "success" in data
        assert "message" in data
        assert data["success"] is True
        assert isinstance(data["message"], str)
    
    def test_error_response_format(self, client):
        """测试错误响应格式"""
        response = client.get("/api/v1/graph/nodes/nonexistent")
        assert response.status_code == 404
        
        data = response.json()
        # 检查错误响应字段
        assert "error" in data
        assert "message" in data or "detail" in data
    
    def test_pagination_response_format(self, client):
        """测试分页响应格式"""
        response = client.post("/api/v1/graph/query", json={
            "query_type": "nodes",
            "limit": 10,
            "offset": 0
        })
        assert response.status_code == 200
        
        data = response.json()
        assert "total_count" in data
        assert "has_more" in data
        assert isinstance(data["total_count"], int)
        assert isinstance(data["has_more"], bool)


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v"])