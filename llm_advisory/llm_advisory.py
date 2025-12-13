from abc import ABC, abstractmethod
from typing import List, Dict, Any
from llm_advisory.llm_advisor import LLMAdvisor, LLMAdvisorState, LLMAdvisorUpdateStateData


class LLMAdvisory(ABC):
    """Abstract base class for LLM Advisory system"""
    
    def __init__(self):
        self.all_advisors: List[LLMAdvisor] = []
        self.metadata: Dict[str, Any] = {}
        
    @abstractmethod
    def init_strategy(self, strategy, **kwargs):
        """Initialize the advisory system with a trading strategy
        
        Args:
            strategy: The trading strategy instance
            **kwargs: Additional initialization parameters
        """
        pass
    
    def add_advisor(self, advisor: LLMAdvisor):
        """Add an advisor to the advisory system
        
        Args:
            advisor: The advisor instance to add
        """
        self.all_advisors.append(advisor)
    
    def update_state(self, state: LLMAdvisorUpdateStateData) -> LLMAdvisorUpdateStateData:
        """Update the advisory system state
        
        Args:
            state: The current system state
            
        Returns:
            Updated system state
        """
        # Default implementation - in practice this would coordinate all advisors
        return LLMAdvisorUpdateStateData(
            messages=state.messages,
            data=state.data,
            metadata=state.metadata
        )
    
    def get_advisors_by_type(self, advisor_type: type) -> List[LLMAdvisor]:
        """Get advisors of a specific type
        
        Args:
            advisor_type: The type of advisor to filter for
            
        Returns:
            List of advisors of the specified type
        """
        return [advisor for advisor in self.all_advisors if isinstance(advisor, advisor_type)]