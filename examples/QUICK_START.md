# LLM Advisory 快速开始指南

## 概述

Backtrader LLM Advisory 是一个强大的工具，允许你在 backtrader 交易策略中集成 AI 建议。通过使用不同的 advisor，你可以获得趋势分析、技术分析、蜡烛图模式识别等 AI 驱动的交易建议。

## 快速开始

### 1. 安装依赖

确保已安装所有必要的依赖：
```bash
pip install -r requirements.txt
```

### 2. 获取 API 密钥

要使用真实的 LLM 功能，你需要获取 API 密钥：
- **OpenAI**: 访问 [OpenAI Platform](https://platform.openai.com) 获取 API 密钥
- **本地部署**: 使用 Ollama 等工具在本地部署 LLM

### 3. 基础使用示例

查看以下示例了解基本用法：

#### 简单示例 (不需要真实 API)
```bash
python examples/simple_llm_advisory.py
```

#### 完整示例 (需要 API 密钥)
```bash
# 首先修改 examples/llm_advisory_example.py 中的 API 密钥
python examples/llm_advisory_example.py
```

## Advisor 类型

### 趋势分析 Advisor (BacktraderTrendAdvisor)
- 识别市场趋势（看涨/看跌/中性）
- 基于移动平均线交叉等指标
- 可配置回溯周期

### 技术分析 Advisor (BacktraderTechnicalAnalysisAdvisor)
- 分析技术指标（RSI、MACD 等）
- 提供交易信号
- 解释指标含义

### 蜡烛图模式 Advisor (BacktraderCandlePatternAdvisor)
- 识别常见的蜡烛图模式
- 提供模式识别信号
- 包含模式解释

### 个性化 Advisor (BacktraderPersonaAdvisor)
- 可定义特定交易角色
- 基于特定知识领域提供建议
- 支持自定义个性描述

## 集成到现有策略

### 步骤 1: 导入必要模块
```python
from llm_advisory.bt_advisory import BacktraderLLMAdvisory
from llm_advisory.advisors import BacktraderTrendAdvisor, BacktraderTechnicalAnalysisAdvisor
```

### 步骤 2: 在 __init__ 中初始化
```python
def __init__(self):
    # 基础指标...
    
    # 初始化 LLM Advisory
    self.advisory = BacktraderLLMAdvisory(
        api_key="your_api_key",
        base_url="https://api.openai.com/v1",
        model="gpt-4"
    )
    
    # 添加 advisors
    self.trend_advisor = BacktraderTrendAdvisor()
    self.advisory.add_advisor("trend", self.trend_advisor)
    
    # 初始化策略
    self.advisory.init_strategy(self)
```

### 步骤 3: 在 next 方法中使用建议
```python
def next(self):
    # 获取建议
    trend_advice = self.advisory.get_advice("trend")
    
    # 基于建议进行交易
    if trend_advice.get("signal") == "bullish" and not self.position:
        self.buy()
    elif trend_advice.get("signal") == "bearish" and self.position:
        self.sell()
```

## 配置建议

### API 配置
- **开发阶段**: 使用 GPT-3.5-turbo 降低成本
- **生产环境**: 使用 GPT-4 获得更好的分析质量
- **预算控制**: 设置合理的 max_tokens 限制

### 参数调优
```python
# 趋势advisor参数
trend_advisor = BacktraderTrendAdvisor(
    short_ma_period=10,      # 短期均线周期
    long_ma_period=25,       # 长期均线周期  
    lookback_period=20,      # 数据回溯周期
    add_all_data_feeds=False # 是否包含所有数据
)
```

## 故障排除

### 常见问题

1. **API 密钥错误**
   - 检查 API 密钥是否正确
   - 确认账户余额充足

2. **网络连接问题**
   - 检查网络连接
   - 验证 API 端点可达性

3. **建议质量不佳**
   - 调整 advisor 参数
   - 尝试不同的 LLM 模型
   - 增加回溯数据周期

### 调试技巧

启用详细日志记录：
```python
class MyStrategy(bt.Strategy):
    params = (("print_advice", True),)
    
    def next(self):
        advice = self.advisory.get_advice("trend")
        if self.params.print_advice:
            print(f"建议: {advice}")
```

## 最佳实践

1. **组合多个 Advisor**: 使用多个 advisor 的建议进行综合判断
2. **风险管理**: 不要完全依赖 AI 建议，结合传统风控
3. **回测验证**: 在使用前进行充分回测
4. **成本控制**: 监控 API 使用成本
5. **持续优化**: 根据市场变化调整 advisor 参数

## 示例策略

项目包含完整的示例策略：
- `examples/llm_advisory_example.py` - 完整功能演示
- `examples/simple_llm_advisory.py` - 基础用法演示
- `examples/config_example.py` - 配置参考

## 支持与贡献

如需帮助或想要贡献代码，请参考项目文档或联系开发团队。