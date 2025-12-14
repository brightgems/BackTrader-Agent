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
