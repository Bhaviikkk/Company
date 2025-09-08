from fastapi import APIRouter, Depends, HTTPException, Body, Query
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
from pydantic import BaseModel
from app.db.base import get_db
from app.services.premium_research_engine import PremiumResearchEngine
from app.agents.agent_orchestrator import AgentOrchestrator
from app.services.quality_assurance import qa_engine
from app.core.auth import get_current_user
from app.core.rate_limiting import rate_limit
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize premium services
premium_engine = PremiumResearchEngine()
agent_orchestrator = AgentOrchestrator()

class ResearchRequest(BaseModel):
    query: str
    research_mode: str = "comprehensive"
    include_recent_updates: bool = True
    max_documents: int = 10

class CustomAnalysisRequest(BaseModel):
    document_text: str
    custom_prompt: str
    agent_preference: str = "auto"  # auto, legal, cs, all

class MultiAgentAnalysisRequest(BaseModel):
    document_text: str
    user_query: Optional[str] = None
    workflow_type: str = "comprehensive"

class PremiumAnalysisResponse(BaseModel):
    status: str
    workflow_type: str
    data: Dict[str, Any]

@router.post("/premium-research")
async def premium_research_request(
    request: ResearchRequest,
    db: Session = Depends(get_db)
):
    """
    Ultimate premium research endpoint for Company Secretary professionals.
    Provides multi-agent AI analysis with comprehensive legal insights.
    """
    try:
        logger.info(f"Premium research request: {request.query}")
        
        # Validate research mode
        valid_modes = ["comprehensive", "cs_focused", "legal_precedent", "compliance_advisory"]
        if request.research_mode not in valid_modes:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid research mode. Must be one of: {valid_modes}"
            )
        
        # Process the premium research request
        result = await premium_engine.process_research_request(
            user_query=request.query,
            research_mode=request.research_mode,
            include_recent_updates=request.include_recent_updates,
            max_documents=request.max_documents
        )
        
        return {
            "status": "success",
            "research_type": "premium_multi_agent_analysis",
            "data": result
        }
        
    except Exception as e:
        logger.error(f"Premium research error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Premium research failed: {str(e)}"
        )

@router.post("/custom-analysis")
async def custom_document_analysis(
    request: CustomAnalysisRequest,
    db: Session = Depends(get_db)
):
    """
    Custom document analysis with user-defined prompts.
    Uses intelligent agent selection based on query content.
    """
    try:
        logger.info("Custom analysis request received")
        
        # Process custom analysis with agent orchestrator
        result = await agent_orchestrator.process_custom_query(
            document_text=request.document_text,
            custom_prompt=request.custom_prompt,
            agent_preference=request.agent_preference
        )
        
        return {
            "status": "success",
            "analysis_type": "custom_multi_agent",
            "data": result
        }
        
    except Exception as e:
        logger.error(f"Custom analysis error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Custom analysis failed: {str(e)}"
        )

@router.post("/multi-agent-analysis", response_model=PremiumAnalysisResponse)
@rate_limit("20/hour")  
async def multi_agent_document_analysis(
    request: MultiAgentAnalysisRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Multi-agent analysis of a specific document.
    Combines Legal Analyst, CS Expert, and Quality Reviewer perspectives.
    """
    try:
        logger.info(f"Multi-agent analysis request with workflow: {request.workflow_type}")
        
        # Perform multi-agent analysis
        result = await agent_orchestrator.analyze_document(
            document_text=request.document_text,
            user_query=request.user_query,
            workflow_type=request.workflow_type
        )
        
        # QUALITY ASSURANCE CHECK - CRITICAL FOR PRODUCTION
        passes_qa, quality_score, qa_issues = qa_engine.validate_quality_threshold(result)
        
        if not passes_qa:
            logger.warning(f"Analysis failed quality threshold: Score {quality_score:.2f}, Issues: {qa_issues}")
            
            # Flag for human review
            flagged_result = await qa_engine.flag_for_human_review(
                result, 
                "multi_agent_analysis", 
                qa_issues
            )
            
            return {
                "status": "quality_review_required",
                "workflow_type": request.workflow_type,
                "quality_score": quality_score,
                "quality_issues": qa_issues,
                "data": flagged_result
            }
        
        # Add quality report to successful analysis
        quality_report = qa_engine.generate_quality_report(result)
        result["quality_assessment"] = quality_report
        
        return PremiumAnalysisResponse(
            status="success",
            workflow_type=request.workflow_type,
            data=result
        )
        
    except Exception as e:
        logger.error(f"Multi-agent analysis error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Multi-agent analysis failed: {str(e)}"
        )

@router.get("/agent-capabilities")
async def get_agent_capabilities():
    """Get information about available AI agents and their capabilities"""
    try:
        capabilities = agent_orchestrator.get_orchestrator_status()
        
        return {
            "status": "success",
            "agent_system": "multi_agent_legal_ai",
            "data": capabilities
        }
        
    except Exception as e:
        logger.error(f"Error getting agent capabilities: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get agent capabilities: {str(e)}"
        )

@router.post("/bulk-analysis")
async def bulk_document_analysis(
    document_texts: list[str] = Body(...),
    research_mode: str = Body("cs_focused"),
    consolidate_results: bool = Body(True),
    db: Session = Depends(get_db)
):
    """
    Bulk analysis of multiple documents with consolidated insights.
    Ideal for comprehensive research across multiple cases.
    """
    try:
        if len(document_texts) > 20:
            raise HTTPException(
                status_code=400,
                detail="Maximum 20 documents allowed for bulk analysis"
            )
        
        logger.info(f"Bulk analysis request for {len(document_texts)} documents")
        
        # Process each document
        analyses = []
        for i, doc_text in enumerate(document_texts):
            try:
                result = await agent_orchestrator.analyze_document(
                    document_text=doc_text,
                    workflow_type=research_mode,
                    context={"bulk_analysis_index": i}
                )
                analyses.append(result)
            except Exception as e:
                logger.error(f"Error analyzing document {i}: {e}")
                analyses.append({"error": str(e), "document_index": i})
        
        # Consolidate results if requested
        consolidated = None
        if consolidate_results:
            consolidated = await _consolidate_bulk_analyses(analyses)
        
        return {
            "status": "success",
            "analysis_type": "bulk_multi_agent",
            "documents_processed": len(document_texts),
            "individual_analyses": analyses,
            "consolidated_insights": consolidated
        }
        
    except Exception as e:
        logger.error(f"Bulk analysis error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Bulk analysis failed: {str(e)}"
        )

@router.get("/research-modes")
async def get_available_research_modes():
    """Get available research modes and their descriptions"""
    
    modes = {
        "comprehensive": {
            "description": "Maximum depth analysis using all available agents",
            "agents": ["Legal Analyst", "CS Expert", "Quality Reviewer"],
            "best_for": "Complex legal research requiring multiple perspectives",
            "quality_threshold": 0.95
        },
        "cs_focused": {
            "description": "Company Secretary focused analysis with practical guidance",
            "agents": ["CS Expert", "Legal Analyst", "Quality Reviewer"],
            "best_for": "Compliance guidance and corporate governance matters",
            "quality_threshold": 0.90
        },
        "legal_precedent": {
            "description": "Legal precedent and case law analysis",
            "agents": ["Legal Analyst", "Quality Reviewer"],
            "best_for": "Precedent research and legal reasoning analysis",
            "quality_threshold": 0.90
        },
        "compliance_advisory": {
            "description": "Practical compliance advisory with actionable guidance",
            "agents": ["CS Expert", "Quality Reviewer"],
            "best_for": "Immediate compliance needs and practical implementation",
            "quality_threshold": 0.85
        }
    }
    
    return {
        "status": "success",
        "available_modes": modes,
        "default_mode": "comprehensive"
    }

async def _consolidate_bulk_analyses(analyses: list) -> Dict[str, Any]:
    """Consolidate insights from bulk document analyses"""
    
    consolidated = {
        "common_legal_themes": [],
        "frequent_compliance_issues": [],
        "cross_document_patterns": [],
        "overall_quality_metrics": {},
        "key_recommendations": []
    }
    
    # Extract themes across all analyses
    all_themes = []
    all_quality_scores = []
    all_recommendations = []
    
    for analysis in analyses:
        if "error" in analysis:
            continue
            
        # Extract consolidated insights
        if "consolidated_insights" in analysis:
            insights = analysis["consolidated_insights"]
            if "key_legal_issues" in insights:
                all_themes.extend(insights["key_legal_issues"])
        
        # Extract quality scores
        if "quality_assessment" in analysis:
            quality = analysis["quality_assessment"]
            if "overall_quality_score" in quality:
                all_quality_scores.append(quality["overall_quality_score"])
        
        # Extract recommendations
        if "final_summary" in analysis:
            summary = analysis["final_summary"]
            if "key_takeaways" in summary:
                all_recommendations.extend(summary["key_takeaways"])
    
    # Find common themes
    from collections import Counter
    
    theme_counter = Counter(all_themes)
    consolidated["common_legal_themes"] = [
        {"theme": theme, "frequency": count}
        for theme, count in theme_counter.most_common(10)
    ]
    
    # Calculate overall quality metrics
    if all_quality_scores:
        consolidated["overall_quality_metrics"] = {
            "average_quality": sum(all_quality_scores) / len(all_quality_scores),
            "minimum_quality": min(all_quality_scores),
            "maximum_quality": max(all_quality_scores),
            "documents_analyzed": len([a for a in analyses if "error" not in a])
        }
    
    # Top recommendations
    rec_counter = Counter(all_recommendations)
    consolidated["key_recommendations"] = [
        rec for rec, count in rec_counter.most_common(8)
    ]
    
    return consolidated