from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Literal


class LLMMessage(BaseModel):
    """LLM message model for advisory system"""
    role: str = Field(description="Message role: system, user, assistant")
    content: str = Field(description="Message content")
    timestamp: Optional[datetime] = None


class LLMAdvisorDataArtefact(BaseModel):
    """Data artefact for LLM advisor"""
    description: str = Field(description="Description of the data artefact")
    artefact: Dict[str, Any] = Field(description="The actual data artefact")
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
    
    def __init__(self):
        self.advisor_messages_input = AdvisorMessagesInput()
        
    @abstractmethod
    def update_state(self, state: LLMAdvisorUpdateStateData) -> LLMAdvisorUpdateStateData:
        """Update the advisor state with new data
        
        Args:
            state: Current state data
            
        Returns:
            Updated state data
        """
        pass
    
    def _update_state(self, state: LLMAdvisorUpdateStateData) -> LLMAdvisorUpdateStateData:
        """Default implementation for state update"""
        # This would typically call an LLM and update the state
        # For now, return a basic response
        return LLMAdvisorUpdateStateData(
            messages=[LLMMessage(role="assistant", content="Default response")],
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
    def __init__(self, name: str = "", personality: str = ""):
        super().__init__()
        self.persona_name = name
        self.personality = personality