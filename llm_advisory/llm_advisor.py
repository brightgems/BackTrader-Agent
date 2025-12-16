from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Literal

# Import unified LLM service adapter
try:
    from llm_advisory.services.llm_service_adapter import get_llm_adapter
    LLM_SERVICE_AVAILABLE = True
except ImportError as e:
    LLM_SERVICE_AVAILABLE = False
    get_llm_adapter = None
    print(f"LLM service adapter import failed: {e}")
except Exception as e:
    LLM_SERVICE_AVAILABLE = False
    get_llm_adapter = None
    print(f"LLM service setup error: {e}")


class LLMMessage(BaseModel):
    """LLM message model for advisory system"""
    role: str = Field(description="Message role: system, user, assistant")
    content: str = Field(description="Message content")
    timestamp: Optional[datetime] = None


class LLMAdvisorDataArtefact(BaseModel):
    """Data artefact for LLM advisor

    The artefact can be a mapping, list, or simple string/value depending on
    the data provided by different advisors (strategy description, tables,
    indicator lists, etc.). Use a flexible `Any` type to avoid validation
    errors when passing simple strings or complex structures.
    """
    description: str = Field(description="Description of the data artefact")
    artefact: Any = Field(description="The actual data artefact")
    output_mode: str = Field(default="text", description="Output format for the artefact")


class LLMAdvisorDataArtefactOutputMode:
    """Output modes for data artefacts"""
    TEXT = "text"
    MARKDOWN_TABLE = "markdown_table"
    JSON = "json"


class LLMAdvisorSignal(BaseModel):
    """Base signal model for LLM advisor"""
    signal: Literal["bullish", "bearish", "neutral", "none"] = Field(
        default="none",
        description="Trading signal from advisor"
    )
    confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Confidence level from 0.0 to 1.0"
    )
    reasoning: str = Field(
        default="",
        description="Reasoning behind the signal"
    )


class LLMAdvisorAdvice(BaseModel):
    """Base advice model for advisory advisor"""
    signal: Literal["buy", "sell", "close", "none"] = Field(
        default="none",
        description="Final trading advice"
    )
    confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Confidence level from 0.0 to 1.0"
    )
    reasoning: str = Field(
        default="",
        description="Reasoning behind the advice"
    )


class LLMAdvisorState(BaseModel):
    """LLM advisor state model"""
    messages: List[LLMMessage] = Field(default_factory=list)
    data: List[LLMAdvisorDataArtefact] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    advisor_name: str = Field(default="", description="Name of the advisor")


class LLMAdvisorUpdateStateData(BaseModel):
    """Data structure for updating advisor state"""
    messages: List[LLMMessage] = Field(default_factory=list)
    data: List[LLMAdvisorDataArtefact] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AdvisorMessagesInput(BaseModel):
    """Input messages for advisor"""
    advisor_prompt: str = Field(default="", description="Prompt for the advisor")
    advisor_data: str = Field(default="", description="Data for the advisor")
    system_message: str = Field(default="", description="System instructions")


class LLMAdvisor(ABC):
    """Abstract base class for LLM Advisors"""
    
    # Default signal model type
    signal_model_type: Type[BaseModel] = LLMAdvisorSignal
    
    # Advisor configuration
    advisor_name: str = "BaseAdvisor"
    advisor_instructions: str = ""
    advisor_prompt: str = ""
    
    # LLM provider configuration
    llm_provider: str = "ollama"  # Default to ollama for local development
    llm_model: str = "qwen3-vl"  # Default model
    
    def __init__(self, provider: str = None, model: str = None):
        self.advisor_messages_input = AdvisorMessagesInput()
        
        if provider:
            self.llm_provider = provider
        if model:
            self.llm_model = model
        
    def update_state(self, state: LLMAdvisorUpdateStateData) -> LLMAdvisorUpdateStateData:
        """Update the advisor state with new data
        
        Args:
            state: Current state data
            
        Returns:
            Updated state data
        """
        return self._update_state(state)
    
    def _update_state(self, state: LLMAdvisorUpdateStateData) -> LLMAdvisorUpdateStateData:
        """Default implementation for state update using LLM service"""
        
        # Build the prompt for the advisor
        system_prompt = self.advisor_instructions or "You are a trading advisor."
        user_prompt = f"{self.advisor_prompt}\n\nData:\n{self.advisor_messages_input.advisor_data}"
        
        if LLM_SERVICE_AVAILABLE and get_llm_adapter:
            try:
                # Use unified LLM service adapter
                llm_adapter = get_llm_adapter()
                response_content = llm_adapter.generate_advisor_response(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    model=self.llm_model,
                    temperature=0.7,
                    max_tokens=500
                )
                
                # Create response message
                response_message = LLMMessage(
                    role="assistant",
                    content=response_content,
                    timestamp=datetime.now()
                )
                
            except Exception as e:
                # Fallback to default response if LLM service fails
                response_message = LLMMessage(
                    role="assistant",
                    content=f"LLM service error: {str(e)}. Using fallback response.",
                    timestamp=datetime.now()
                )
        else:
            # Fallback response if LLM service is not available
            response_message = LLMMessage(
                role="assistant",
                content="LLM service not configured. Please set up OpenAI or Ollama service.",
                timestamp=datetime.now()
            )
        
        # Update state with the response
        new_messages = state.messages + [response_message]
        
        return LLMAdvisorUpdateStateData(
            messages=new_messages,
            data=state.data,
            metadata=state.metadata
        )
    
    def _get_signal_data(self, state: LLMAdvisorState) -> LLMAdvisorDataArtefact:
        """Get signal data for advisory advisors"""
        return LLMAdvisorDataArtefact(
            description=f"Signal from {self.advisor_name}",
            artefact={"signal": "none", "confidence": 0.0, "reasoning": "Default"},
            output_mode=LLMAdvisorDataArtefactOutputMode.TEXT
        )


class AdvisoryAdvisor(LLMAdvisor):
    """Base class for advisory advisors that make final decisions"""
    signal_model_type: Type[BaseModel] = LLMAdvisorAdvice
    

class PersonaAdvisor(LLMAdvisor):
    """Base class for persona-based advisors"""
    def __init__(self, name: str = "", personality: str = "", provider: str = None, model: str = None):
        super().__init__(provider, model)
        self.persona_name = name
        self.personality = personality
        
        # Set instructions based on personality
        if personality:
            self.advisor_instructions = f"You are {name} with the following personality: {personality}"
        else:
            self.advisor_instructions = f"You are {name}"


# LLM Service availability check utility
def check_llm_service_availability(provider: str = None) -> Dict[str, Any]:
    """Check availability of LLM services"""
    result = {
        "available": False,
        "provider": provider,
        "details": {}
    }
    
    if not LLM_SERVICE_AVAILABLE:
        result["details"]["error"] = "LLM service adapter not available"
        return result
    
    try:
        llm_adapter = get_llm_adapter(provider)
        result["available"] = llm_adapter.test_connection()
        result["provider"] = llm_adapter.provider
        result["available_providers"] = llm_adapter.get_available_providers()
        
        if result["available"]:
            result["details"]["status"] = f"{llm_adapter.provider} service is available"
        else:
            result["details"]["status"] = f"{llm_adapter.provider} service is not available"
            
    except Exception as e:
        result["details"]["error"] = str(e)
    
    return result