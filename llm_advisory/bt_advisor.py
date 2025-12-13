from backtrader import Strategy

from llm_advisory.llm_advisor import LLMAdvisor
from llm_advisory.pydantic_models import (
    LLMAdvisorState,
    LLMAdvisorDataArtefact,
    LLMAdvisorDataArtefactOutputMode,
    LLMAdvisorUpdateStateData,
)
from llm_advisory.helper.llm_prompt import compile_data_artefacts

from llm_advisory.pydantic_models import BacktraderLLMAdvisorSignal
from llm_advisory.helper.bt_data_generation import (
    show_lineroot_obj,
    get_strategy_from_state,
    get_data_feed_name,
    get_indicator_name,
    generate_strategy_data,
    generate_broker_data,
    generate_positions_data,
    generate_data_feed_data,
    generate_indicator_data,
)


class BacktraderLLMAdvisor(LLMAdvisor):
    """LLM Advisor for backtrader"""

    # Default signal for backtrader advisors
    signal_model_type = BacktraderLLMAdvisorSignal

    def init_strategy(self, strategy: Strategy) -> None:
        """Init method of advisors

        This method will get invoked when advisory's init method is called.
        By overriding this method, advisors are able to add indicators to a
        strategy"""
        pass

    def update_state(
        self, state: LLMAdvisorUpdateStateData
    ) -> LLMAdvisorUpdateStateData:
        """Default update_state method which uses all available strategy data

        To modify the data that the advisor is using, this method needs to be
        overwritten."""
        self.advisor_messages_input.advisor_prompt = state.messages[0].content
        self.advisor_messages_input.advisor_data = compile_data_artefacts(
            self._get_default_strategy_data(state) + state.data
        )
        return self._update_state(state)

    def _get_default_strategy_data(
        self, state: LLMAdvisorState
    ) -> list[LLMAdvisorDataArtefact]:
        """Returns default strategy data"""
        strategy = get_strategy_from_state(state)
        strategy_data = generate_strategy_data(strategy)
        broker_data = generate_broker_data(strategy)
        positions_data = generate_positions_data(strategy)
        data_feeds_data = {
            get_data_feed_name(data_feed): generate_data_feed_data(
                data_feed=data_feed,
                lookback_period=state.metadata["data_lookback_period"],
            )
            for data_feed in strategy.datas
        }
        indicators_data = {
            get_indicator_name(indicator): generate_indicator_data(
                indicator=indicator,
                lookback_period=state.metadata["indicator_lookback_period"],
            )
            for indicator in strategy.getindicators()
            if show_lineroot_obj(indicator)
        }
        response = []
        response.append(
            LLMAdvisorDataArtefact(
                description="Strategy", artefact=strategy_data.description
            )
        )
        response.append(
            LLMAdvisorDataArtefact(
                description="Broker",
                artefact=broker_data.description,
                output_mode=LLMAdvisorDataArtefactOutputMode.MARKDOWN_TABLE,
            )
        )
        for data_name, position in positions_data.positions.items():
            response.append(
                LLMAdvisorDataArtefact(
                    description=f"Position {data_name}",
                    artefact=position.model_dump(),
                    output_mode=LLMAdvisorDataArtefactOutputMode.MARKDOWN_TABLE,
                )
            )
        for data_feed_data in data_feeds_data.values():
            response.append(
                LLMAdvisorDataArtefact(
                    description=f"DataFeed {data_feed_data.name}",
                    artefact=data_feed_data.data,
                    output_mode=LLMAdvisorDataArtefactOutputMode.MARKDOWN_TABLE,
                )
            )
        for indicator_data in indicators_data.values():
            response.append(
                LLMAdvisorDataArtefact(
                    description=f"Indicator {indicator_data.name}",
                    artefact=indicator_data.data,
                    output_mode=LLMAdvisorDataArtefactOutputMode.MARKDOWN_TABLE,
                )
            )
        return response
