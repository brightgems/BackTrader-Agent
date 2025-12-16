# LLM Advisory 提示词优化实施计划

## 一、问题总结

经过深度分析，已识别出LLM Advisory系统在提示词结构上的核心问题：

### 1.1 信号输出不一致问题
- **格式不统一**：各advisor使用不同的信号输出格式
- **置信度评估标准缺失**：缺乏统一的置信度评分标准
- **趋势强度指标缺失**：只有方向信号，没有强度量化

### 1.2 数据格式混乱问题
- **混合数据格式**：同时使用自定义字典和Markdown表格
- **时间序列表示不一致**：不同advisor使用不同的时间序列格式
- **指标单位不统一**：指标名称和数值格式存在差异

### 1.3 专业化程度不足
- **重复功能**：趋势advisor和反转advisor功能重叠
- **分析框架模糊**：缺乏具体的技术分析指导步骤
- **模式识别标准不明确**：蜡烛图模式识别缺乏标准化

## 二、优化目标

### 2.1 统一信号输出标准
```json
{
    "signal": "bullish/bearish/neutral/none",
    "confidence": 0.0-1.0,
    "trend_strength": "weak/medium/strong",
    "time_frame": "short/medium/long-term",
    "key_levels": ["support_level", "resistance_level"],
    "risk_level": "low/medium/high"
}
```

### 2.2 标准化数据格式
- 统一使用Markdown表格格式
- 标准化的时间序列表示
- 一致的指标命名和单位

### 2.3 专业advisor专业化
- 明确各advisor的独特职责
- 优化特定领域的技术分析框架
- 提供标准化的分析模板

## 三、具体实施步骤

### 3.1 第一阶段：基础框架优化（高优先级）

#### 3.1.1 统一信号模型
**文件**: `llm_advisory/pydantic_models.py`
```python
class EnhancedBacktraderLLMAdvisorSignal(LLMAdvisorSignal):
    signal: Literal["bullish", "bearish", "neutral", "none"]
    confidence: float = Field(ge=0.0, le=1.0)
    trend_strength: Literal["weak", "medium", "strong"] = "medium"
    time_frame: Literal["short", "medium", "long"] = "short"
    key_levels: List[float] = Field(default_factory=list)
    risk_level: Literal["low", "medium", "high"] = "medium"
    reasoning: str
```

#### 3.1.2 优化数据编译函数
**文件**: `llm_advisory/helper/llm_prompt.py`
```python
def compile_data_artefacts_enhanced(data_artefacts: List[LLMAdvisorDataArtefact]) -> str:
    """增强的数据编译函数，统一数据格式"""
    # 实现标准化的Markdown表格转换
```

### 3.2 第二阶段：各advisor专业化优化（中优先级）

#### 3.2.1 趋势advisor优化
**文件**: `llm_advisory/advisors/bt_trend_advisor.py`
- 添加趋势强度量化指标（ADX值、均线角度等）
- 明确定义趋势确认条件
- 优化提示词中的技术分析指导

#### 3.2.2 技术分析advisor优化  
**文件**: `llm_advisory/advisors/bt_technical_analysis_advisor.py`
- 添加多时间框架分析指导
- 明确各指标的权重分配策略
- 提供标准化的分析模板

#### 3.2.3 蜡烛图模式advisor优化
**文件**: `llm_advisory/advisors/bt_candle_pattern_advisor.py`
- 标准化模式名称和定义
- 添加模式匹配度评分标准
- 提供形态确认条件

#### 3.2.4 反转advisor重构
**文件**: `llm_advisory/advisors/bt_reversal_advisor.py`
- 重构为专门的动量反转检测
- 添加反转确认指标（RSI背离、成交量等）
- 明确与趋势advisor的职责区分

### 3.3 第三阶段：高级功能优化（低优先级）

#### 3.3.1 多时间框架整合
- 实现多时间框架信号融合
- 添加趋势一致性检查

#### 3.3.2 风险评估增强
- 添加市场波动率评估
- 实现仓位规模建议

## 四、实施时间表

### 4.1 第一周：基础框架搭建
- 完成信号模型统一
- 实现数据格式标准化
- 创建测试用例

### 4.2 第二周：专业化advisor优化
- 逐个优化各advisor的提示词
- 实现专业化的技术分析框架
- 完成功能测试

### 4.3 第三周：系统集成测试
- 集成所有优化内容
- 进行端到端测试
- 性能优化和问题修复

### 4.4 第四周：文档完善
- 更新使用文档
- 创建配置指南
- 编写最佳实践

## 五、预期效果评估

### 5.1 量化指标
- **信号一致性**：各advisor信号输出格式统一度 > 95%
- **置信度准确性**：置信度评级与实际信号质量相关性 > 0.8
- **响应时间**：平均响应时间增加 < 20%

### 5.2 质量指标
- **可操作性**：交易策略能够直接利用信号的比例 > 90%
- **稳定性**：信号波动率降低 > 30%
- **专业化**：各advisor领域专业性显著提升

## 六、风险与应对

### 6.1 技术风险
- **性能影响**：优化的复杂性可能导致响应时间增加
  - *应对*：分批实施，监控性能指标
- **兼容性**：现有策略可能受到影响
  - *应对*：提供向后兼容选项

### 6.2 质量风险  
- **过度优化**：可能导致模型过拟合
  - *应对*：保持提示词的通用性和适应性
- **复杂性增加**：可能影响使用体验
  - *应对*：提供简化的配置选项

## 七、总结

通过系统性的提示词优化，LLM Advisory系统将能够提供更加清晰、一致和专业的交易信号。该优化计划将从基础框架统一入手，逐步实现各advisor的专业化，最终提升整个系统的决策支持能力。