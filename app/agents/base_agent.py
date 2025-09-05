from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import PromptTemplate
from langchain.schema import HumanMessage
import json
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

class BaseAgent(ABC):
    """
    Base class for specialized AI agents in the legal research system.
    Each agent has a specific role and expertise area.
    """
    
    def __init__(self, agent_name: str, role_description: str, temperature: float = 0.1):
        self.agent_name = agent_name
        self.role_description = role_description
        self.temperature = temperature
        self.model = None
        self.conversation_history = []
        self._initialize_model()
    
    def _initialize_model(self):
        """Initialize the LLM model for this agent"""
        if settings.google_api_key:
            try:
                self.model = ChatGoogleGenerativeAI(
                    model=settings.llm_model,
                    google_api_key=settings.google_api_key,
                    temperature=self.temperature
                )
                logger.info(f"Initialized model for {self.agent_name}")
            except Exception as e:
                logger.error(f"Failed to initialize model for {self.agent_name}: {e}")
    
    def add_to_history(self, role: str, content: str):
        """Add interaction to conversation history"""
        self.conversation_history.append({
            "role": role,
            "content": content,
            "timestamp": str(__import__('datetime').datetime.now())
        })
    
    @abstractmethod
    def create_system_prompt(self) -> str:
        """Create the system prompt that defines the agent's role and capabilities"""
        pass
    
    @abstractmethod
    async def analyze(self, document_text: str, user_query: str = None, context: Dict = None) -> Dict[str, Any]:
        """Analyze document based on the agent's specialty"""
        pass
    
    async def generate_response(self, prompt: str, context: Dict = None) -> Optional[str]:
        """Generate response using the LLM"""
        if not self.model:
            logger.error(f"No model available for {self.agent_name}")
            return None
        
        try:
            # Add context to prompt if provided
            if context:
                prompt = f"Context: {json.dumps(context, indent=2)}\n\n{prompt}"
            
            messages = [HumanMessage(content=prompt)]
            response = await self.model.ainvoke(messages)
            
            # Add to conversation history
            self.add_to_history("user", prompt)
            self.add_to_history("assistant", response.content)
            
            return response.content
            
        except Exception as e:
            logger.error(f"Error generating response for {self.agent_name}: {e}")
            return None
    
    async def validate_json_response(self, response: str) -> Optional[Dict[str, Any]]:
        """Validate and parse JSON response"""
        try:
            # Clean the response
            content = response.strip()
            if content.startswith("```json"):
                content = content[7:-3]
            elif content.startswith("```"):
                content = content[3:-3]
            
            # Parse JSON
            parsed = json.loads(content)
            return parsed
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error for {self.agent_name}: {e}")
            return None
        except Exception as e:
            logger.error(f"Validation error for {self.agent_name}: {e}")
            return None
    
    def get_agent_info(self) -> Dict[str, Any]:
        """Get information about this agent"""
        return {
            "name": self.agent_name,
            "role": self.role_description,
            "temperature": self.temperature,
            "conversation_length": len(self.conversation_history)
        }