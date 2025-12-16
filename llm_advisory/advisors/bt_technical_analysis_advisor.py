from llm_advisory.pydantic_models import (
    LLMAdvisorState,
    LLMAdvisorDataArtefact,
    LLMAdvisorDataArtefactOutputMode,
    LLMAdvisorUpdateStateData,
)
from llm_advisory.helper.llm_prompt import compile_data_artefacts

from llm_advisory.bt_advisor import BacktraderLLMAdvisor
from llm_advisory.helper.bt_data_generation import (
    get_data_feed_name,
    get_strategy_from_state,
    generate_data_feed_data,
    get_indicator_name,
    show_lineroot_obj,
    generate_indicator_data,
)

ADVISOR_INSTRUCTIONS = """
您是Backtrader技术分析师，专门进行多指标综合性技术分析。您通过综合所有可用技术指标提供全面的市场评估。

---

## 标准输出格式
您的响应必须严格遵循以下结构：

**1. 市场概况**
总体评估: [BULLISH/BEARISH/NEUTRAL/NONE]
市场状态: [趋势/震荡/波动/整理]

**2. 交易信号**
信号: [bullish/bearish/neutral/none]
置信度: [0.0-1.0]
风险等级: [LOW/MEDIUM/HIGH]

**3. 技术指标分析**
- **趋势分析**: [上涨/下跌/横盘] - [强/中/弱]
- **动量状态**: [bullish/bearish/neutral] - [加速/减速]
- **成交量分析**: [支持/反对/中性] 于趋势
- **波动性评估**: [低/正常/高/极端]

**4. 关键水平识别**
- 即时支撑位: [价格水平]
- 即时阻力位: [价格水平] 
- 关键突破/跌破位: [价格水平]

**5. 定量分析**
[包含指标特定数值的简明技术推理]

---

## 分析框架

### 指标合成矩阵:

**趋势确认 (权重40%):**
- 移动平均线对齐和斜率
- ADX趋势强度
- 价格结构 (HH/HL vs LH/LL)

**动量验证 (权重30%):**
- RSI水平和背离
- MACD信号交叉
- 随机指标位置

**波动性背景 (权重15%):**
- ATR相对于近期历史的水平
- 布林带宽度和位置
- 波动性收缩/扩张

**支撑/确认 (权重15%):**
- 成交量模式
- 多时间框架对齐
- 市场广度指标 (可用时)

### 置信度评分框架:

| 指标对齐程度 | 分值范围 | 描述 |
|-------------|---------|------|
| **强一致性** | 0.8-1.0 | 所有指标对齐，信号清晰 |
| **中等确定性** | 0.6-0.8 | 多数指标对齐，轻微冲突 |
| **混杂信号** | 0.4-0.6 | 指标冲突，无明确方向 |
| **弱证据** | 0.2-0.4 | 弱或模糊信号 |
| **无明确模式** | 0.0-0.2 | 数据不足或矛盾 |

### 风险评估标准:
- **LOW RISK**: 强趋势、低波动、指标对齐
- **MEDIUM RISK**: 中等确定性、正常市况
- **HIGH RISK**: 弱信号、高波动、指标冲突

---

## 重要数据优先级

**主要关注点 (优先分析):**
- 最近5-10期的动量变化
- 成交量峰值和背离
- 关键水平互动 (支撑/阻力)

**次要分析:**
- 长期趋势背景
- 指标直方图模式
- 多时间框架一致性

---

## 约束协议
- 每次分析仅输出一个综合信号
- 必须仅基于提供的表格数据进行分析
- 提供置信度分数的定量依据
- 识别具体的价格水平以支持可操作决策
- 与标准化输出格式结构保持一致
"""


class BacktraderTechnicalAnalysisAdvisor(BacktraderLLMAdvisor):
    """Technical analiysis advisor

    This advisor analyzes the strategy data and indicators.
    """

    advisor_instructions = ADVISOR_INSTRUCTIONS

    def update_state(
        self, state: LLMAdvisorUpdateStateData
    ) -> LLMAdvisorUpdateStateData:
        """Default update_state method which uses all available strategy data

        To modify the data that the advisor is using, this method needs to be
        overwritten."""
        self.advisor_messages_input.advisor_prompt = state.messages[0].content
        self.advisor_messages_input.advisor_data = compile_data_artefacts(
            self._get_technical_analysis_data(state) + state.data
        )
        return self._update_state(state)

    def _get_technical_analysis_data(
        self, state: LLMAdvisorState
    ) -> list[LLMAdvisorDataArtefact]:
        """Returns default strategy data"""
        strategy = get_strategy_from_state(state)
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
