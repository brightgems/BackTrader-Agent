import os
import backtrader as bt
from datetime import datetime
from llm_advisory.advisors import (
    BacktraderTrendAdvisor, 
    BacktraderTechnicalAnalysisAdvisor,
    BacktraderCandlePatternAdvisor,
    BacktraderFeedbackAdvisor,
    BacktraderPersonaAdvisor
)
from llm_advisory.bt_advisory import BacktraderLLMAdvisory
from utils.fetch_data import get_yfinance_data

class LLMAdvisoryStrategy(bt.Strategy):
    """使用LLM Advisory的交易策略示例"""
    
    params = (
        ("print_advice", True),  # 是否打印建议
        ("lookback_period", 20),  # 数据回溯周期
    )
    
    def log(self, txt, dt=None):
        """日志记录函数"""
        dt = dt or self.datas[0].datetime.date(0)
        print(f"{dt.isoformat()}, {txt}")
    
    def __init__(self):
        # 基本指标
        self.dataclose = self.datas[0].close
        self.sma_fast = bt.indicators.SimpleMovingAverage(self.datas[0], period=10)
        self.sma_slow = bt.indicators.SimpleMovingAverage(self.datas[0], period=30)
        self.rsi = bt.indicators.RSI(self.datas[0], period=14)
        
        self.order = None
        
        # 初始化LLM Advisory
        self.bt_llm_advisory = BacktraderLLMAdvisory()
        
        # 添加多种advisor
        # 1. 趋势advisor
        self.trend_advisor = BacktraderTrendAdvisor(
            short_ma_period=10,
            long_ma_period=25,
            lookback_period=self.params.lookback_period
        )
        self.bt_llm_advisory.add_advisor("trend", self.trend_advisor)
        
        # 2. 技术分析advisor
        self.tech_advisor = BacktraderTechnicalAnalysisAdvisor()
        self.bt_llm_advisory.add_advisor("technical", self.tech_advisor)
        
        # 3. 蜡烛图模式advisor
        self.candle_advisor = BacktraderCandlePatternAdvisor(
            lookback_period=self.params.lookback_period
        )
        self.bt_llm_advisory.add_advisor("candle", self.candle_advisor)
        
        # # 4. 反馈advisor
        # self.feedback_advisor = BacktraderFeedbackAdvisor()
        # self.bt_llm_advisory.add_advisor("feedback", self.feedback_advisor)
        
        # # 5. 个性化advisor（交易专家角色）
        # self.persona_advisor = BacktraderPersonaAdvisor(
        #     person_name="Professional Trader",
        #     personality="你是一名经验丰富的专业交易员，擅长技术分析和风险管理"
        # )
        # self.bt_llm_advisory.add_advisor("persona", self.persona_advisor)
        
        # 初始化策略
        self.bt_llm_advisory.init_strategy(
            self, 
            data_lookback_period=self.params.lookback_period,
            indicator_lookback_period=self.params.lookback_period
        )
        
        # 存储advisor建议
        self.advice_history = []
    
    def notify_order(self, order):
        """订单状态通知"""
        if order.status in [order.Submitted, order.Accepted]:
            return
        
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(f"买入执行: 价格 {order.executed.price:.2f}, 价值 {order.executed.value:.2f}")
            else:
                self.log(f"卖出执行: 价格 {order.executed.price:.2f}, 价值 {order.executed.value:.2f}")
        
        self.order = None
    
    def get_consensus_signal(self, advice_results):
        """综合所有advisor的建议生成共识信号"""
        bullish_count = 0
        bearish_count = 0
        neutral_count = 0
        
        for advisor_name, advice in advice_results.items():
            signal = advice.get("signal", "none")
            if signal == "bullish":
                bullish_count += 1
            elif signal == "bearish":
                bearish_count += 1
            else:
                neutral_count += 1
        
        # 简单多数投票
        if bullish_count > bearish_count and bullish_count > neutral_count:
            return "bullish"
        elif bearish_count > bullish_count and bearish_count > neutral_count:
            return "bearish"
        else:
            return "neutral"
    
    def next(self):
        """主要交易逻辑"""
        if self.order:
            return
        
        # 获取所有advisor的建议
        advice_results = {}
        for advisor_name in ["trend", "technical", "candle", "persona"]:
            try:
                advice = self.bt_llm_advisory.get_advice(advisor_name)
                advice_results[advisor_name] = advice
                
                if self.params.print_advice:
                    self.log(f"{advisor_name}建议: {advice.get('signal', 'none')} - {advice.get('reasoning', '')}")
                    
            except Exception as e:
                self.log(f"获取{advisor_name}建议失败: {str(e)}")
        
        # 存储建议历史
        self.advice_history.append({
            'date': self.datas[0].datetime.date(0),
            'advice': advice_results
        })
        
        # 基于共识信号进行交易
        consensus_signal = self.get_consensus_signal(advice_results)
        
        # 交易逻辑
        if consensus_signal == "bullish" and not self.position:
            # 买入条件：至少2个advisor给出买入信号且技术指标支持
            bullish_advisors = sum(1 for a in advice_results.values() if a.get("signal") == "bullish")
            if bullish_advisors >= 2 and self.sma_fast[0] > self.sma_slow[0] and self.rsi[0] < 70:
                self.order = self.buy()
                self.log(f"基于LLM建议买入，共识信号: {consensus_signal}")
                
        elif consensus_signal == "bearish" and self.position:
            # 卖出条件：至少2个advisor给出卖出信号
            bearish_advisors = sum(1 for a in advice_results.values() if a.get("signal") == "bearish")
            if bearish_advisors >= 2:
                self.order = self.sell()
                self.log(f"基于LLM建议卖出，共识信号: {consensus_signal}")
    
    def stop(self):
        """策略结束时的分析"""
        self.log(f"最终资产: {self.broker.getvalue():.2f}")
        
        # 输出advisor建议统计
        advice_stats = {}
        for entry in self.advice_history:
            for advisor, advice in entry['advice'].items():
                if advisor not in advice_stats:
                    advice_stats[advisor] = {'bullish': 0, 'bearish': 0, 'neutral': 0}
                signal = advice.get('signal', 'neutral')
                advice_stats[advisor][signal] += 1
        
        self.log("advisor建议统计:")
        for advisor, stats in advice_stats.items():
            self.log(f"  {advisor}: bullish={stats['bullish']}, bearish={stats['bearish']}, neutral={stats['neutral']}")


def run_llm_advisory_backtest():
    """运行LLM Advisory回测"""
    print("启动LLM Advisory回测...")
    
    # 创建Cerebro引擎
    cerebro = bt.Cerebro()
    
    # 设置初始资金
    cerebro.broker.setcash(100000.0)
    cerebro.broker.setcommission(commission=0.001)
    
    # 添加数据
    symbol = 'AAPL'  # 使用苹果股票作为示例
    start_date = datetime(2023, 1, 1)
    end_date = datetime(2023, 12, 31)
    
    print(f"获取 {symbol} 数据...")
    data = get_yfinance_data(symbol, start_date, end_date)
    cerebro.adddata(data)
    
    # 添加策略
    cerebro.addstrategy(LLMAdvisoryStrategy, print_advice=True, lookback_period=20)
    
    # 添加分析器
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name="sharpe")
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name="drawdown")
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name="trades")
    
    # 运行回测
    print("运行回测...")
    results = cerebro.run()
    
    # 输出结果
    strat = results[0]
    print(f"\n回测结果:")
    print(f"起始资金: 100,000.00")
    print(f"最终资产: {cerebro.broker.getvalue():.2f}")
    print(f"收益率: {(cerebro.broker.getvalue() - 100000) / 100000 * 100:.2f}%")
    
    # 分析器结果
    sharpe = strat.analyzers.sharpe.get_analysis()
    drawdown = strat.analyzers.drawdown.get_analysis()
    trades = strat.analyzers.trades.get_analysis()
    
    print(f"夏普比率: {sharpe.get('sharperatio', 'N/A'):.2f}")
    print(f"最大回撤: {drawdown.get('max', {}).get('drawdown', 'N/A'):.2f}%")
    print(f"总交易次数: {trades.get('total', {}).get('total', 0)}")
    
    # 绘制图表
    cerebro.plot(style='candle')


if __name__ == "__main__":
    print("LLM Advisory 交易示例")
    print("注意: 运行前请确保设置正确的OpenAI API密钥")
    
    # 运行回测
    run_llm_advisory_backtest()