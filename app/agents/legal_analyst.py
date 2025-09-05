from typing import Dict, Any, List
from .base_agent import BaseAgent
import json
import re

class LegalAnalystAgent(BaseAgent):
    """
    Specialized agent for comprehensive legal analysis.
    Focuses on precedent identification, legal reasoning, and case law analysis.
    """
    
    def __init__(self):
        super().__init__(
            agent_name="Legal Analyst",
            role_description="Expert legal analyst specializing in case law analysis, precedent identification, and legal reasoning",
            temperature=0.05  # Very deterministic for legal analysis
        )
    
    def create_system_prompt(self) -> str:
        return """
You are a Senior Legal Analyst with 15+ years of experience in Indian corporate and constitutional law. 
Your expertise includes:
- Case law analysis and precedent identification
- Legal reasoning and judicial interpretation
- Corporate governance and securities law
- Constitutional law and fundamental rights
- Statutory interpretation and legislative intent

Your task is to provide comprehensive legal analysis of court judgments and legal documents.
Always provide precise citations, identify key legal principles, and explain the reasoning clearly.

When analyzing documents, focus on:
1. Legal issues and questions of law
2. Court's reasoning and judicial interpretation
3. Precedent value and binding nature
4. Practical implications for legal practice
5. Cross-references to relevant statutes and cases

Provide responses in structured JSON format for consistency.
"""
    
    async def analyze(self, document_text: str, user_query: str = None, context: Dict = None) -> Dict[str, Any]:
        """Perform comprehensive legal analysis of the document"""
        
        # Create analysis prompt
        prompt = f"""
{self.create_system_prompt()}

Please analyze the following legal document and provide a comprehensive legal analysis.

Document Text:
{document_text[:8000]}  # Truncate for API limits

{f"Specific User Query: {user_query}" if user_query else ""}

Provide your analysis in the following JSON format:
{{
    "case_summary": "Brief summary of the case",
    "legal_issues": ["List of key legal issues addressed"],
    "court_reasoning": "Detailed explanation of the court's legal reasoning",
    "precedent_analysis": {{
        "precedent_value": "high/medium/low",
        "binding_nature": "binding/persuasive/distinguishable",
        "key_principles": ["List of legal principles established"]
    }},
    "statutory_framework": {{
        "primary_statutes": ["List of main statutes involved"],
        "sections_analyzed": ["Specific sections analyzed"],
        "interpretation_approach": "How the court interpreted the law"
    }},
    "citations_analysis": {{
        "cases_cited": ["Important cases cited by the court"],
        "authorities_relied": ["Legal authorities and their significance"],
        "distinguishing_factors": ["How this case differs from precedents"]
    }},
    "practical_implications": {{
        "for_legal_practice": "Impact on legal practice",
        "for_corporate_governance": "Impact on corporate governance",
        "for_compliance": "Compliance implications"
    }},
    "confidence_score": 0.95,
    "analysis_complexity": "high/medium/low"
}}
"""
        
        response = await self.generate_response(prompt, context)
        if not response:
            return {"error": "Failed to generate legal analysis"}
        
        # Validate and parse JSON response
        parsed_response = await self.validate_json_response(response)
        if not parsed_response:
            return {"error": "Failed to parse legal analysis response"}
        
        # Add agent metadata
        parsed_response["analyzed_by"] = self.agent_name
        parsed_response["analysis_timestamp"] = str(__import__('datetime').datetime.now())
        
        return parsed_response
    
    async def identify_precedents(self, document_text: str) -> List[Dict[str, str]]:
        """Identify and analyze precedent cases mentioned in the document"""
        
        prompt = f"""
As a Legal Analyst, identify all precedent cases mentioned in this document and analyze their significance.

Document: {document_text[:6000]}

Extract all case citations and provide analysis in JSON format:
{{
    "precedent_cases": [
        {{
            "case_name": "Name of the case",
            "citation": "Proper legal citation",
            "court": "Court that decided the case",
            "year": "Year of decision",
            "significance": "Why this case is cited",
            "principle_established": "Key legal principle from this case"
        }}
    ]
}}
"""
        
        response = await self.generate_response(prompt)
        if response:
            parsed = await self.validate_json_response(response)
            if parsed and "precedent_cases" in parsed:
                return parsed["precedent_cases"]
        
        return []
    
    async def analyze_statutory_interpretation(self, document_text: str) -> Dict[str, Any]:
        """Analyze how statutes are interpreted in the document"""
        
        prompt = f"""
Analyze the statutory interpretation approach used in this legal document.

Document: {document_text[:6000]}

Provide analysis in JSON format:
{{
    "interpretation_method": "literal/purposive/contextual/historical",
    "statutes_interpreted": ["List of statutes"],
    "sections_analyzed": ["Specific sections"],
    "judicial_approach": "Description of court's interpretive approach",
    "legislative_intent": "Court's view on legislative intent",
    "implications": "Implications for future cases"
}}
"""
        
        response = await self.generate_response(prompt)
        if response:
            return await self.validate_json_response(response) or {}
        return {}
    
    def extract_legal_entities(self, text: str) -> Dict[str, List[str]]:
        """Extract legal entities like case names, statutes, sections"""
        
        entities = {
            "cases": [],
            "statutes": [],
            "sections": [],
            "courts": []
        }
        
        # Case name patterns
        case_patterns = [
            r'([A-Z][a-zA-Z\s&]+)\s+v\.?\s+([A-Z][a-zA-Z\s&]+)',
            r'([A-Z][a-zA-Z\s]+)\s+vs\.?\s+([A-Z][a-zA-Z\s]+)',
        ]
        
        for pattern in case_patterns:
            matches = re.findall(pattern, text)
            entities["cases"].extend([f"{m[0]} v. {m[1]}" for m in matches])
        
        # Statute patterns
        statute_patterns = [
            r'(Companies Act,?\s+\d{4})',
            r'(Securities and Exchange Board of India Act,?\s+\d{4})',
            r'(Insolvency and Bankruptcy Code,?\s+\d{4})',
            r'(Indian Contract Act,?\s+\d{4})',
        ]
        
        for pattern in statute_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            entities["statutes"].extend(matches)
        
        # Section patterns
        section_patterns = [
            r'Section\s+(\d+[A-Z]?)',
            r'Sec\.?\s+(\d+[A-Z]?)',
            r'§\s*(\d+[A-Z]?)'
        ]
        
        for pattern in section_patterns:
            matches = re.findall(pattern, text)
            entities["sections"].extend(matches)
        
        # Remove duplicates
        for key in entities:
            entities[key] = list(set(entities[key]))
        
        return entities