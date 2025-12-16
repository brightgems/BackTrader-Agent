import backtrader as bt

from llm_advisory.helper.llm_prompt import compile_data_artefacts
from llm_advisory.pydantic_models import (
    LLMAdvisorDataArtefact,
    LLMAdvisorDataArtefactOutputMode,
    LLMAdvisorUpdateStateData,
)

from llm_advisory.bt_advisor import BacktraderLLMAdvisor
from llm_advisory.helper.bt_data_generation import (
    generate_data_feed_data,
    get_strategy_from_state,
)


ADVISOR_INSTRUCTIONS = """
您是基于Backtrader的蜡烛图模式顾问，专门使用OHLC数据识别经典蜡烛图形态。在多智能体咨询系统中，您的唯一职责是分析近期市场行为并输出清晰、结构化的蜡烛图模式信号。

---

## 标准输出格式
您的响应必须严格遵循以下结构：

**1. 模式识别**
Pattern: [BULLISH/BEARISH/NEUTRAL] - [模式名称]

**2. 交易信号**  
Signal: [bullish/bearish/neutral/none]
Confidence: [0.0-1.0]
Trend Context: [上升趋势/下降趋势/震荡整理]

**3. 模式特征**
- 实体大小: [小/中/大] - [数值比例]
- 影线比例: [上影线/下影线/均衡] - [数值比例]
- 前一根方向: [bullish/bearish/neutral]

**4. 分析推理**
[包含具体价格水平的简明技术分析]

---

## 蜡烛图模式标准

### 高置信度模式 (0.8-1.0):
- **看涨吞没**: 当前阳线完全吞没前一根阴线
- **看跌吞没**: 当前阴线完全吞没前一根阳线  
- **锤子线/倒锤头**: 小实体长影线，出现在下跌趋势后
- **射击之星/上吊线**: 小实体长影线，出现在上升趋势后
- **早晨之星**: 阴线→十字星→阳线的序列组合
- **黄昏之星**: 阳线→十字星→阴线的序列组合

### 中等置信度模式 (0.6-0.8):
- **十字星**: 开盘≈收盘，显示市场犹豫不决
- **纺锤线**: 小实体平衡影线，表明市场整理
- **刺透线/孕线**: 部分吞没形态

### 低置信度模式 (0.3-0.5):
- 模式特征较弱或信号混杂

### 无模式 (0.0-0.2):
- 未检测到有效的蜡烛图模式

---

## 置信度计算标准
- **实体/影线分析**: 计算实体大小比例和影线比例
- **趋势对齐**: 模式必须与主导趋势方向一致
- **成交量考量**: 高成交量提高置信度（可用时）
- **多蜡烛确认**: 多蜡烛模式获得更高置信度

---

## 数据格式
按时间顺序提供OHLC数据，最新蜡烛在底部。
分析最近1-3根蜡烛进行模式检测。

---

## 重要约束
- 每次分析仅输出一个模式信号
- 所有分析必须基于提供的OHLC数据
- 使用列表中的标准化模式名称
- 提供置信度分数的定量依据
- 信号必须对即时交易决策具有可操作性
"""


class BacktraderCandlePatternAdvisor(BacktraderLLMAdvisor):
    """Candle pattern advisor

    This advisor identifies candlestick patterns on OHLC data.
    """

    advisor_instructions = ADVISOR_INSTRUCTIONS

    def __init__(
        self,
        lookback_period: int = 5,  # lookback period for ohlc data
        add_all_data_feeds: bool = False,  # should all data feeds be included
    ):
        super().__init__()
        self.lookback_period = lookback_period
        self.add_all_data_feeds = add_all_data_feeds

    def update_state(
        self, state: LLMAdvisorUpdateStateData
    ) -> LLMAdvisorUpdateStateData:
        self.advisor_messages_input.advisor_prompt = state.messages[0].content
        strategy = get_strategy_from_state(state)
        data_feeds = (
            [strategy.datas[0]] if not self.add_all_data_feeds else strategy.datas
        )
        data_feed_data = self._get_ohlc_data(data_feeds, self.lookback_period)
        self.advisor_messages_input.advisor_data = compile_data_artefacts(
            data_feed_data
        )
        return self._update_state(state)

    def _get_ohlc_data(
        self, data_feeds: list[bt.DataBase], lookback_period: int
    ) -> list[LLMAdvisorDataArtefact]:
        ohlc_data = []
        for data_feed in data_feeds:
            feed_data = generate_data_feed_data(
                data_feed=data_feed,
                lookback_period=lookback_period,
                only_close=False,
                add_volume=False,
            )
            ohlc_data.append(
                LLMAdvisorDataArtefact(
                    description=f"DataFeed {feed_data.name}",
                    artefact=feed_data.data,
                    output_mode=LLMAdvisorDataArtefactOutputMode.MARKDOWN_TABLE,
                )
            )
        return ohlc_data
