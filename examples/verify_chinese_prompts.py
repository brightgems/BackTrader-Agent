"""验证LLM Advisor中文提示词转换效果"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from llm_advisory.advisors import (
    BacktraderTrendAdvisor,
    BacktraderTechnicalAnalysisAdvisor,
    BacktraderCandlePatternAdvisor
)

def verify_chinese_prompts():
    """验证所有advisor已成功转换为中文提示词"""
    
    print("=== LLM Advisor 中文提示词验证 ===\n")
    
    # 趋势advisor验证
    trend = BacktraderTrendAdvisor()
    trend_chinese = "趋势判断标准" in trend.advisor_instructions
    trend_english = "bullish" in trend.advisor_instructions and "bearish" in trend.advisor_instructions
    
    # 技术分析advisor验证
    tech = BacktraderTechnicalAnalysisAdvisor()
    tech_chinese = "分析框架" in tech.advisor_instructions
    tech_english = "bullish" in tech.advisor_instructions and "bearish" in tech.advisor_instructions
    
    # 蜡烛图advisor验证
    candle = BacktraderCandlePatternAdvisor()
    candle_chinese = "蜡烛图模式标准" in candle.advisor_instructions
    candle_english = "bullish" in candle.advisor_instructions and "bearish" in candle.advisor_instructions
    
    print("🔍 验证结果:")
    print("-" * 50)
    
    print("1. 趋势Advisor:")
    print(f"   中文提示词: {'✓' if trend_chinese else '✗'}")
    print(f"   英文信号保留: {'✓' if trend_english else '✗'}")
    
    print("2. 技术分析Advisor:")
    print(f"   中文提示词: {'✓' if tech_chinese else '✗'}")
    print(f"   英文信号保留: {'✓' if tech_english else '✗'}")
    
    print("3. 蜡烛图Advisor:")
    print(f"   中文提示词: {'✓' if candle_chinese else '✗'}")
    print(f"   英文信号保留: {'✓' if candle_english else '✗'}")
    
    print("-" * 50)
    
    # 样本输出预览
    print("\n📊 样本输出结构预览:")
    print("""
**1. 模式识别**
Pattern: BULLISH - 看涨吞没

**2. 交易信号**  
Signal: bullish
Confidence: 0.85
Trend Context: 上升趋势
    """)
    
    # 最终验证结果
    all_chinese = trend_chinese and tech_chinese and candle_chinese
    all_english_signals = trend_english and tech_english and candle_english
    
    if all_chinese and all_english_signals:
        print("🎯 验证成功！")
        print("• 所有advisor提示词已转换为中文")
        print("• 交易信号保持英文格式 (bullish/bearish等)")
        print("• 现在可以运行 examples/openai_advisory_example.py 测试实际效果")
        return True
    else:
        print("⚠️ 验证发现问题，请重新检查提示词转换")
        return False

if __name__ == "__main__":
    verify_chinese_prompts()