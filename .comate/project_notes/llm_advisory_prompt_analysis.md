# LLM Advisor 提示词结构分析报告

## 项目概况

本项目是一个基于 Backtrader 的 LLM Advisory 系统，包含多个专门化的 advisor，用于提供交易决策建议。系统采用多智能体架构，每个 advisor 专注于特定的技术分析领域。

## 一、系统架构分析

### 1.1 核心组件结构
```
llm_advisory/
├── llm_advisor.py           # 基础 LLM Advisor 抽象类
├── bt_advisor.py           # Backtrader 专用 LLM Advisor 基类
├── advisors/               # 具体 advisor 实现
│   ├── bt_trend_advisor.py             # 趋势分析
│   ├── bt_technical_analysis_advisor.py # 技术分析
│   ├── bt_candle_pattern_advisor.py    # 蜡烛图模式
│   ├── bt_reversal_advisor.py          # 反转信号
│   ├── bt_feedback_advisor.py          # 策略反馈
│   └── __init__.py
├── helper/
│   ├── llm_prompt.py                   # 提示词编译工具
│   └── bt_data_generation.py          # 数据生成工具
└── pydantic_models.py                 # 数据模型
```

### 1.2 LLM 消息构建流程
1. **数据准备**：通过 `bt_data_generation.py` 生成策略数据
2. **提示词编译**：通过 `llm_prompt.py` 格式化数据为 LLM 可读格式
3. **消息发送**：通过 `llm_service_adapter.py` 调用 LLM 服务
4. **响应解析**：提取信号、置信度和推理说明

## 二、各 Advisor 提示词结构分析

### 2.1 BacktraderTrendAdvisor (趋势advisor)

**当前提示词问题：**
- ✅ 信号格式统一：`bullish/bearish/neutral/none`
- ✅ 包含置信度：0.0-1.0
- ❌ **缺失趋势强度量化**：只有方向，没有强弱指标
- ❌ **数据格式不一致**：使用自定义字典格式而非标准表格

**数据格式不一致示例：**
```python
# 当前使用自定义格式
{
    "price_history": [100.0, 101.0, 102.0],
    "ma_short": 101.5,
    "ma_long": 100.2,
    # ... 其他指标
}

# 建议统一为表格格式
| datetime | open | high | low | close | volume | ma_short | ma_long | ...
```

### 2.2 BacktraderTechnicalAnalysisAdvisor (技术分析advisor)

**当前提示词特点：**
- ✅ 支持多数据源表格格式
- ✅ 要求全面分析所有数据
- ✅ 包含置信度评分
- ❌ **缺乏具体的分析框架**：没有明确的分析步骤指导
- ❌ **输出格式不具体**：只要求"结构化格式"，但未定义具体结构

**建议改进：**
```markdown
TASK
1. 趋势分析：[强/中/弱] [上升/下降/震荡] 趋势
2. 动量分析：RSI超买/超卖状态，动量方向
3. 支撑阻力：关键价格水平识别
4. 信号输出：具体交易建议 + 置信度
```

### 2.3 BacktraderCandlePatternAdvisor (蜡烛图模式advisor)

**当前提示词问题：**
- ✅ 明确的模式识别任务
- ✅ 要求模式名称作为开头
- ❌ **模式名称规范缺失**：缺乏标准化的模式名称列表
- ❌ **置信度评估标准不明确**：如何评估模式匹配度未定义

**改进建议：**
```markdown
## 标准模式列表
- bullish: 锤子线、看涨吞没、晨星...
- bearish: 上吊线、看跌吞没、黄昏星...
- neutral: 十字星、纺锤线...

## 置信度评估标准
- 0.8-1.0: 完美匹配标准形态
- 0.6-0.8: 基本匹配，有轻微偏差
- 0.4-0.6: 部分特征匹配
- <0.4: 不明确或不符合
```

### 2.4 BacktraderReversalAdvisor (反转advisor)

**关键问题：**
- ❌ **与趋势advisor高度相似**：使用相同的数据格式和分析方法
- ❌ **缺乏反转特定指标**：没有专门的动量反转指标
- ❌ **信号区分度不足**：难以与趋势advisor的"neutral"信号区分

**重复代码问题：**
```python
# 趋势advisor和反转advisor使用相同的指标集
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
```

### 2.5 BacktraderFeedbackAdvisor (反馈advisor)

**特点分析：**
- ✅ 专注于策略性能评估
- ✅ 使用"none"信号，专注于反馈
- ❌ **反馈标准不明确**：缺乏量化的评估指标
- ❌ **改进建议过于宽泛**：没有具体的可执行建议框架

## 三、信号输出标准化问题

### 3.1 信号格式不统一问题

**当前信号模型：**
```python
class BacktraderLLMAdvisorSignal(LLMAdvisorSignal):
    signal: Literal["bullish", "bearish", "neutral", "none"]
    confidence: float  # 0.0-1.0
    reasoning: str
```

**缺失的关键维度：**
1. **趋势强度**：强弱程度的量化指标
2. **时间框架**：信号的时效性评估
3. **风险等级**：与信号相关的风险指标

### 3.2 置信度评估不一致

**问题表现：**
- 各advisor对置信度的理解不一致
- 缺乏统一的评估标准
- 难以跨advisor比较置信度水平

## 四、数据格式标准化问题

### 4.1 数据表示方式混乱

**当前问题：**
- 混合使用自定义字典和Markdown表格格式
- 时间序列数据的表示不一致
- 指标名称和单位不统一

### 4.2 `compile_data_artefacts` 函数限制

**功能局限：**
```python
def compile_data_artefacts(data_artefacts: List[LLMAdvisorDataArtefact]) -> str:
    # 仅支持简单表格转换
    # 缺乏复杂数据格式的统一处理
```

## 五、具体改进建议

### 5.1 统一提示词框架

**标准模板建议：**
```
## 信号输出格式
1. 信号方向: [bullish/bearish/neutral/none]
2. 置信度: [0.0-1.0]
3. 趋势强度: [weak/medium/strong]
4. 时间框架: [short/medium/long-term]
5. 关键水平: [支撑位/阻力位]
6. 风险评估: [low/medium/high]

## 推理说明
[详细分析过程...]
```

### 5.2 特定advisor优化

**趋势advisor：**
- 添加趋势强度量化指标（ADX值、均线角度等）
- 明确定义趋势确认条件

**技术分析advisor：**
- 添加多时间框架分析
- 明确各指标的权重分配

**蜡烛图advisor：**
- 标准化模式名称列表
- 添加模式匹配度评分标准

**反转advisor：**
- 重构为专门的动量反转指标
- 添加反转确认条件

### 5.3 数据格式标准化

**统一数据表示：**
```python
# 标准表格格式
output_mode = LLMAdvisorDataArtefactOutputMode.STANDARDIZED_TABLE

# 包含标准字段：
# - 时间戳
# - 价格数据 (OHLCV)
# - 技术指标值
# - 指标状态 (超买/超卖等)
```

## 六、实施优先级

### 高优先级（立即实施）
1. 统一信号输出格式标准
2. 修复数据格式不一致问题
3. 明确定义置信度评估标准

### 中优先级（近期实施）
1. 重构反转advisor，避免与趋势advisor重复
2. 完善各advisor的特定分析框架
3. 优化反馈advisor的评估标准

### 低优先级（长期优化）
1. 添加更复杂的技术指标支持
2. 实现多时间框架分析
3. 开发高级风险评估功能

## 七、总结

当前LLM Advisory系统在提示词结构上存在显著的不一致性和标准化问题。主要问题集中在信号输出格式、数据表示方式和各advisor的专业化程度方面。通过实施上述改进建议，可以显著提升系统的信号质量和决策支持能力。