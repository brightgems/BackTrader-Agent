"""
Ollama Advisory 示例
使用本地 Ollama 模型进行交易决策
"""

import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import backtrader as bt
from datetime import datetime
from llm_advisory.advisors import (
    BacktraderTrendAdvisor, 
    BacktraderTechnicalAnalysisAdvisor,
    BacktraderCandlePatternAdvisor,
    BacktraderPersonaAdvisor
)
from llm_advisory.bt_advisory import BacktraderLLMAdvisory
from llm_advisory.llm_advisor import check_llm_service_availability
from utils.fetch_data import get_yfinance_data


def setup_ollama_environment():
    """设置和检查 Ollama 环境"""
    print("=== Ollama 环境检查 ===")
    
    # 检查 LLM 服务可用性
    service_status = check_llm_service_availability("ollama")
    
    if service_status["available"]:
        print(f"✅ {service_status['details']['status']}")
        print(f"可用提供商: {', '.join(service_status['available_providers'])}")
    else:
        print("❌ Ollama 服务不可用")
        print(f"错误信息: {service_status['details'].get('error', '未知错误')}")
        print("\n请确保:")
        print("1. 已安装 Ollama: https://ollama.ai")
        print("2. 已下载模型: ollama pull qwen3-vl")
        print("3. Ollama 服务正在运行")
        return False
    
    return True


class OllamaAdvisoryStrategy(bt.Strategy):
    """使用 Ollama 本地模型的交易策略"""
    
    params = (
        ("print_advice", True),
        ("lookback_period", 15),
        ("provider", "ollama"),  # 指定使用 ollama
        ("model", os.getenv('OLLAMA_MODEL', "qwen3-vl")),     # 指定模型
    )
    
    def log(self, txt, dt=None):
        """日志记录函数"""
        if self.params.print_advice:
            dt = dt or self.datas[0].datetime.date(0)
            print(f"{dt.isoformat()}, {txt}")
    
    def __init__(self):
        # 基本指标
        self.dataclose = self.datas[0].close
        self.sma_fast = bt.indicators.SimpleMovingAverage(self.datas[0], period=10)
        self.sma_slow = bt.indicators.SimpleMovingAverage(self.datas[0], period=30)
        self.rsi = bt.indicators.RSI(self.datas[0], period=14)
        
        self.order = None
        
        # 初始化 LLM Advisory，指定使用 Ollama
        self.bt_llm_advisory = BacktraderLLMAdvisory(
            api_key="not-required",  # Ollama 不需要 API 密钥
            base_url="http://localhost:11434",  # Ollama 默认地址
            model=os.getenv('OLLAMA_MODEL', "qwen3-vl") 
        )
        
        # 添加多种 advisor，明确指定使用 Ollama
        # 1. 趋势 advisor
        self.trend_advisor = BacktraderTrendAdvisor(
            short_ma_period=10,
            long_ma_period=25,
            lookback_period=self.params.lookback_period
        )
        self.bt_llm_advisory.add_advisor("trend", self.trend_advisor)
        
        # 2. 技术分析 advisor
        self.tech_advisor = BacktraderTechnicalAnalysisAdvisor()
        self.bt_llm_advisory.add_advisor("technical", self.tech_advisor)
        
        # 3. 蜡烛图模式 advisor
        self.candle_advisor = BacktraderCandlePatternAdvisor(
            lookback_period=self.params.lookback_period
        )
        self.bt_llm_advisory.add_advisor("candle", self.candle_advisor)
        
        # 4. 个性化 advisor（本地专家角色）
        self.persona_advisor = BacktraderPersonaAdvisor(
            person_name="本地量化交易专家",
            personality="""你是一名本地部署的量化交易专家，专门分析股票市场。
            基于提供的技术指标和价格数据，给出明确的交易建议。
            考虑趋势、支撑阻力位、成交量等因素。
            给出: bullish(看涨), bearish(看跌), neutral(中性) 或 none(无法判断) 的信号。""",
            provider=self.params.provider,
            model=self.params.model
        )
        self.bt_llm_advisory.add_advisor("persona", self.persona_advisor)
        
        # 初始化策略
        self.bt_llm_advisory.init_strategy(
            self, 
            data_lookback_period=self.params.lookback_period,
            indicator_lookback_period=self.params.lookback_period
        )
        
        # 存储建议历史
        self.advice_history = []
        
        self.log(f"策略初始化完成，使用 {self.params.provider} 服务")
    
    def notify_order(self, order):
        """订单状态通知"""
        if order.status in [order.Submitted, order.Accepted]:
            return
        
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(f"买入执行: 价格 {order.executed.price:.2f}")
            else:
                self.log(f"卖出执行: 价格 {order.executed.price:.2f}")
        
        self.order = None
    
    def get_llm_advice(self):
        """获取 LLM 建议"""
        advice_results = {}
        
        for advisor_name in ["trend", "technical", "candle", "persona"]:
            try:
                advice = self.bt_llm_advisory.get_advice(advisor_name)
                advice_results[advisor_name] = advice
                
                if self.params.print_advice:
                    signal = advice.get('signal', 'none')
                    reasoning = advice.get('reasoning', '')[:100] + "..." if len(advice.get('reasoning', '')) > 100 else advice.get('reasoning', '')
                    self.log(f"{advisor_name}: {signal} - {reasoning}")
                    
            except Exception as e:
                self.log(f"获取 {advisor_name} 建议失败: {str(e)}")
                advice_results[advisor_name] = {"signal": "none", "reasoning": f"错误: {str(e)}"}
        
        return advice_results
    
    def next(self):
        """主要交易逻辑"""
        if self.order:
            return
        
        # 获取 LLM 建议
        advice_results = self.get_llm_advice()
        
        # 存储建议历史
        self.advice_history.append({
            'date': self.datas[0].datetime.date(0),
            'advice': advice_results
        })
        
        # 简单的决策逻辑（演示用）
        # 在实际使用中，这里应该更复杂地分析 LLM 建议
        bullish_count = sum(1 for a in advice_results.values() if a.get("signal") == "bullish")
        bearish_count = sum(1 for a in advice_results.values() if a.get("signal") == "bearish")
        
        # 交易逻辑
        if bullish_count >= 2 and not self.position and self.sma_fast[0] > self.sma_slow[0]:
            # 买入条件：至少2个看涨建议，且技术指标支持
            self.order = self.buy()
            self.log(f"基于 LLM 建议买入 - 看涨建议数: {bullish_count}")
            
        elif bearish_count >= 2 and self.position:
            # 卖出条件：至少2个看跌建议
            self.order = self.sell()
            self.log(f"基于 LLM 建议卖出 - 看跌建议数: {bearish_count}")
    
    def stop(self):
        """策略结束时的分析"""
        final_value = self.broker.getvalue()
        initial_cash = self.broker.startingcash
        roi = (final_value - initial_cash) / initial_cash * 100
        
        self.log(f"策略结束")
        self.log(f"初始资金: {initial_cash:.2f}")
        self.log(f"最终资产: {final_value:.2f}")
        self.log(f"收益率: {roi:.2f}%")
        
        # 统计建议分布
        if self.advice_history:
            stats = {"bullish": 0, "bearish": 0, "neutral": 0, "none": 0}
            for entry in self.advice_history:
                for advisor_advice in entry['advice'].values():
                    signal = advisor_advice.get('signal', 'none')
                    if signal in stats:
                        stats[signal] += 1
            
            self.log("建议统计:")
            for signal, count in stats.items():
                percentage = (count / (len(self.advice_history) * 4)) * 100
                self.log(f"  {signal}: {count}次 ({percentage:.1f}%)")


def run_ollama_backtest():
    """运行 Ollama 回测"""
    print("=== Ollama Advisory 回测演示 ===")
    
    # 检查环境
    if not setup_ollama_environment():
        print("环境检查失败，使用模拟模式运行演示")
        return run_demo_mode()
    
    cerebro = bt.Cerebro()
    
    # 基本设置
    initial_cash = 50000.0
    cerebro.broker.setcash(initial_cash)
    cerebro.broker.setcommission(0.001)
    
    # 添加数据（使用较短的时间范围用于演示）
    symbol = '000001.SZ'  # 平安银行
    start_date = datetime(2023, 9, 1)
    end_date = datetime(2023, 11, 30)
    
    print(f"获取 {symbol} 数据...")
    data = get_yfinance_data(symbol, start_date, end_date)
    cerebro.adddata(data)
    
    # 添加策略
    cerebro.addstrategy(OllamaAdvisoryStrategy, print_advice=True)
    
    # 添加分析器
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name="sharpe")
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name="drawdown")
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name="trades")
    
    # 运行回测
    print("运行 Ollama 回测...")
    results = cerebro.run()
    
    # 输出结果
    strat = results[0]
    print(f"\n回测结果:")
    print(f"起始资金: {initial_cash:,.2f}")
    print(f"最终资产: {cerebro.broker.getvalue():,.2f}")
    
    # 简单绘图
    print("生成回测图表...")
    cerebro.plot(style='line')


def run_demo_mode():
    """演示模式 - 没有真实 Ollama 服务时的演示"""
    print("=== 演示模式 (无真实 Ollama 服务) ===")
    print("此模式展示代码逻辑，但不会调用真实的 LLM 服务")
    
    cerebro = bt.Cerebro()
    cerebro.broker.setcash(50000.0)
    cerebro.broker.setcommission(0.001)
    
    # 添加测试数据
    symbol = '000001.SZ'
    start_date = datetime(2023, 9, 1)
    end_date = datetime(2023, 9, 30)  # 更短的时间用于演示
    
    print(f"获取 {symbol} 数据...")
    data = get_yfinance_data(symbol, start_date, end_date)
    cerebro.adddata(data)
    
    # 使用简化策略演示
    cerebro.addstrategy(OllamaAdvisoryStrategy, print_advice=False)
    
    results = cerebro.run()
    
    print("演示完成！")
    print("要使用真实 Ollama 服务，请:")
    print("1. 安装 Ollama: https://ollama.ai")
    print("2. 下载模型: ollama pull qwen3-vl")
    print("3. 确保 Ollama 服务运行")


if __name__ == "__main__":
    print("Ollama Advisory 示例")
    print("=" * 50)
    
    try:
        run_ollama_backtest()
    except Exception as e:
        print(f"回测过程中出现错误: {e}")
        print("切换到演示模式...")
        run_demo_mode()