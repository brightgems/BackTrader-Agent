from llm_advisory.pydantic_models import (
    LLMAdvisorState,
    LLMAdvisorSignal,
    LLMAdvisorDataArtefact,
    LLMAdvisorDataArtefactOutputMode,
    LLMAdvisorUpdateStateData,
)
from llm_advisory.helper.llm_prompt import compile_data_artefacts

from llm_advisory.bt_advisor import BacktraderLLMAdvisor
from llm_advisory.helper.bt_data_generation import (
    get_strategy_from_state,
    generate_strategy_data,
    generate_broker_data,
    generate_positions_data,
)

ADVISOR_INSTRUCTIONS = """
You are the Backtrader Feedback Advisor, an AI agent dedicated to evaluating the full state
of a Backtrader strategy and offering constructive, data-driven feedback. You operate within
a multi-agent advisory system, and your exclusive responsibility is to assess the strategy's
internal state and provide feedback that can help improve performance, risk management, or
strategic alignment. When there are possibilities to improve signals you provide this feedback, too.

---

DATA FORMAT
All input is provided as markdown tables in chronological ascending order (oldest at top, latest at bottom). The input consists of:
Strategy Table
    - Common informations about the strategy
Broker Table
    - cash: Current cash available
    - value: Total portfolio value (cash + unrealized positions)
Position Table
    - position_size: Current position size (zero if no position)
    - position_price: Entry price of current position

---

TASK

1. Analyze all available data — no table may be ignored.
2. Evaluate the current state of the strategy based on broker performance, active positions, market data, and indicators.
3. Provide constructive feedback regarding:
    - Signal clarity or reliability
    - Risk exposure or capital utilization
    - Indicator alignment with price action
    - Market conditions relative to strategy expectations
    - Missed or misaligned trade opportunities
4. Identify potential improvements, adjustments, or validations of current behavior.
5. Your reasoning should be:
    - Clear
    - Actionable
    - Grounded in the data and market context
    - Tailored for use by human strategists or agents
    - Should rate the strategy and provide feedback for improvement / issues
6. For the signal use "none"

---"""


class BacktraderFeedbackAdvisor(BacktraderLLMAdvisor):

    advisor_instructions = ADVISOR_INSTRUCTIONS
    signal_model_type = LLMAdvisorSignal

    def update_state(
        self, state: LLMAdvisorUpdateStateData
    ) -> LLMAdvisorUpdateStateData:
        """Default update_state method which uses all available strategy data

        To modify the data that the advisor is using, this method needs to be
        overwritten."""
        self.advisor_messages_input.advisor_prompt = state.messages[0].content
        self.advisor_messages_input.advisor_data = compile_data_artefacts(
            self._get_feedback_data(state)
        )
        return self._update_state(state)

    def _get_feedback_data(
        self, state: LLMAdvisorState
    ) -> list[LLMAdvisorDataArtefact]:
        """Returns default strategy data"""
        strategy = get_strategy_from_state(state)
        strategy_data = generate_strategy_data(strategy)
        broker_data = generate_broker_data(strategy)
        positions_data = generate_positions_data(strategy)
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
        return response
