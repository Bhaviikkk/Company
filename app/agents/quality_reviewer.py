from typing import Dict, Any, List, Tuple
from .base_agent import BaseAgent
import json
import re

class QualityReviewerAgent(BaseAgent):
    """
    Specialized agent for quality assurance and validation of legal analysis.
    Ensures accuracy, completeness, and reliability of generated summaries.
    """
    
    def __init__(self):
        super().__init__(
            agent_name="Quality Reviewer",
            role_description="Quality assurance expert specializing in legal analysis validation and accuracy verification",
            temperature=0.0  # Maximum determinism for quality checks
        )
        
        # Quality metrics and thresholds
        self.quality_thresholds = {
            "citation_accuracy": 0.95,
            "factual_consistency": 0.95,
            "completeness_score": 0.90,
            "logical_coherence": 0.90,
            "grounding_coverage": 0.95
        }
    
    def create_system_prompt(self) -> str:
        return """
You are a Senior Quality Assurance Specialist with expertise in legal document analysis validation.
Your role is to rigorously review and validate legal analyses for:

1. ACCURACY: Verify factual correctness and proper citations
2. COMPLETENESS: Ensure all important aspects are covered
3. CONSISTENCY: Check for logical consistency and coherence
4. GROUNDING: Verify all claims are supported by the source document
5. COMPLIANCE: Ensure analysis meets professional standards

Your review must be thorough, objective, and precise. Identify any errors, inconsistencies, 
or areas needing improvement. Rate each aspect on a scale of 0-1.

Quality Standards:
- All citations must be accurate and verifiable
- Claims must be directly supported by document text
- Analysis must be logically consistent
- No contradictory statements
- Professional tone and terminology
- Complete coverage of key legal issues
"""
    
    async def analyze(self, document_text: str, user_query: str = None, context: Dict = None) -> Dict[str, Any]:
        """Perform comprehensive quality review of legal analysis"""
        
        # This would typically review an existing analysis
        # For now, we'll focus on document quality assessment
        
        prompt = f"""
{self.create_system_prompt()}

Perform a comprehensive quality assessment of this legal document for analysis purposes.

Document Text:
{document_text[:8000]}

Assess the document's suitability for legal analysis and provide quality metrics:

{{
    "document_quality": {{
        "readability_score": 0.95,
        "completeness": "complete/partial/fragmented",
        "text_clarity": "excellent/good/poor",
        "citation_presence": "extensive/moderate/minimal/none",
        "structural_integrity": "excellent/good/poor"
    }},
    "content_analysis": {{
        "legal_issues_clarity": "clear/moderate/unclear",
        "factual_consistency": 0.95,
        "logical_flow": "excellent/good/poor",
        "key_information_present": true/false
    }},
    "analysis_challenges": {{
        "potential_difficulties": ["List of challenges"],
        "missing_information": ["What information is missing"],
        "ambiguous_sections": ["Sections that are ambiguous"]
    }},
    "recommendations": {{
        "preprocessing_needed": ["Any preprocessing steps"],
        "focus_areas": ["Key areas to focus analysis on"],
        "caution_areas": ["Areas requiring extra caution"]
    }},
    "overall_quality_score": 0.95,
    "suitable_for_analysis": true/false
}}
"""
        
        response = await self.generate_response(prompt, context)
        if not response:
            return {"error": "Failed to generate quality assessment"}
        
        parsed_response = await self.validate_json_response(response)
        if not parsed_response:
            return {"error": "Failed to parse quality assessment"}
        
        # Add reviewer metadata
        parsed_response["reviewed_by"] = self.agent_name
        parsed_response["review_timestamp"] = str(__import__('datetime').datetime.now())
        
        return parsed_response
    
    async def review_legal_analysis(self, analysis: Dict[str, Any], source_document: str) -> Dict[str, Any]:
        """Review and validate a completed legal analysis"""
        
        prompt = f"""
Review this legal analysis for accuracy, completeness, and quality.

Source Document: {source_document[:4000]}

Analysis to Review: {json.dumps(analysis, indent=2)[:4000]}

Provide comprehensive quality review:
{{
    "accuracy_assessment": {{
        "citation_accuracy": 0.95,
        "factual_correctness": 0.95,
        "legal_reasoning_validity": 0.95,
        "errors_identified": ["List any errors found"]
    }},
    "completeness_assessment": {{
        "key_issues_covered": 0.95,
        "missing_elements": ["What's missing"],
        "depth_of_analysis": "excellent/good/superficial",
        "coverage_score": 0.95
    }},
    "consistency_assessment": {{
        "logical_coherence": 0.95,
        "internal_consistency": 0.95,
        "contradictions_found": ["Any contradictions"],
        "coherence_score": 0.95
    }},
    "grounding_assessment": {{
        "claims_supported": 0.95,
        "unsupported_claims": ["Claims without support"],
        "evidence_quality": "strong/moderate/weak",
        "grounding_score": 0.95
    }},
    "professional_standards": {{
        "terminology_accuracy": 0.95,
        "tone_appropriateness": "professional/acceptable/inappropriate",
        "presentation_quality": "excellent/good/poor"
    }},
    "recommendations": {{
        "improvements_needed": ["List of improvements"],
        "critical_issues": ["Critical issues to address"],
        "approval_status": "approved/needs_revision/rejected"
    }},
    "overall_quality_score": 0.95,
    "certification": "quality_assured/conditional_approval/rejected"
}}
"""
        
        response = await self.generate_response(prompt)
        if not response:
            return {"error": "Failed to generate quality review"}
        
        return await self.validate_json_response(response) or {}
    
    async def validate_citations(self, analysis: Dict[str, Any], source_document: str) -> Dict[str, Any]:
        """Validate all citations and references in the analysis"""
        
        # Extract citations from analysis
        citations = self._extract_citations(analysis)
        
        validation_results = {
            "total_citations": len(citations),
            "validated_citations": [],
            "invalid_citations": [],
            "citation_accuracy_score": 0.0
        }
        
        for citation in citations:
            is_valid = await self._validate_single_citation(citation, source_document)
            if is_valid:
                validation_results["validated_citations"].append(citation)
            else:
                validation_results["invalid_citations"].append(citation)
        
        if citations:
            accuracy = len(validation_results["validated_citations"]) / len(citations)
            validation_results["citation_accuracy_score"] = accuracy
        
        return validation_results
    
    def _extract_citations(self, analysis: Dict[str, Any]) -> List[str]:
        """Extract all citations from the analysis"""
        citations = []
        
        # Recursively search for citations in the analysis
        def search_citations(obj):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if "citation" in key.lower() or "case" in key.lower():
                        if isinstance(value, list):
                            citations.extend(value)
                        elif isinstance(value, str):
                            citations.append(value)
                    else:
                        search_citations(value)
            elif isinstance(obj, list):
                for item in obj:
                    search_citations(item)
            elif isinstance(obj, str):
                # Look for citation patterns in text
                citation_patterns = [
                    r'[A-Z][a-zA-Z\s]+v\.?\s+[A-Z][a-zA-Z\s]+',
                    r'\(\d{4}\)\s+\d+\s+[A-Z]+',
                    r'AIR\s+\d{4}\s+[A-Z]+\s+\d+'
                ]
                for pattern in citation_patterns:
                    matches = re.findall(pattern, obj)
                    citations.extend(matches)
        
        search_citations(analysis)
        return list(set(citations))  # Remove duplicates
    
    async def _validate_single_citation(self, citation: str, source_document: str) -> bool:
        """Validate if a citation appears in the source document"""
        
        # Simple validation: check if citation or parts of it appear in source
        citation_clean = re.sub(r'[^\w\s]', ' ', citation.lower())
        source_clean = source_document.lower()
        
        # Check for exact match or significant word overlap
        citation_words = citation_clean.split()
        if len(citation_words) >= 2:
            significant_words = [w for w in citation_words if len(w) > 3]
            matches = sum(1 for word in significant_words if word in source_clean)
            return matches >= len(significant_words) * 0.6  # 60% word match threshold
        
        return citation.lower() in source_clean
    
    async def calculate_overall_quality_score(self, individual_scores: Dict[str, float]) -> Tuple[float, str]:
        """Calculate weighted overall quality score"""
        
        # Define weights for different quality aspects
        weights = {
            "citation_accuracy": 0.25,
            "factual_consistency": 0.25, 
            "completeness_score": 0.20,
            "logical_coherence": 0.15,
            "grounding_coverage": 0.15
        }
        
        weighted_score = 0.0
        total_weight = 0.0
        
        for aspect, score in individual_scores.items():
            if aspect in weights:
                weighted_score += score * weights[aspect]
                total_weight += weights[aspect]
        
        if total_weight > 0:
            final_score = weighted_score / total_weight
        else:
            final_score = 0.0
        
        # Determine certification level
        if final_score >= 0.95:
            certification = "premium_quality"
        elif final_score >= 0.85:
            certification = "high_quality"
        elif final_score >= 0.75:
            certification = "acceptable_quality"
        else:
            certification = "needs_improvement"
        
        return final_score, certification