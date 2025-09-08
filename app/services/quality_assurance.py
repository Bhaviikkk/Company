"""
Production-grade quality assurance system enforcing 95% accuracy threshold
"""
from typing import Dict, Any, List, Tuple
import logging
from datetime import datetime
from app.db.base import SessionLocal
from app.db.models import Summary
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

class QualityAssuranceEngine:
    """Enforces quality standards for legal analysis"""
    
    def __init__(self):
        self.quality_threshold = 0.95
        self.minimum_scores = {
            "grounding_score": 0.95,
            "citation_accuracy": 0.90,
            "factual_consistency": 0.95,
            "completeness_score": 0.90
        }
    
    def calculate_overall_quality_score(self, analysis: Dict[str, Any]) -> float:
        """Calculate overall quality score from multiple metrics"""
        
        scores = []
        
        # Extract quality metrics from agent analyses
        for agent_name, agent_result in analysis.get("agent_analyses", {}).items():
            if isinstance(agent_result, dict):
                # Legal Analyst quality
                if agent_name == "legal_analyst":
                    if "confidence_score" in agent_result:
                        try:
                            score = float(agent_result["confidence_score"])
                            scores.append(score)
                        except (ValueError, TypeError):
                            pass
                
                # CS Expert quality  
                elif agent_name == "cs_expert":
                    if "confidence_level" in agent_result:
                        confidence_map = {"high": 0.95, "medium": 0.75, "low": 0.50}
                        scores.append(confidence_map.get(agent_result["confidence_level"], 0.50))
                
                # Quality Reviewer assessment
                elif agent_name == "quality_reviewer":
                    if "overall_quality_score" in agent_result:
                        try:
                            score = float(agent_result["overall_quality_score"])
                            scores.append(score)
                        except (ValueError, TypeError):
                            pass
        
        # Default scoring if no quality metrics found
        if not scores:
            # Assign default score based on content completeness
            content_score = self._assess_content_completeness(analysis)
            scores.append(content_score)
        
        # Calculate weighted average (Quality Reviewer gets 40% weight)
        if len(scores) >= 3:
            # If we have all three agents
            return (scores[0] * 0.3 + scores[1] * 0.3 + scores[2] * 0.4)
        else:
            return sum(scores) / len(scores) if scores else 0.0
    
    def _assess_content_completeness(self, analysis: Dict[str, Any]) -> float:
        """Assess content completeness as fallback quality measure"""
        
        score = 0.0
        
        # Check if key sections are present
        required_sections = [
            "consolidated_insights", 
            "final_summary",
            "agent_analyses"
        ]
        
        present_sections = sum(1 for section in required_sections 
                             if section in analysis and analysis[section])
        
        score += (present_sections / len(required_sections)) * 0.4
        
        # Check content depth
        if "agent_analyses" in analysis:
            agents_with_content = sum(
                1 for agent_result in analysis["agent_analyses"].values()
                if isinstance(agent_result, dict) and len(str(agent_result)) > 100
            )
            score += (agents_with_content / 3.0) * 0.3
        
        # Check for specific insights
        if analysis.get("consolidated_insights", {}).get("key_legal_issues"):
            score += 0.3
        
        return min(score, 1.0)
    
    def validate_quality_threshold(self, analysis: Dict[str, Any]) -> Tuple[bool, float, List[str]]:
        """
        Validate if analysis meets quality threshold
        Returns: (passes_threshold, quality_score, issues)
        """
        
        quality_score = self.calculate_overall_quality_score(analysis)
        issues = []
        
        # Check overall threshold
        passes_threshold = quality_score >= self.quality_threshold
        
        if not passes_threshold:
            issues.append(f"Overall quality score {quality_score:.2f} below threshold {self.quality_threshold}")
        
        # Check specific quality aspects
        agent_analyses = analysis.get("agent_analyses", {})
        
        # Validate Legal Analyst output
        if "legal_analyst" in agent_analyses:
            legal_analysis = agent_analyses["legal_analyst"]
            if not self._validate_legal_analysis_structure(legal_analysis):
                issues.append("Legal analysis missing required structure")
                passes_threshold = False
        
        # Validate CS Expert output
        if "cs_expert" in agent_analyses:
            cs_analysis = agent_analyses["cs_expert"]
            if not self._validate_cs_analysis_structure(cs_analysis):
                issues.append("CS analysis missing required structure")
                passes_threshold = False
        
        # Check for citation accuracy
        citation_issues = self._validate_citations(analysis)
        if citation_issues:
            issues.extend(citation_issues)
            passes_threshold = False
        
        return passes_threshold, quality_score, issues
    
    def _validate_legal_analysis_structure(self, legal_analysis: Dict) -> bool:
        """Validate legal analysis has required structure"""
        
        required_fields = [
            "case_summary",
            "legal_issues", 
            "court_reasoning",
            "precedent_analysis"
        ]
        
        return all(field in legal_analysis for field in required_fields)
    
    def _validate_cs_analysis_structure(self, cs_analysis: Dict) -> bool:
        """Validate CS analysis has required structure"""
        
        required_fields = [
            "executive_summary",
            "compliance_implications",
            "practical_guidance",
            "cs_action_items"
        ]
        
        return all(field in cs_analysis for field in required_fields)
    
    def _validate_citations(self, analysis: Dict[str, Any]) -> List[str]:
        """Validate citation quality"""
        
        issues = []
        
        # Check if citations are present in legal analysis
        legal_analysis = analysis.get("agent_analyses", {}).get("legal_analyst", {})
        
        if "citations_analysis" in legal_analysis:
            citations = legal_analysis["citations_analysis"]
            
            # Must have at least some cases cited
            if not citations.get("cases_cited"):
                issues.append("No cases cited in legal analysis")
            
            # Check for distinguishing factors (shows analysis depth)  
            if not citations.get("distinguishing_factors"):
                issues.append("Analysis lacks distinguishing factors for cited cases")
        
        return issues
    
    async def flag_for_human_review(
        self, 
        analysis: Dict[str, Any],
        document_id: str,
        issues: List[str]
    ) -> Dict[str, Any]:
        """Flag analysis for human review due to quality issues"""
        
        db = SessionLocal()
        
        try:
            # Create flagged summary entry
            flagged_summary = Summary(
                document_id=document_id,
                style="quality_review",
                model_id="multi_agent_system", 
                prompt_version="v2.0",
                summary_short="FLAGGED FOR REVIEW: Quality threshold not met",
                summary_detailed=str(analysis)[:10000],  # Truncate if too long
                span_citations=analysis.get("consolidated_insights", {}),
                quality_score="BELOW_THRESHOLD",
                human_status="pending",
                grounding_score=str(self.calculate_overall_quality_score(analysis)),
                citation_score="REVIEW_REQUIRED",
                consistency_score="REVIEW_REQUIRED"
            )
            
            db.add(flagged_summary)
            db.commit()
            db.refresh(flagged_summary)
            
            logger.warning(f"Analysis flagged for review: Document {document_id}, Issues: {issues}")
            
            return {
                "status": "flagged_for_review",
                "summary_id": str(flagged_summary.summary_id),
                "quality_issues": issues,
                "requires_human_review": True,
                "message": "Analysis quality below threshold - flagged for human review"
            }
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error flagging for review: {e}")
            return {
                "status": "error",
                "error": "Failed to flag for human review"
            }
        finally:
            db.close()
    
    def generate_quality_report(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Generate detailed quality assessment report"""
        
        quality_score = self.calculate_overall_quality_score(analysis)
        passes_threshold, _, issues = self.validate_quality_threshold(analysis)
        
        return {
            "overall_quality_score": quality_score,
            "passes_threshold": passes_threshold,
            "threshold_requirement": self.quality_threshold,
            "quality_grade": self._get_quality_grade(quality_score),
            "quality_issues": issues,
            "recommendations": self._generate_quality_recommendations(analysis, issues),
            "assessment_timestamp": datetime.now().isoformat(),
            "certification_status": "APPROVED" if passes_threshold else "REQUIRES_REVIEW"
        }
    
    def _get_quality_grade(self, score: float) -> str:
        """Convert score to letter grade"""
        if score >= 0.95:
            return "A+ (Premium Quality)"
        elif score >= 0.90:
            return "A (High Quality)" 
        elif score >= 0.85:
            return "B+ (Good Quality)"
        elif score >= 0.80:
            return "B (Acceptable Quality)"
        elif score >= 0.70:
            return "C (Below Standards)"
        else:
            return "F (Unacceptable)"
    
    def _generate_quality_recommendations(self, analysis: Dict[str, Any], issues: List[str]) -> List[str]:
        """Generate recommendations for quality improvement"""
        
        recommendations = []
        
        if "Overall quality score" in str(issues):
            recommendations.append("Improve content depth and analysis comprehensiveness")
        
        if "Legal analysis missing" in str(issues):
            recommendations.append("Ensure legal analysis includes case summary, legal issues, reasoning, and precedent analysis")
        
        if "CS analysis missing" in str(issues): 
            recommendations.append("Include executive summary, compliance implications, practical guidance, and action items")
        
        if "No cases cited" in str(issues):
            recommendations.append("Add relevant case citations and legal authorities")
        
        if not recommendations:
            recommendations.append("Analysis meets quality standards - continue current approach")
        
        return recommendations

# Global quality assurance instance
qa_engine = QualityAssuranceEngine()