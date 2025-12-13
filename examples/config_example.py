"""
LLM Advisory 配置示例
快速设置和使用说明
"""

# OpenAI API 配置示例
OPENAI_CONFIG = {
    "api_key": "your_openai_api_key_here",  # 替换为您的OpenAI API密钥
    "base_url": "https://api.openai.com/v1",
    "model": "gpt-4",  # 或 "gpt-3.5-turbo" 用于成本优化
    "temperature": 0.7,
    "max_tokens": 500
}

# 本地LLM配置示例（如使用Ollama等本地部署）
LOCAL_LLM_CONFIG = {
    "api_key": "not-required",  # 本地部署可能不需要API密钥
    "base_url": "http://localhost:11434/v1",  # Ollama默认地址
    "model": "llama2",  # 或其他本地模型
    "temperature": 0.7,
    "max_tokens": 500
}

# Advisor 配置示例
ADVISOR_CONFIGS = {
    "trend_advisor": {
        "class": "BacktraderTrendAdvisor",
        "params": {
            "short_ma_period": 10,
            "long_ma_period": 25,
            "lookback_period": 20,
            "add_all_data_feeds": False
        }
    },
    "tech_advisor": {
        "class": "BacktraderTechnicalAnalysisAdvisor",
        "params": {}
    },
    "candle_advisor": {
        "class": "BacktraderCandlePatternAdvisor",
        "params": {
            "lookback_period": 10,
            "add_all_data_feeds": False
        }
    },
    "persona_advisor": {
        "class": "BacktraderPersonaAdvisor",
        "params": {
            "person_name": "专业交易员",
            "personality": "你是一名经验丰富的量化交易专家，擅长技术分析和风险管理"
        }
    }
}

def create_advisory_setup(strategy, config_name="openai"):
    """快速创建LLM Advisory配置"""
    
    if config_name == "openai":
        llm_config = OPENAI_CONFIG
    else:
        llm_config = LOCAL_LLM_CONFIG
    
    from llm_advisory.bt_advisory import BacktraderLLMAdvisory
    from llm_advisory.advisors import (
        BacktraderTrendAdvisor,
        BacktraderTechnicalAnalysisAdvisor,
        BacktraderCandlePatternAdvisor,
        BacktraderPersonaAdvisor
    )
    
    # 创建advisory实例
    advisory = BacktraderLLMAdvisory(
        api_key=llm_config["api_key"],
        base_url=llm_config["base_url"],
        model=llm_config["model"]
    )
    
    # 添加advisors
    trend_config = ADVISOR_CONFIGS["trend_advisor"]
    trend_advisor = BacktraderTrendAdvisor(**trend_config["params"])
    advisory.add_advisor("trend", trend_advisor)
    
    tech_config = ADVISOR_CONFIGS["tech_advisor"]
    tech_advisor = BacktraderTechnicalAnalysisAdvisor(**tech_config["params"])
    advisory.add_advisor("technical", tech_advisor)
    
    candle_config = ADVISOR_CONFIGS["candle_advisor"]
    candle_advisor = BacktraderCandlePatternAdvisor(**candle_config["params"])
    advisory.add_advisor("candle", candle_advisor)
    
    persona_config = ADVISOR_CONFIGS["persona_advisor"]
    persona_advisor = BacktraderPersonaAdvisor(**persona_config["params"])
    advisory.add_advisor("persona", persona_advisor)
    
    # 初始化
    advisory.init_strategy(strategy)
    
    return advisory

if __name__ == "__main__":
    print("LLM Advisory 配置示例")
    print("复制此配置到您的策略中，并替换相应的API密钥")
    print("使用示例:")
    print("1. 在策略的 __init__ 方法中调用 create_advisory_setup(self)")
    print("2. 在 next 方法中调用 advisory.get_advice('advisor_name') 获取建议")
    print("3. 根据建议制定交易决策")