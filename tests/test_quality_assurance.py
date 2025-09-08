"""
Test quality assurance system
"""
import pytest
from app.services.quality_assurance import QualityAssuranceEngine

class TestQualityAssurance:
    """Test quality assurance functionality"""
    
    def test_qa_engine_initialization(self):
        """Test QA engine initializes correctly"""
        qa_engine = QualityAssuranceEngine()
        assert qa_engine.quality_threshold == 0.95
        assert "grounding_score" in qa_engine.minimum_scores
    
    def test_quality_score_calculation(self):
        """Test quality score calculation"""
        qa_engine = QualityAssuranceEngine()
        
        # Test high quality analysis
        high_quality_analysis = {
            "agent_analyses": {
                "legal_analyst": {"confidence_score": 0.96},
                "cs_expert": {"confidence_level": "high"}, 
                "quality_reviewer": {"overall_quality_score": 0.97}
            }
        }
        
        score = qa_engine.calculate_overall_quality_score(high_quality_analysis)
        assert score >= 0.90
        
        # Test low quality analysis
        low_quality_analysis = {
            "agent_analyses": {
                "legal_analyst": {"confidence_score": 0.70},
                "cs_expert": {"confidence_level": "low"},
                "quality_reviewer": {"overall_quality_score": 0.65}
            }
        }
        
        score = qa_engine.calculate_overall_quality_score(low_quality_analysis)
        assert score < 0.80
    
    def test_quality_threshold_validation(self):
        """Test quality threshold validation"""
        qa_engine = QualityAssuranceEngine()
        
        # Test analysis that passes threshold
        good_analysis = {
            "agent_analyses": {
                "legal_analyst": {
                    "confidence_score": 0.96,
                    "case_summary": "Test summary",
                    "legal_issues": ["Issue 1"],
                    "court_reasoning": "Reasoning",
                    "precedent_analysis": {"precedent_value": "high"},
                    "citations_analysis": {
                        "cases_cited": ["Case 1"],
                        "distinguishing_factors": ["Factor 1"]
                    }
                },
                "cs_expert": {
                    "confidence_level": "high",
                    "executive_summary": "Summary",
                    "compliance_implications": {"immediate_actions": ["Action 1"]},
                    "practical_guidance": {"implementation_steps": ["Step 1"]},
                    "cs_action_items": ["Item 1"]
                },
                "quality_reviewer": {"overall_quality_score": 0.97}
            }
        }
        
        passes, score, issues = qa_engine.validate_quality_threshold(good_analysis)
        assert passes == True
        assert score >= 0.95
        assert len(issues) == 0
        
        # Test analysis that fails threshold
        poor_analysis = {
            "agent_analyses": {
                "legal_analyst": {"confidence_score": 0.60},
                "cs_expert": {"confidence_level": "low"}
            }
        }
        
        passes, score, issues = qa_engine.validate_quality_threshold(poor_analysis)
        assert passes == False
        assert len(issues) > 0
    
    def test_quality_report_generation(self):
        """Test quality report generation"""
        qa_engine = QualityAssuranceEngine()
        
        analysis = {
            "agent_analyses": {
                "legal_analyst": {"confidence_score": 0.92},
                "cs_expert": {"confidence_level": "high"}
            }
        }
        
        report = qa_engine.generate_quality_report(analysis)
        
        assert "overall_quality_score" in report
        assert "passes_threshold" in report
        assert "quality_grade" in report
        assert "certification_status" in report
        assert report["threshold_requirement"] == 0.95
    
    def test_quality_grades(self):
        """Test quality grade assignment"""
        qa_engine = QualityAssuranceEngine()
        
        # Test different score ranges
        assert "A+" in qa_engine._get_quality_grade(0.96)
        assert "A" in qa_engine._get_quality_grade(0.91)
        assert "B+" in qa_engine._get_quality_grade(0.86) 
        assert "F" in qa_engine._get_quality_grade(0.50)