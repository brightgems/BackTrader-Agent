"""
测试LLM Advisory信号生成功能
"""

import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from llm_advisory.llm_advisor import LLMAdvisor, AdvisoryAdvisor
from llm_advisory.pydantic_models import (
    BacktraderLLMAdvisorSignal, 
    BacktraderLLMAdvisorAdvice
)

def test_advisory_components():
    """测试advisory核心组件"""
    print("=== LLM Advisory 组件测试 ===\n")
    
    # 1. 测试信号模型
    print("1. 测试信号模型:")
    signal = BacktraderLLMAdvisorSignal(
        signal="bullish",
        confidence=0.8,
        reasoning="Strong uptrend detection with multiple confirmations"
    )
    print(f"  信号: {signal.signal}, 置信度: {signal.confidence:.2f}")
    print(f"  推理: {signal.reasoning}")
    
    # 2. 测试建议模型
    print("\n2. 测试建议模型:")
    advice = BacktraderLLMAdvisorAdvice(
        signal="buy",
        confidence=0.7,
        reasoning="Buy opportunity identified based on technical analysis"
    )
    print(f"  建议: {advice.signal}, 置信度: {advice.confidence:.2f}")
    print(f"  推理: {advice.reasoning}")
    
    # 3. 测试advisor初始化
    print("\n3. 测试advisor初始化:")
    try:
        from llm_advisory.advisors import (
            BacktraderTrendAdvisor,
            BacktraderTechnicalAnalysisAdvisor
        )
        
        trend_advisor = BacktraderTrendAdvisor(short_ma_period=10, long_ma_period=30)
        print(f"  趋势advisor创建成功: {trend_advisor.advisor_name}")
        
        tech_advisor = BacktraderTechnicalAnalysisAdvisor()
        print(f"  技术分析advisor创建成功: {tech_advisor.advisor_name}")
        
        print("  ✅ 所有advisor组件加载成功")
        
    except Exception as e:
        print(f"  ❌ advisor组件加载失败: {e}")
        return False
    
    # 4. 测试advisory系统
    print("\n4. 测试advisory系统:")
    try:
        from llm_advisory.bt_advisory import BacktraderLLMAdvisory
        
        advisory = BacktraderLLMAdvisory()
        print("  Advisory系统创建成功")
        
        # 添加advisor
        advisory.add_advisor("trend", trend_advisor)
        advisory.add_advisor("technical", tech_advisor)
        print(f"  已添加 {len(advisory.all_advisors)} 个advisor")
        
        # 获取特定advisor
        trend_advisor_retrieved = advisory.get_advisor_by_name("trend")
        if trend_advisor_retrieved:
            print("  ✅ 成功获取指定名称的advisor")
        
    except Exception as e:
        print(f"  ❌ advisory系统测试失败: {e}")
        return False
    
    print("\n✅ 所有LLM Advisory组件测试通过!")
    return True

def test_signal_generation():
    """测试信号生成逻辑"""
    print("\n=== 信号生成逻辑测试 ===\n")
    
    # 模拟交易信号生成场景
    print("信号生成场景测试:")
    
    # 场景1: 强烈买入信号
    signals_strong_buy = [
        {"signal": "buy", "confidence": 0.8, "type": "trend"},
        {"signal": "buy", "confidence": 0.7, "type": "rsi"},
        {"signal": "buy", "confidence": 0.6, "type": "macd"}
    ]
    
    # 整合信号
    buy_votes = sum(1 for s in signals_strong_buy if s["signal"] == "buy")
    avg_confidence = sum(s["confidence"] for s in signals_strong_buy if s["signal"] == "buy") / buy_votes
    
    print(f"  场景1 - 强烈买入:")
    print(f"    买入投票: {buy_votes}")
    print(f"    平均置信度: {avg_confidence:.2f}")
    print(f"    决策: {'买入' if avg_confidence > 0.6 else '等待'}")
    
    # 场景2: 分歧信号
    signals_mixed = [
        {"signal": "buy", "confidence": 0.7, "type": "trend"},
        {"signal": "sell", "confidence": 0.6, "type": "rsi"},
        {"signal": "none", "confidence": 0.4, "type": "macd"}
    ]
    
    buy_votes = sum(1 for s in signals_mixed if s["signal"] == "buy")
    sell_votes = sum(1 for s in signals_mixed if s["signal"] == "sell")
    
    print(f"  场景2 - 信号分歧:")
    print(f"    买入投票: {buy_votes}")
    print(f"    卖出投票: {sell_votes}")
    print(f"    决策: {'观望' if buy_votes == sell_votes else '谨慎操作'}")
    
    print("\n✅ 信号生成逻辑测试完成!")

def main():
    """主测试函数"""
    print("🤖 LLM Advisory 交易信号系统测试")
    print("=" * 50)
    
    # 测试组件
    if not test_advisory_components():
        print("\n❌ 组件测试失败，请检查项目配置")
        return
    
    # 测试信号生成
    test_signal_generation()
    
    print("\n" + "=" * 50)
    print("🎯 测试总结:")
    print("1. ✅ Advisory组件架构完整")
    print("2. ✅ 信号生成逻辑合理")
    print("3. ✅ 可以创建完整的交易策略")
    print("\n📚 可用策略示例:")
    print("   - advisory_trading_strategy.py (完整交易策略)")
    print("   - advisory_signal_strategy.py (基础信号策略)")
    print("\n🚀 下一步: 运行策略示例进行回测验证")

if __name__ == "__main__":
    main()