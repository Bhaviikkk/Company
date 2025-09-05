from typing import Dict, Any, List
from .base_agent import BaseAgent
import json

class CompanySecretaryExpertAgent(BaseAgent):
    """
    Specialized agent focused on Company Secretary practice areas.
    Provides CS-specific insights, compliance guidance, and practical implications.
    """
    
    def __init__(self):
        super().__init__(
            agent_name="CS Expert",
            role_description="Company Secretary expert with deep knowledge of corporate compliance, governance, and secretarial practice",
            temperature=0.1  # Slightly more flexibility for practical guidance
        )
        
        # CS-specific knowledge areas
        self.cs_expertise_areas = [
            "Corporate Governance",
            "Board Meetings and Procedures",
            "AGM/EGM Compliance",
            "Regulatory Filings",
            "Securities Law Compliance", 
            "SEBI Regulations",
            "Companies Act Compliance",
            "Corporate Restructuring",
            "Merger & Acquisition Procedures",
            "Insolvency Procedures",
            "Share Capital Management",
            "Corporate Social Responsibility",
            "Related Party Transactions"
        ]
    
    def create_system_prompt(self) -> str:
        return f"""
You are a Senior Company Secretary with 20+ years of experience in corporate secretarial practice.
You are an expert in:
{chr(10).join(f"- {area}" for area in self.cs_expertise_areas)}

Your role is to provide practical, actionable insights for Company Secretary professionals.
Focus on:
1. Compliance implications and requirements
2. Practical steps and procedures
3. Risk assessment and mitigation
4. Best practices for corporate governance
5. Actionable recommendations for CS practitioners

When analyzing legal documents, always consider:
- What does this mean for day-to-day CS practice?
- What compliance actions are required?
- What are the practical implications for corporate governance?
- How should companies prepare for compliance?
- What are the key takeaways for CS professionals?

Provide clear, practical guidance that CS professionals can implement immediately.
"""
    
    async def analyze(self, document_text: str, user_query: str = None, context: Dict = None) -> Dict[str, Any]:
        """Analyze document from CS professional perspective"""
        
        prompt = f"""
{self.create_system_prompt()}

Analyze the following legal document from a Company Secretary's practical perspective.

Document Text:
{document_text[:8000]}

{f"Specific CS Query: {user_query}" if user_query else ""}

Provide your CS-focused analysis in JSON format:
{{
    "executive_summary": "Key takeaways for CS professionals",
    "compliance_implications": {{
        "immediate_actions": ["Actions companies must take immediately"],
        "ongoing_compliance": ["Long-term compliance requirements"],
        "filing_requirements": ["Specific filings or disclosures required"],
        "deadlines": ["Important dates and deadlines"]
    }},
    "governance_impact": {{
        "board_considerations": ["Issues for board attention"],
        "policy_updates": ["Corporate policies that may need updating"],
        "procedure_changes": ["Procedural changes required"],
        "documentation": ["Documentation requirements"]
    }},
    "practical_guidance": {{
        "implementation_steps": ["Step-by-step implementation guide"],
        "key_checkpoints": ["Critical checkpoints for compliance"],
        "common_pitfalls": ["Common mistakes to avoid"],
        "best_practices": ["Recommended best practices"]
    }},
    "stakeholder_communication": {{
        "board_briefing_points": ["Key points for board briefing"],
        "management_updates": ["Updates for management team"],
        "investor_disclosures": ["Disclosure requirements for investors"],
        "regulatory_communications": ["Communications with regulators"]
    }},
    "risk_assessment": {{
        "compliance_risks": ["Key compliance risks identified"],
        "mitigation_strategies": ["Risk mitigation approaches"],
        "monitoring_requirements": ["Ongoing monitoring needs"]
    }},
    "industry_impact": {{
        "affected_sectors": ["Industries most affected"],
        "company_size_considerations": ["Impact based on company size"],
        "timeline_for_implementation": "Expected implementation timeline"
    }},
    "cs_action_items": ["Specific action items for CS professionals"],
    "confidence_level": "high/medium/low",
    "urgency_level": "immediate/high/medium/low"
}}
"""
        
        response = await self.generate_response(prompt, context)
        if not response:
            return {"error": "Failed to generate CS analysis"}
        
        parsed_response = await self.validate_json_response(response)
        if not parsed_response:
            return {"error": "Failed to parse CS analysis response"}
        
        # Add agent metadata
        parsed_response["analyzed_by"] = self.agent_name
        parsed_response["analysis_timestamp"] = str(__import__('datetime').datetime.now())
        parsed_response["expertise_areas_covered"] = await self._identify_relevant_areas(document_text)
        
        return parsed_response
    
    async def _identify_relevant_areas(self, document_text: str) -> List[str]:
        """Identify which CS expertise areas are relevant to this document"""
        relevant_areas = []
        text_lower = document_text.lower()
        
        area_keywords = {
            "Corporate Governance": ["corporate governance", "board", "directors", "governance"],
            "Board Meetings and Procedures": ["board meeting", "resolution", "quorum", "minutes"],
            "AGM/EGM Compliance": ["agm", "egm", "annual general meeting", "general meeting"],
            "Regulatory Filings": ["filing", "form", "register", "regulatory"],
            "Securities Law Compliance": ["securities", "sebi", "stock exchange", "listing"],
            "Companies Act Compliance": ["companies act", "company law", "corporate law"],
            "Corporate Restructuring": ["merger", "amalgamation", "demerger", "restructuring"],
            "Insolvency Procedures": ["insolvency", "bankruptcy", "winding up", "liquidation"],
            "Share Capital Management": ["share capital", "shares", "equity", "capital"]
        }
        
        for area, keywords in area_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                relevant_areas.append(area)
        
        return relevant_areas
    
    async def generate_compliance_checklist(self, document_text: str) -> List[Dict[str, Any]]:
        """Generate a practical compliance checklist based on the document"""
        
        prompt = f"""
Based on this legal document, create a detailed compliance checklist for Company Secretary professionals.

Document: {document_text[:6000]}

Provide a comprehensive checklist in JSON format:
{{
    "compliance_checklist": [
        {{
            "task": "Specific compliance task",
            "priority": "high/medium/low",
            "deadline": "Deadline if any",
            "responsible_party": "Who should handle this",
            "documentation_required": "Documents needed",
            "steps": ["Step 1", "Step 2", "etc."]
        }}
    ]
}}
"""
        
        response = await self.generate_response(prompt)
        if response:
            parsed = await self.validate_json_response(response)
            if parsed and "compliance_checklist" in parsed:
                return parsed["compliance_checklist"]
        
        return []
    
    async def assess_impact_by_company_size(self, document_text: str) -> Dict[str, Dict[str, Any]]:
        """Assess how the legal change impacts different company sizes"""
        
        prompt = f"""
Analyze how this legal development impacts companies of different sizes.

Document: {document_text[:6000]}

Provide impact analysis by company size:
{{
    "listed_companies": {{
        "impact_level": "high/medium/low",
        "key_implications": ["List of implications"],
        "specific_requirements": ["Requirements specific to listed companies"]
    }},
    "large_unlisted_companies": {{
        "impact_level": "high/medium/low", 
        "key_implications": ["List of implications"],
        "specific_requirements": ["Requirements for large unlisted companies"]
    }},
    "small_medium_companies": {{
        "impact_level": "high/medium/low",
        "key_implications": ["List of implications"], 
        "specific_requirements": ["Requirements for small/medium companies"]
    }},
    "startups": {{
        "impact_level": "high/medium/low",
        "key_implications": ["List of implications"],
        "specific_requirements": ["Requirements for startups"]
    }}
}}
"""
        
        response = await self.generate_response(prompt)
        if response:
            return await self.validate_json_response(response) or {}
        
        return {}