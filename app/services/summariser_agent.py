from typing import Dict, Any, List, Optional
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import PromptTemplate
from langchain.schema import HumanMessage
import json
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

class SummariserAgent:
    """LangChain + Gemini powered summarization agent for legal documents"""
    
    def __init__(self):
        self.model = None
        self._initialize_model()
    
    def _initialize_model(self):
        """Initialize Gemini model if API key is available"""
        if settings.google_api_key:
            try:
                self.model = ChatGoogleGenerativeAI(
                    model=settings.llm_model,
                    google_api_key=settings.google_api_key,
                    temperature=0  # Deterministic output
                )
                logger.info("Gemini model initialized successfully")
            except Exception as e:
                logger.warning(f"Failed to initialize Gemini model: {e}")
    
    def summarise_document(self, raw_text: str, style: str = "cs_student") -> Optional[Dict[str, Any]]:
        """
        Generate structured summary of legal document.
        Returns: parsed JSON summary or None if failed
        """
        if not self.model:
            logger.error("Model not available for summarization")
            return None
        
        try:
            # Create prompt based on style
            prompt = self._create_prompt(style)
            
            # Generate summary
            messages = [HumanMessage(content=prompt.format(text=raw_text))]
            response = self.model.invoke(messages)
            
            # Parse structured output
            summary_data = self._parse_response(response.content)
            
            if summary_data:
                logger.info("Summary generated successfully")
                return summary_data
            else:
                logger.error("Failed to parse summary response")
                return None
                
        except Exception as e:
            logger.error(f"Error generating summary: {e}")
            return None
    
    def _create_prompt(self, style: str) -> PromptTemplate:
        """Create prompt template based on summary style"""
        
        if style == "cs_student":
            template = """
You are a legal summarization expert for Company Secretary students. Analyze the following legal document and provide a structured JSON response.

Your response must be ONLY valid JSON with the following structure:
{{
    "issues": ["List of key legal issues discussed"],
    "holding": "Court's main decision/ruling",
    "reasoning": "Brief reasoning behind the decision",
    "key_sections": ["Relevant sections of Companies Act or other laws"],
    "precedents": ["Important case citations mentioned"],
    "practical_implications": ["What this means for company secretaries"],
    "span_offsets": [
        {{"claim": "specific claim", "start_offset": 123, "end_offset": 456}}
    ]
}}

For span_offsets, identify key claims and their exact positions in the raw text.

Document:
{text}

JSON Response:"""
        else:
            # Default research style
            template = """
You are a legal research assistant. Analyze the following legal document and provide a structured JSON response.

Your response must be ONLY valid JSON with the following structure:
{{
    "issues": ["List of legal issues"],
    "holding": "Court's holding",
    "reasoning": "Legal reasoning",
    "citations": ["Case citations and legal references"],
    "span_offsets": [
        {{"claim": "specific claim", "start_offset": 123, "end_offset": 456}}
    ]
}}

Document:
{text}

JSON Response:"""
        
        return PromptTemplate(template=template, input_variables=["text"])
    
    def _parse_response(self, response_content: str) -> Optional[Dict[str, Any]]:
        """Parse and validate JSON response"""
        try:
            # Clean response content
            content = response_content.strip()
            if content.startswith("```json"):
                content = content[7:-3]
            elif content.startswith("```"):
                content = content[3:-3]
            
            # Parse JSON
            parsed = json.loads(content)
            
            # Basic validation
            required_fields = ["issues", "holding", "reasoning", "span_offsets"]
            if all(field in parsed for field in required_fields):
                return parsed
            else:
                logger.error(f"Missing required fields in response: {parsed.keys()}")
                return None
                
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            return None
        except Exception as e:
            logger.error(f"Error parsing response: {e}")
            return None

# Global summarizer instance
summariser_agent = SummariserAgent()