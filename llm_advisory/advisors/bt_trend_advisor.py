import backtrader as bt
import numpy as np

from llm_advisory.pydantic_models import (
    LLMAdvisorDataArtefact,
    LLMAdvisorUpdateStateData,
)
from llm_advisory.helper.llm_prompt import compile_data_artefacts

from llm_advisory.bt_advisor import BacktraderLLMAdvisor
from llm_advisory.helper.bt_data_generation import get_data_feed_name

ADVISOR_INSTRUCTIONS = """
您是Backtrader趋势advisor，专门使用技术指标检测和量化市场趋势。您在多智能体咨询系统中运行，提供清晰、量化的趋势分析。

---

## 标准输出格式
您的响应必须严格遵循以下结构：

**1. 趋势分析摘要**
Trend Direction: [BULLISH/BEARISH/NEUTRAL/NONE]
Trend Strength: [WEAK/MEDIUM/STRONG]
Time Frame: [SHORT/MEDIUM/LONG] term

**2. 交易信号**
Signal: [bullish/bearish/neutral/none]
Confidence: [0.0-1.0]
Risk Level: [LOW/MEDIUM/HIGH]

**3. 关键指标状态**
- MA Alignment: [bullish/bearish/neutral]
- ADX Trend Strength: [weak/medium/strong]
- RSI Positioning: [oversold/neutral/overbought]
- Volatility Level: [low/medium/high]
- Overall Momentum: [negative/neutral/positive]

**4. 定量分析**
[包含具体数值的简明技术推理]

---

## 趋势判断标准

### 主要趋势指标:
- **移动平均对比 (权重: 40%):** 
  - Bullish: 短期MA > 长期MA (差值X%)
  - Bearish: 短期MA < 长期MA (差值X%)
  - Neutral: MA差值在0.5%以内

- **ADX强度 (权重: 30%):**
  - 强: ADX > 50
  - 中: ADX 25-50  
  - 弱: ADX < 25

- **价格行为 (权重: 30%):**
  - 持续的高点/低点 = Bullish
  - 持续的低点/高点 = Bearish
  - 横向运动 = Neutral

### 置信度评分矩阵:

| 指标对齐程度 | 分值范围 |
|-------------|---------|
| 所有指标强对齐 | 0.8-1.0 |
| 多数指标对齐 | 0.6-0.8 |
| 信号混杂 | 0.4-0.6 |
| 弱信号或冲突信号 | 0.2-0.4 |
| 数据不足 | 0.0-0.2 |

### 风险评估:
- **LOW**: 强趋势、低波动、指标对齐
- **MEDIUM**: 中等趋势强度、正常波动
- **HIGH**: 弱趋势、高波动、指标冲突

---

## 数据字段解释
提供的数据包括:
- price_history: 分析方向性偏差
- ma_short/ma_long: 主要趋势方向
- ma_diff: 趋势程度指标
- adx: 趋势强度测量
- atr: 波动性评估
- rsi: 动量确认
- bb_width: 波动性背景
- linreg_slope: 基础趋势方向

---

## 重要约束
- 每次分析仅输出一个趋势信号
- 所有分析必须基于提供的定量数据
- 提供置信度分数的具体数值依据
- 信号必须对即时交易决策具有可操作性
- 使用上述框架中的标准化术语
"""


class BollingerBandsW(bt.ind.BollingerBands):
    """
    Extends the Bollinger Bands with a Percentage line
    """

    alias = ("BBW",)
    lines = ("bbw",)
    plotlines = dict(
        top=dict(_plotskip=True),
        mid=dict(_plotskip=True),
        bot=dict(_plotskip=True),
        bbw=dict(_name="bbw", color="green", _skipnan=True),
    )
    plotinfo = dict(subplot=True)

    def __init__(self):
        super(BollingerBandsW, self).__init__()
        self.l.bbw = (self.l.top - self.l.bot) / self.l.mid


class LinearRegressionSlope(bt.Indicator):
    """
    Computes the slope of a linear regression over the last `period` values of `data`.
    """

    lines = ("slope",)
    params = (("period", 10),)  # look‐back window

    def __init__(self):
        # ensure we have at least `period` data points before calculating
        self.addminperiod(self.params.period)

    def next(self):
        # grab the last `period` values as a NumPy array
        y = np.array(self.data.get(size=self.params.period))
        x = np.arange(self.params.period)
        # compute slope = Cov(x,y) / Var(x)
        xm = x.mean()
        ym = y.mean()
        slope = ((x - xm) * (y - ym)).sum() / ((x - xm) ** 2).sum()
        self.lines.slope[0] = slope


class BacktraderTrendAdvisor(BacktraderLLMAdvisor):
    """Trend advisor

    This advisor tries to identify the current trend by using multiple indicators.
    """

    advisor_instructions = ADVISOR_INSTRUCTIONS
    

    def __init__(
        self,
        llm_provider: str = "ollama", # Default to ollama for local development
        llm_model: str = "qwen3-vl", # Default model
        short_ma_period: int = 10,  # period for short moving average
        long_ma_period: int = 50,  # period for long moving average
        lookback_period: int = 5,  # lookback period for trend data
        add_all_data_feeds: bool = False,  # adds all data if True, only first if False
    ):
        super().__init__(llm_provider, llm_model)
        self.short_ma_period = short_ma_period
        self.long_ma_period = long_ma_period
        self.lookback_period = lookback_period
        self.add_all_data_feeds = add_all_data_feeds
        self.indicators: dict[str, dict[str, bt.Indicator]] = {}

    def init_strategy(self, strategy):
        # init and add all required indicators
        data_feeds = (
            [strategy.datas[0]] if not self.add_all_data_feeds else strategy.datas
        )
        for data_feed in data_feeds:
            short_ma = bt.ind.SMA(
                data_feed,
                period=self.short_ma_period,
                # plotskip=True,
                plotname="bt_trend_short_ma",
            )
            long_ma = bt.ind.SMA(
                data_feed,
                period=self.long_ma_period,
                # plotskip=True,
                plotname="bt_trend_long_ma",
            )
            adx = bt.ind.AverageDirectionalMovementIndex(
                data_feed,
                # plotskip=True,
                plotname="bt_trend_adx",
            )
            atr = bt.ind.ATR(
                data_feed,
                # plotskip=True,
                plotname="bt_trend_atr",
            )
            rsi = bt.ind.RSI(
                data_feed,
                # plotskip=True,
                plotname="bt_trend_rsi",
            )
            bb = BollingerBandsW(
                data_feed,
                # plotskip=True,
                plotname="bt_trend_bb",
            )
            linreg_slope = LinearRegressionSlope(
                data_feed,
                # plotskip=True,
                period=10,
            )
            data_indicators = {
                "short_ma": short_ma,
                "long_ma": long_ma,
                "ma_diff": long_ma - short_ma,
                "adx": adx,
                "atr": atr,
                "rsi": rsi,
                "bb_width": bb.bbw,
                "linreg_slope": linreg_slope,
            }
            self.indicators[data_feed] = data_indicators

    def update_state(
        self, state: LLMAdvisorUpdateStateData
    ) -> LLMAdvisorUpdateStateData:
        self.advisor_messages_input.advisor_prompt = state.messages[0].content
        self.advisor_messages_input.advisor_data = compile_data_artefacts(
            self._get_trend_indicators_data(self.lookback_period)
        )
        return self._update_state(state)

    def _get_trend_indicators_data(
        self, lookback_period: int, accuracy: int = 4
    ) -> LLMAdvisorDataArtefact:
        response = []
        for data_feed, indicators in self.indicators.items():
            feed_data = {
                "price_history": [data_feed[-i] for i in range(lookback_period)]
            }
            feed_data |= {
                indicator_name: round(indicator[0], accuracy)
                for indicator_name, indicator in indicators.items()
            }
            response.append(
                LLMAdvisorDataArtefact(
                    description=f"DataFeed {get_data_feed_name(data_feed)}",
                    artefact=feed_data,
                )
            )
        return response
