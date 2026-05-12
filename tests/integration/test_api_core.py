"""
核心API端点集成测试

测试最重要的API端点功能。
"""

import pytest
import tempfile
import os
from fastapi.testclient import TestClient

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


class TestCoreAPI:
    """核心API功能测试"""
    
    def test_root_endpoint(self, client):
        """测试根端点"""
        response = client.get("/")
        assert response.status_code == 200
        
        data = response.json()
        assert "message" in data
        assert "version" in data
        assert data["version"] == "0.1.0"
    
    def test_health_check(self, client):
        """测试健康检查"""
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        
        data = response.json()
        assert "status" in data
        assert "services" in data
        assert data["status"] in ["healthy", "degraded", "unhealthy"]
    
    def test_ping(self, client):
        """测试ping"""
        response = client.get("/api/v1/ping")
        assert response.status_code == 200
        
        data = response.json()
        assert data["message"] == "pong"
    
    def test_parser_languages(self, client):
        """测试获取支持的语言"""
        response = client.get("/api/v1/parser/languages")
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert "languages" in data
        assert isinstance(data["languages"], list)
    
    def test_parser_status(self, client):
        """测试解析器状态"""
        response = client.get("/api/v1/parser/status")
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert data["status"] == "healthy"
    
    def test_parse_project_success(self, client, temp_project_dir):
        """测试解析项目成功"""
        request_data = {
            "project_path": temp_project_dir,
            "languages": ["python"]
        }
        
        response = client.post("/api/v1/parser/project", json=request_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert "elements" in data
        assert "relationships" in data
        assert isinstance(data["elements"], list)
    
    def test_parse_project_invalid_path(self, client):
        """测试解析无效路径"""
        request_data = {
            "project_path": "/nonexistent/path"
        }
        
        response = client.post("/api/v1/parser/project", json=request_data)
        assert response.status_code == 404
    
    def test_graph_query(self, client):
        """测试图查询"""
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
    
    def test_graph_statistics(self, client):
        """测试图统计"""
        response = client.get("/api/v1/graph/statistics")
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert "statistics" in data
    
    def test_qa_ask_question(self, client):
        """测试问答"""
        request_data = {
            "question": "这个项目的主要功能是什么？"
        }
        
        response = client.post("/api/v1/qa/ask", json=request_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert "answer" in data
        assert "relevant_code" in data
    
    def test_qa_suggestions(self, client):
        """测试问题建议"""
        response = client.get("/api/v1/qa/suggestions")
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert "suggestions" in data
    
    def test_risk_scan(self, client):
        """测试风险扫描"""
        request_data = {
            "scan_types": ["security", "quality"]
        }
        
        response = client.post("/api/v1/risk/scan", json=request_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert "issues" in data
        assert "summary" in data
    
    def test_risk_rules(self, client):
        """测试获取检测规则"""
        response = client.get("/api/v1/risk/rules")
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert "rules" in data
    
    def test_visualization_layouts(self, client):
        """测试获取布局"""
        response = client.get("/api/v1/viz/layouts")
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert "layouts" in data
    
    def test_visualization_themes(self, client):
        """测试获取主题"""
        response = client.get("/api/v1/viz/themes")
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert "themes" in data
    
    def test_documentation_templates(self, client):
        """测试获取文档模板"""
        response = client.get("/api/v1/docs/templates")
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert "templates" in data


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
    
    def test_nonexistent_endpoint(self, client):
        """测试不存在的端点"""
        response = client.get("/api/v1/nonexistent")
        assert response.status_code == 404


if __name__ == "__main__":
    pytest.main([__file__, "-v"])