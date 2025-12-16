from backtrader import Strategy

from llm_advisory.llm_advisory import LLMAdvisory

from llm_advisory.bt_advisor import BacktraderLLMAdvisor
from llm_advisory.state_advisors.bt_advisory_advisor import BacktraderAdvisoryAdvisor

DATA_LOOKBACK_PERIOD = 25
INDICATOR_LOOKBACK_PERIOD = 10


class BacktraderLLMAdvisory(LLMAdvisory):
    """LLM Advisory for backtrader"""

    def __init__(self):
        super().__init__()
        self.advisor_names = {}  # 存储advisor名称映射

    def add_advisor(self, name: str, advisor):
        """Add an advisor with a name to the advisory system
        
        Args:
            name: The name identifier for the advisor
            advisor: The advisor instance to add
        """
        self.all_advisors.append(advisor)
        self.advisor_names[name] = advisor

    def get_advisor_by_name(self, name: str):
        """Get an advisor by its name
        
        Args:
            name: The name of the advisor to retrieve
            
        Returns:
            The advisor instance or None if not found
        """
        return self.advisor_names.get(name)

    def get_advice(self, advisor_name: str):
        """Get trading advice from a specific advisor
        
        Args:
            advisor_name: The name of the advisor to get advice from
            
        Returns:
            Dictionary containing signal, confidence, and reasoning
        """
        advisor = self.get_advisor_by_name(advisor_name)
        if not advisor:
            return {"signal": "none", "reasoning": f"Advisor '{advisor_name}' not found"}
        
        try:
            # Create a basic state for the advisor
            from llm_advisory.llm_advisor import LLMAdvisorUpdateStateData, LLMMessage
            from llm_advisory.pydantic_models import LLMAdvisorDataArtefact
            
            # Create initial state with proper data artefacts
            initial_message = LLMMessage(
                role="system",
                content="Provide trading advice based on current market conditions"
            )
            
            # Create valid data artefacts
            data_artefacts = [
                LLMAdvisorDataArtefact(
                    description="Strategy Data",
                    artefact={"status": "initializing"},
                    output_mode="text"
                )
            ]
            
            state = LLMAdvisorUpdateStateData(
                messages=[initial_message],
                data=data_artefacts,
                metadata=self.metadata
            )
            
            # Update state with advisor-specific data
            updated_state = advisor.update_state(state)
            
            # Extract the last message as the advice
            if updated_state.messages:
                last_message = updated_state.messages[-1]
                reasoning = last_message.content
                
                # Parse the response to extract signal and confidence
                signal = "none"
                confidence = 0.0
                
                # Basic parsing of common signal keywords
                if any(word in reasoning.lower() for word in ["bullish", "buy", "上涨", "看涨"]):
                    signal = "bullish"
                    confidence = 0.7
                elif any(word in reasoning.lower() for word in ["bearish", "sell", "下跌", "看跌"]):
                    signal = "bearish"
                    confidence = 0.7
                elif any(word in reasoning.lower() for word in ["neutral", "hold", "中性"]):
                    signal = "neutral"
                    confidence = 0.5
                
                return {
                    "signal": signal,
                    "confidence": confidence,
                    "reasoning": reasoning
                }
            else:
                return {"signal": "none", "reasoning": "No response from advisor"}
                
        except Exception as e:
            return {"signal": "none", "reasoning": f"Error getting advice: {str(e)}"}

    def init_strategy(
        self,
        strategy: Strategy,
        data_lookback_period: int = DATA_LOOKBACK_PERIOD,
        indicator_lookback_period=INDICATOR_LOOKBACK_PERIOD,
    ) -> None:
        """Initializes backtrader functionality

        This method needs to be called inside __init__ of the strategy it is running on
        ```
        class Strategy(bt.Strategy):

            def __init__(self):
                self.bt_llm_advisory = BacktraderLLMAdvisory(...)
                self.bt_llm_advisory.init_strategy(self)
        ```
        """
        self.advisory_advisor = BacktraderAdvisoryAdvisor()
        self.metadata["strategy"] = strategy
        self.metadata["data_lookback_period"] = data_lookback_period
        self.metadata["indicator_lookback_period"] = indicator_lookback_period
        for advisor in self.all_advisors + [self.advisory_advisor]:
            if not isinstance(advisor, BacktraderLLMAdvisor):
                continue
            if not hasattr(advisor, "init_strategy"):
                continue
            advisor.init_strategy(strategy)
