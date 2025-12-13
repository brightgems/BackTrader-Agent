from .bt_advisor import BacktraderLLMAdvisor
from .bt_advisory import BacktraderLLMAdvisory
from .llm_advisor import LLMAdvisor, AdvisoryAdvisor, PersonaAdvisor, check_llm_service_availability

# Import advisors
from .advisors import (
    BacktraderTrendAdvisor,
    BacktraderTechnicalAnalysisAdvisor,
    BacktraderCandlePatternAdvisor,
    BacktraderFeedbackAdvisor,
    BacktraderPersonaAdvisor,
    BacktraderStrategyAdvisor,
    BacktraderReversalAdvisor
)

__version__ = "0.0.1"

__all__ = [
    "BacktraderLLMAdvisor", 
    "BacktraderLLMAdvisory", 
    "LLMAdvisor",
    "AdvisoryAdvisor", 
    "PersonaAdvisor",
    "BacktraderTrendAdvisor",
    "BacktraderTechnicalAnalysisAdvisor",
    "BacktraderCandlePatternAdvisor",
    "BacktraderFeedbackAdvisor",
    "BacktraderPersonaAdvisor",
    "BacktraderStrategyAdvisor",
    "BacktraderReversalAdvisor",
    "check_llm_service_availability",
    "__version__"
]