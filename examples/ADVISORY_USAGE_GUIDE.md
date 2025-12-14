# LLM Advisory 交易信号使用指南

## 概述
本项目提供了一套完整的LLM Advisory系统，用于在Backtrader框架下生成交易信号。系统采用多advisor架构，每个advisor专注于特定领域的分析，共同协作产生最终交易决策。

## 核心组件

### 1. Advisor 类型
- **BacktraderTrendAdvisor**: 趋势分析顾问，检测市场趋势
- **BacktraderTechnicalAnalysisAdvisor**: 技术分析顾问，综合技术指标
- **BacktraderReversalAdvisor**: 反转信号顾问，检测趋势反转
- **BacktraderPersonaAdvisor**: 个性分析顾问，基于特定交易风格

### 2. 信号模型
- **BacktraderLLMAdvisorSignal**: 基础信号模型（bullish/bearish/neutral/none）
- **BacktraderLLMAdvisorAdvice**: 交易建议模型（buy/sell/close/none）

## 快速开始

### 基本使用示例
```python
import backtrader as bt
from llm_advisory.bt_advisory import BacktraderLLMAdvisory
from llm_advisory.advisors import BacktraderTrendAdvisor

class MyStrategy(bt.Strategy):
    def __init__(self):
        # 创建advisory系统
        self.advisory = BacktraderLLMAdvisory()
        
        # 添加advisors
        trend_advisor = BacktraderTrendAdvisor(
            short_ma_period=10,
            long_ma_period=30,
            lookback_period=15
        )
        self.advisory.add_advisor("trend", trend_advisor)
        
        # 初始化
        self.advisory.init_strategy(self)
    
    def next(self):
        # 生成交易信号
        advisory_result = self._generate_signal()
        signal = advisory_result["signal"]
        
        if signal == "buy" and not self.position:
            self.buy()
        elif signal == "sell" and self.position:
            self.sell()
```

### 高级使用示例：多信号集成
```python
def _generate_composite_signal(self):
    """集成多个advisor的信号"""
    signals = []
    
    # 趋势信号
    trend_signal = self._get_trend_signal()
    signals.append(trend_signal)
    
    # 技术分析信号
    tech_signal = self._get_tech_signal()
    signals.append(tech_signal)
    
    # 信号整合
    return self._combine_signals(signals)

def _combine_signals(self, signals):
    """整合多个信号源"""
    buy_votes = sum(1 for s in signals if s["signal"] == "buy")
    sell_votes = sum(1 for s in signals if s["signal"] == "sell")
    
    if buy_votes > sell_votes:
        avg_confidence = sum(s["confidence"] for s in signals if s["signal"] == "buy") / buy_votes
        return {"signal": "buy", "confidence": avg_confidence}
    elif sell_votes > buy_votes:
        avg_confidence = sum(s["confidence"] for s in signals if s["signal"] == "sell") / sell_votes
        return {"signal": "sell", "confidence": avg_confidence}
    else:
        return {"signal": "none", "confidence": 0.3}
```

## 实战策略模板

### 模板1：基础Advisory策略
```python
class AdvisoryBasicStrategy(bt.Strategy):
    params = (
        ("trade_size", 100),
        ("confidence_threshold", 0.6),
    )
    
    def __init__(self):
        self.advisory = BacktraderLLMAdvisory()
        # ... 添加advisors ...
        
    def _generate_advisory_signal(self):
        """核心信号生成逻辑"""
        # 实现多信号源集成
        pass
        
    def next(self):
        advisory_result = self._generate_advisory_signal()
        if advisory_result["confidence"] > self.params.confidence_threshold:
            self._execute_trade(advisory_result["signal"])
```

### 模板2：带风险管理的Advisory策略
```python
class AdvisoryRiskManagedStrategy(bt.Strategy):
    def __init__(self):
        self.advisory = BacktraderLLMAdvisory()
        # ... 添加advisors ...
        self.risk_manager = RiskManager()
        
    def next(self):
        advisory_result = self._generate_advisory_signal()
        
        # 风险管理检查
        if self.risk_manager.approve_trade(advisory_result):
            self._execute_trade(advisory_result["signal"])
```

## 信号处理最佳实践

### 1. 置信度管理
- 设置置信度阈值（推荐：0.6-0.8）
- 低于阈值时采取观望策略
- 高置信度信号可适当增加仓位

### 2. 信号验证
- 多时间框架确认
- 成交量验证
- 市场环境考量

### 3. 风险管理
- 单次交易风险控制（不超过资本的2%）
- 最大回撤限制
- 连续亏损保护

## 示例文件说明

### 已提供的示例
1. **advisory_trading_strategy.py** - 完整交易策略
   - 集成趋势、RSI、MACD、动量信号
   - 带权重分配的信号组合
   - 完整的回测和分析功能

2. **advisory_signal_demo.py** - 信号生成演示
   - 简化的信号生成流程
   - 信号统计和分析
   - 适合学习和测试

3. **simple_llm_advisory.py** - 基础示例
   - 项目原有的基础示例
   - 展示基本框架

### 运行示例
```bash
# 运行完整策略
python examples/advisory_trading_strategy.py

# 运行信号演示
python examples/advisory_signal_demo.py

# 测试组件
python examples/test_advisory_signal.py
```

## 自定义开发

### 创建自定义Advisor
```python
class MyCustomAdvisor(BacktraderLLMAdvisor):
    def __init__(self, custom_param):
        super().__init__()
        self.custom_param = custom_param
        
    def update_state(self, state):
        # 自定义信号生成逻辑
        pass
```

### 扩展信号模型
```python
class EnhancedSignal(BaseModel):
    signal: Literal["buy", "sell", "hold", "close"]
    confidence: float
    urgency: Literal["high", "medium", "low"]
    timeframe: str  # 信号有效期
```

## 性能优化建议

### 1. 参数调优
- 移动平均线周期
- RSI参数设置
- 置信度阈值

### 2. 信号过滤
- 避免过度交易
- 信号质量评估
- 假信号识别

### 3. 回测验证
- 多市场测试
- 不同周期验证
- 压力测试

## 故障排除

### 常见问题
1. **数据加载失败**: 检查数据源和网络连接
2. **信号不一致**: 检查advisor配置和参数
3. **性能不佳**: 调整信号权重和置信度阈值

### 调试工具
```python
# 启用详细日志
def log_signals(self):
    for advisor in self.advisory.all_advisors:
        print(f"{advisor.advisor_name}: {advisor.current_signal}")
```

## 下一步
1. 运行提供的示例熟悉系统
2. 根据需要定制advisors和信号逻辑
3. 进行充分的回测验证
4. 实盘前的小规模测试

通过这套系统，您可以构建智能化的交易决策框架，结合机器学习与传统技术分析的优势。