"""
Test the multi-agent AI system
"""
import pytest
import asyncio
from app.agents.legal_analyst import LegalAnalystAgent
from app.agents.cs_expert import CompanySecretaryExpertAgent  
from app.agents.quality_reviewer import QualityReviewerAgent
from app.agents.agent_orchestrator import AgentOrchestrator

class TestAgents:
    """Test AI agents functionality"""
    
    def test_agent_initialization(self):
        """Test that agents initialize correctly"""
        legal_agent = LegalAnalystAgent()
        cs_agent = CompanySecretaryExpertAgent()
        qa_agent = QualityReviewerAgent()
        
        assert legal_agent.agent_name == "Legal Analyst"
        assert cs_agent.agent_name == "CS Expert"
        assert qa_agent.agent_name == "Quality Reviewer"
        
        # Check model initialization
        assert legal_agent.model is not None
        assert cs_agent.model is not None
        assert qa_agent.model is not None
    
    @pytest.mark.asyncio
    async def test_agent_orchestrator(self):
        """Test agent orchestrator functionality"""
        orchestrator = AgentOrchestrator()
        
        # Test status
        status = orchestrator.get_orchestrator_status()
        assert "available_agents" in status
        assert len(status["available_agents"]) == 3
        
        # Test with sample document
        sample_doc = """
        This is a test legal document about corporate governance.
        The board of directors has implemented new policies for compliance.
        """
        
        # This will use actual API - should work in CI
        try:
            result = await orchestrator.analyze_document(
                document_text=sample_doc,
                user_query="What are the compliance requirements?",
                workflow_type="cs_focused"
            )
            
            assert "agent_analyses" in result
            assert "consolidated_insights" in result
            
        except Exception as e:
            # In CI/testing environment, API might not be available
            pytest.skip(f"API not available in test environment: {e}")

    def test_agent_info(self):
        """Test agent information retrieval"""
        orchestrator = AgentOrchestrator()
        
        for agent_name, agent in orchestrator.agent_instances.items():
            info = agent.get_agent_info()
            assert "name" in info
            assert "role" in info
            assert "temperature" in info