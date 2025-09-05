from typing import Dict, Any, List, Optional
from .legal_analyst import LegalAnalystAgent
from .cs_expert import CompanySecretaryExpertAgent
from .quality_reviewer import QualityReviewerAgent
import asyncio
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class AgentOrchestrator:
    """
    Advanced orchestrator for multi-agent legal analysis system.
    Coordinates between specialized agents to produce premium-quality research outputs.
    """
    
    def __init__(self):
        # Initialize specialized agents
        self.legal_analyst = LegalAnalystAgent()
        self.cs_expert = CompanySecretaryExpertAgent()
        self.quality_reviewer = QualityReviewerAgent()
        
        # Agent coordination settings
        self.analysis_workflows = {
            "comprehensive": ["legal_analyst", "cs_expert", "quality_reviewer"],
            "cs_focused": ["cs_expert", "legal_analyst", "quality_reviewer"],
            "legal_focused": ["legal_analyst", "quality_reviewer"],
            "quick_review": ["cs_expert", "quality_reviewer"]
        }
        
        self.agent_instances = {
            "legal_analyst": self.legal_analyst,
            "cs_expert": self.cs_expert,
            "quality_reviewer": self.quality_reviewer
        }
    
    async def analyze_document(
        self, 
        document_text: str, 
        user_query: str = None, 
        workflow_type: str = "comprehensive",
        context: Dict = None
    ) -> Dict[str, Any]:
        """
        Orchestrate multi-agent analysis of a legal document.
        Returns comprehensive analysis from multiple expert perspectives.
        """
        
        logger.info(f"Starting {workflow_type} analysis with agents")
        
        if workflow_type not in self.analysis_workflows:
            workflow_type = "comprehensive"
        
        agent_sequence = self.analysis_workflows[workflow_type]
        
        # Initialize analysis results
        analysis_results = {
            "document_metadata": {
                "analysis_timestamp": datetime.now().isoformat(),
                "workflow_type": workflow_type,
                "user_query": user_query,
                "agents_involved": agent_sequence
            },
            "agent_analyses": {},
            "consolidated_insights": {},
            "quality_assessment": {},
            "final_summary": {}
        }
        
        # Execute agents in sequence for dependent analyses
        previous_results = {}
        
        for agent_name in agent_sequence:
            if agent_name in self.agent_instances:
                logger.info(f"Executing {agent_name} analysis")
                
                try:
                    # Prepare context with previous results
                    agent_context = {
                        **(context or {}),
                        "previous_analyses": previous_results,
                        "workflow_stage": agent_name
                    }
                    
                    # Execute agent analysis
                    agent_result = await self.agent_instances[agent_name].analyze(
                        document_text=document_text,
                        user_query=user_query,
                        context=agent_context
                    )
                    
                    analysis_results["agent_analyses"][agent_name] = agent_result
                    previous_results[agent_name] = agent_result
                    
                    logger.info(f"Completed {agent_name} analysis")
                    
                except Exception as e:
                    logger.error(f"Error in {agent_name} analysis: {e}")
                    analysis_results["agent_analyses"][agent_name] = {
                        "error": f"Analysis failed: {str(e)}"
                    }
        
        # Consolidate insights from all agents
        analysis_results["consolidated_insights"] = await self._consolidate_insights(
            analysis_results["agent_analyses"]
        )
        
        # Perform final quality assessment
        if "quality_reviewer" in analysis_results["agent_analyses"]:
            analysis_results["quality_assessment"] = analysis_results["agent_analyses"]["quality_reviewer"]
        
        # Generate final executive summary
        analysis_results["final_summary"] = await self._generate_final_summary(
            analysis_results["agent_analyses"],
            user_query
        )
        
        logger.info("Multi-agent analysis completed")
        return analysis_results
    
    async def _consolidate_insights(self, agent_analyses: Dict[str, Dict]) -> Dict[str, Any]:
        """Consolidate insights from multiple agents into unified view"""
        
        consolidated = {
            "key_legal_issues": [],
            "compliance_requirements": [],
            "practical_implications": [],
            "risk_factors": [],
            "recommendations": [],
            "confidence_metrics": {}
        }
        
        # Extract and combine insights from each agent
        for agent_name, analysis in agent_analyses.items():
            if "error" in analysis:
                continue
                
            # Consolidate legal issues
            if "legal_issues" in analysis:
                consolidated["key_legal_issues"].extend(analysis["legal_issues"])
            
            # Consolidate compliance requirements
            if "compliance_implications" in analysis:
                compliance = analysis["compliance_implications"]
                if isinstance(compliance, dict):
                    for key, value in compliance.items():
                        if isinstance(value, list):
                            consolidated["compliance_requirements"].extend(value)
            
            # Consolidate practical implications
            if "practical_implications" in analysis:
                impl = analysis["practical_implications"]
                if isinstance(impl, dict):
                    for key, value in impl.items():
                        if isinstance(value, str):
                            consolidated["practical_implications"].append({
                                "category": key,
                                "implication": value,
                                "source_agent": agent_name
                            })
            
            # Extract confidence metrics
            if "confidence_score" in analysis:
                consolidated["confidence_metrics"][agent_name] = analysis["confidence_score"]
        
        # Remove duplicates and rank by importance
        consolidated["key_legal_issues"] = list(set(consolidated["key_legal_issues"]))
        consolidated["compliance_requirements"] = list(set(consolidated["compliance_requirements"]))
        
        return consolidated
    
    async def _generate_final_summary(
        self, 
        agent_analyses: Dict[str, Dict], 
        user_query: str = None
    ) -> Dict[str, Any]:
        """Generate executive summary combining all agent perspectives"""
        
        summary = {
            "executive_overview": "",
            "key_takeaways": [],
            "critical_actions": [],
            "strategic_implications": [],
            "next_steps": []
        }
        
        # Build executive overview
        overview_parts = []
        
        if "legal_analyst" in agent_analyses:
            legal_analysis = agent_analyses["legal_analyst"]
            if "case_summary" in legal_analysis:
                overview_parts.append(f"Legal Analysis: {legal_analysis['case_summary']}")
        
        if "cs_expert" in agent_analyses:
            cs_analysis = agent_analyses["cs_expert"]
            if "executive_summary" in cs_analysis:
                overview_parts.append(f"CS Perspective: {cs_analysis['executive_summary']}")
        
        summary["executive_overview"] = " | ".join(overview_parts)
        
        # Extract key takeaways from all agents
        for agent_name, analysis in agent_analyses.items():
            if "error" in analysis:
                continue
                
            # Extract various types of takeaways
            takeaway_fields = [
                "key_takeaways", "cs_action_items", "key_principles", 
                "practical_guidance", "recommendations"
            ]
            
            for field in takeaway_fields:
                if field in analysis:
                    value = analysis[field]
                    if isinstance(value, list):
                        summary["key_takeaways"].extend([
                            f"[{agent_name.upper()}] {item}" for item in value
                        ])
                    elif isinstance(value, str):
                        summary["key_takeaways"].append(f"[{agent_name.upper()}] {value}")
        
        # Remove duplicates while preserving order
        summary["key_takeaways"] = list(dict.fromkeys(summary["key_takeaways"]))[:10]
        
        return summary
    
    async def process_custom_query(
        self,
        document_text: str,
        custom_prompt: str,
        agent_preference: str = "auto"
    ) -> Dict[str, Any]:
        """
        Process a custom user query with intelligent agent selection.
        Agent preference can be 'auto', 'legal', 'cs', or 'all'
        """
        
        logger.info(f"Processing custom query with agent preference: {agent_preference}")
        
        # Determine optimal agent(s) based on query content and preference
        selected_agents = await self._select_agents_for_query(custom_prompt, agent_preference)
        
        results = {
            "query": custom_prompt,
            "selected_agents": selected_agents,
            "responses": {},
            "consolidated_response": ""
        }
        
        # Execute selected agents
        for agent_name in selected_agents:
            if agent_name in self.agent_instances:
                try:
                    response = await self.agent_instances[agent_name].analyze(
                        document_text=document_text,
                        user_query=custom_prompt
                    )
                    results["responses"][agent_name] = response
                except Exception as e:
                    logger.error(f"Error in {agent_name} custom query: {e}")
                    results["responses"][agent_name] = {"error": str(e)}
        
        # Consolidate responses
        results["consolidated_response"] = await self._consolidate_custom_responses(
            results["responses"], 
            custom_prompt
        )
        
        return results
    
    async def _select_agents_for_query(self, query: str, preference: str) -> List[str]:
        """Intelligently select agents based on query content and user preference"""
        
        if preference == "legal":
            return ["legal_analyst"]
        elif preference == "cs":
            return ["cs_expert"]
        elif preference == "all":
            return ["legal_analyst", "cs_expert", "quality_reviewer"]
        
        # Auto selection based on query content
        query_lower = query.lower()
        selected_agents = []
        
        # Legal analyst keywords
        legal_keywords = [
            "precedent", "case law", "judgment", "legal reasoning", "statute",
            "interpretation", "court", "appeal", "constitutional"
        ]
        
        # CS expert keywords
        cs_keywords = [
            "compliance", "corporate governance", "board", "filing", "regulatory",
            "company secretary", "agm", "egm", "disclosure", "procedure"
        ]
        
        legal_score = sum(1 for keyword in legal_keywords if keyword in query_lower)
        cs_score = sum(1 for keyword in cs_keywords if keyword in query_lower)
        
        # Select agents based on scores
        if legal_score > cs_score:
            selected_agents = ["legal_analyst", "quality_reviewer"]
        elif cs_score > legal_score:
            selected_agents = ["cs_expert", "quality_reviewer"]
        else:
            # Both relevant or unclear - use comprehensive approach
            selected_agents = ["cs_expert", "legal_analyst", "quality_reviewer"]
        
        return selected_agents
    
    async def _consolidate_custom_responses(
        self, 
        responses: Dict[str, Dict], 
        original_query: str
    ) -> str:
        """Consolidate responses from multiple agents for custom queries"""
        
        consolidated_parts = []
        
        for agent_name, response in responses.items():
            if "error" in response:
                continue
            
            # Extract relevant response content based on agent type
            if agent_name == "legal_analyst":
                if "court_reasoning" in response:
                    consolidated_parts.append(f"Legal Analysis: {response['court_reasoning']}")
            
            elif agent_name == "cs_expert":
                if "executive_summary" in response:
                    consolidated_parts.append(f"CS Perspective: {response['executive_summary']}")
                if "cs_action_items" in response:
                    actions = response["cs_action_items"]
                    if actions:
                        consolidated_parts.append(f"Action Items: {'; '.join(actions[:3])}")
            
            elif agent_name == "quality_reviewer":
                if "recommendations" in response:
                    recs = response.get("recommendations", {})
                    if isinstance(recs, dict) and "improvements_needed" in recs:
                        improvements = recs["improvements_needed"]
                        if improvements:
                            consolidated_parts.append(f"Quality Notes: {'; '.join(improvements[:2])}")
        
        if consolidated_parts:
            return " | ".join(consolidated_parts)
        else:
            return "Unable to generate consolidated response from available analyses."
    
    def get_orchestrator_status(self) -> Dict[str, Any]:
        """Get status and capabilities of the orchestrator"""
        
        return {
            "available_agents": list(self.agent_instances.keys()),
            "workflow_types": list(self.analysis_workflows.keys()),
            "agent_status": {
                name: agent.get_agent_info() 
                for name, agent in self.agent_instances.items()
            },
            "capabilities": [
                "Multi-agent legal analysis",
                "Custom query processing", 
                "Quality assurance validation",
                "CS-specific insights",
                "Comprehensive legal reasoning"
            ]
        }