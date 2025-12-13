import backtrader as bt
from datetime import datetime
from llm_advisory.bt_advisory import BacktraderLLMAdvisory
from llm_advisory.advisors import (
    BacktraderTrendAdvisor,
    BacktraderTechnicalAnalysisAdvisor
)
from utils.fetch_data import get_yfinance_data

class SimpleLLMStrategy(bt.Strategy):
    """简单的LLM Advisory示例策略"""
    
    params = (
        ("print_log", True),
    )
    
    def log(self, txt, dt=None):
        """日志记录"""
        if self.params.print_log:
            dt = dt or self.datas[0].datetime.date(0)
            print(f"{dt.isoformat()}, {txt}")
    
    def __init__(self):
        # 基本指标
        self.dataclose = self.datas[0].close
        self.sma = bt.indicators.SimpleMovingAverage(self.datas[0], period=20)
        
        self.order = None
        
        # 创建LLM Advisory（不使用真实API密钥的演示版本）
        self.advisory = BacktraderLLMAdvisory(
            api_key="demo_key",  # 演示用密钥
            base_url="http://localhost:8000",  # 本地模拟API
            model="gpt-3.5-turbo"  # 模拟模型
        )
        
        # 添加趋势advisor
        self.trend_advisor = BacktraderTrendAdvisor(
            short_ma_period=10,
            long_ma_period=30,
            lookback_period=15
        )
        self.advisory.add_advisor("trend", self.trend_advisor)
        
        # 添加技术分析advisor
        self.tech_advisor = BacktraderTechnicalAnalysisAdvisor()
        self.advisory.add_advisor("technical", self.tech_advisor)
        
        # 初始化
        self.advisory.init_strategy(self)
        
        # 交易计数器
        self.trade_count = 0
        
    def notify_order(self, order):
        """订单处理"""
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(f"买入成交 - 价格: {order.executed.price:.2f}")
            else:
                self.log(f"卖出成交 - 价格: {order.executed.price:.2f}")
            self.trade_count += 1
        self.order = None
    
    def next(self):
        """交易逻辑"""
        if self.order:
            return
        
        # 基础交易逻辑（不依赖LLM，用于演示）
        if not self.position:
            if self.dataclose[0] > self.sma[0]:
                self.order = self.buy()
                self.log(f"基于基础策略买入 - 价格: {self.dataclose[0]:.2f}")
        else:
            if self.dataclose[0] < self.sma[0]:
                self.order = self.sell()
                self.log(f"基于基础策略卖出 - 价格: {self.dataclose[0]:.2f}")
        
        # 演示：记录一些基本指标状态（模拟LLM分析）
        if len(self) % 10 == 0:  # 每10个bar记录一次
            trend_status = "上升" if self.dataclose[0] > self.sma[0] else "下降"
            self.log(f"趋势状态: {trend_status}, 价格: {self.dataclose[0]:.2f}, SMA: {self.sma[0]:.2f}")
    
    def stop(self):
        """结束时的统计"""
        self.log(f"策略结束 - 最终资产: {self.broker.getvalue():.2f}")
        self.log(f"总交易次数: {self.trade_count}")

def demo_llm_advisory():
    """演示LLM Advisory基本用法"""
    print("=== LLM Advisory 基础演示 ===")
    
    cerebro = bt.Cerebro()
    
    # 基本设置
    cerebro.broker.setcash(50000.0)
    cerebro.broker.setcommission(0.001)
    
    # 添加数据（使用较短的时间范围用于演示）
    symbol = '000001.SZ'  # 平安银行
    start_date = datetime(2023, 6, 1)
    end_date = datetime(2023, 8, 31)
    
    print(f"获取 {symbol} 数据...")
    data = get_yfinance_data(symbol, start_date, end_date)
    cerebro.adddata(data)
    
    # 添加策略
    cerebro.addstrategy(SimpleLLMStrategy)
    
    # 运行回测
    print("运行演示回测...")
    results = cerebro.run()
    
    # 基本结果
    final_value = cerebro.broker.getvalue()
    roi = (final_value - 50000) / 50000 * 100
    
    print(f"\n演示结果:")
    print(f"起始资金: 50,000.00")
    print(f"最终资产: {final_value:.2f}")
    print(f"收益率: {roi:.2f}%")
    
    # 简单绘图
    cerebro.plot(style='line')

if __name__ == "__main__":
    demo_llm_advisory()