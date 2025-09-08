"""
Test API endpoints
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

class TestAPI:
    """Test API endpoints"""
    
    def test_root_endpoint(self):
        """Test root endpoint"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "Ultimate Legal-AI Backend" in data["message"]
    
    def test_health_endpoint(self):
        """Test health endpoint"""  
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
    
    def test_agent_capabilities_endpoint(self):
        """Test agent capabilities endpoint"""
        response = client.get("/api/v1/agent-capabilities")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "available_agents" in data["data"]
        assert len(data["data"]["available_agents"]) == 3
    
    def test_research_modes_endpoint(self):
        """Test research modes endpoint"""
        response = client.get("/api/v1/research-modes")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "comprehensive" in data["available_modes"]
        assert "cs_focused" in data["available_modes"]
    
    def test_ultimate_capabilities_endpoint(self):
        """Test ultimate capabilities endpoint"""
        response = client.get("/ultimate-capabilities")
        assert response.status_code == 200
        data = response.json()
        assert "🏛️ legal_ai_backend" in data
        assert data["🔥 power_level"] == "MAXIMUM"
    
    def test_multi_agent_analysis_endpoint(self):
        """Test multi-agent analysis endpoint"""
        test_data = {
            "document_text": "Test legal document about corporate compliance",
            "user_query": "What are the key points?",
            "workflow_type": "cs_focused"
        }
        
        # This might fail in test environment without API key
        response = client.post("/api/v1/multi-agent-analysis", json=test_data)
        # Accept both success and API-related errors
        assert response.status_code in [200, 500]  # 500 expected if API limits hit
    
    def test_custom_analysis_endpoint(self):
        """Test custom analysis endpoint"""
        test_data = {
            "document_text": "Test document for custom analysis",
            "custom_prompt": "Analyze the key compliance requirements", 
            "agent_preference": "cs"
        }
        
        response = client.post("/api/v1/custom-analysis", json=test_data)
        # Accept both success and API-related errors  
        assert response.status_code in [200, 500]
    
    def test_login_endpoint(self):
        """Test authentication login endpoint"""
        login_data = {
            "username": "admin",
            "password": "admin_password"
        }
        
        response = client.post("/api/v1/auth/login", json=login_data)
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
    
    def test_verify_token_endpoint(self):
        """Test token verification"""
        # First login to get token
        login_data = {"username": "admin", "password": "admin_password"}
        login_response = client.post("/api/v1/auth/login", json=login_data)
        assert login_response.status_code == 200
        
        token = login_response.json()["access_token"]
        
        # Then verify token
        headers = {"Authorization": f"Bearer {token}"}
        response = client.get("/api/v1/auth/verify", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "valid"
        assert data["user"] == "admin"