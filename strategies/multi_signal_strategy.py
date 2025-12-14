import os
import backtrader as bt
from datetime import datetime
import sys

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.fetch_data import get_yfinance_data


class AdvisorySignalStrategy(bt.Strategy):
    """基于LLM Advisory信号的全新交易策略"""
    
    params = (
        ("print_log", True),
        ("broker_starting_cash", 10000),  # 每次交易股数
        # 趋势指标参数
        ("trend_short_ma_period", 10),    # 短期移动平均线周期
        ("trend_long_ma_period", 30),     # 长期移动平均线周期
        ("trend_lookback_period", 20),    # 趋势回看周期
        # RSI指标参数
        ("rsi_period", 14),               # RSI周期
        ("rsi_oversold", 30),             # 超卖阈值
        ("rsi_overbought", 70),           # 超买阈值
    )
    
    def log(self, txt, dt=None):
        """日志记录"""
        if self.params.print_log:
            dt = dt or self.datas[0].datetime.date(0)
            print(f"{dt.isoformat()}, {txt}")
    
    def __init__(self):
        # 跟踪订单状态
        self.order = None
        self.last_advisory_signal = "none"
        self.last_confidence = 0.0
        
        # 性能统计
        self.trade_count = 0
        self.total_confidence = 0.0
        
        # 初始化指标（避免每次调用都重新创建）
        self.ma_short_indicator = bt.ind.SMA(self.datas[0], period=self.params.trend_short_ma_period)
        self.ma_long_indicator = bt.ind.SMA(self.datas[0], period=self.params.trend_long_ma_period)
        self.rsi_indicator = bt.ind.RSI(self.datas[0], period=self.params.rsi_period)
        
    def notify_order(self, order):
        """订单处理"""
        if order.status in [order.Submitted, order.Accepted]:
            return  # 订单已提交或接受，无需操作
        
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(f"多头信号 - 买入成交: {order.executed.price:.2f}, 数量: {order.executed.size}")
                self.log(f"Advisory信号: {self.last_advisory_signal}, 置信度: {self.last_confidence:.2f}")
            else:
                self.log(f"空头信号 - 卖出成交: {order.executed.price:.2f}, 数量: {order.executed.size}")
                self.log(f"Advisory信号: {self.last_advisory_signal}, 置信度: {self.last_confidence:.2f}")
            
            self.trade_count += 1
            self.total_confidence += self.last_confidence
            
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log(f"订单失败: {order.status}")
            
        self.order = None
    
    def _get_advisory_signal(self):
        """获取advisory系统的综合信号"""
        # 模拟调用advisory系统获取信号
        # 在实际应用中，这里会调用advisory的update_state方法
        current_price = self.datas[0].close[0]
        
        # 模拟多个advisor的信号整合
        trend_signal = self._get_trend_advisory_signal()
        tech_signal = self._get_tech_advisory_signal()
        reversal_signal = self._get_reversal_advisory_signal()
        
        # 简单的信号聚合逻辑
        signals = [trend_signal, tech_signal, reversal_signal]
        buy_signals = sum(1 for s in signals if s["signal"] == "buy")
        sell_signals = sum(1 for s in signals if s["signal"] == "sell")
        
        if buy_signals > sell_signals and buy_signals >= 2:
            final_signal = "buy"
            confidence = sum(s["confidence"] for s in signals if s["signal"] == "buy") / buy_signals
        elif sell_signals > buy_signals and sell_signals >= 2:
            final_signal = "sell"
            confidence = sum(s["confidence"] for s in signals if s["signal"] == "sell") / sell_signals
        else:
            final_signal = "none"
            confidence = 0.0
            
        return {"signal": final_signal, "confidence": confidence}
    
    def _get_trend_advisory_signal(self):
        """模拟趋势advisor信号"""
        # 使用移动平均线判断趋势
        if len(self.datas[0]) < self.params.trend_long_ma_period:
            return {"signal": "none", "confidence": 0.0}
            
        price = self.datas[0].close[0]
        
        if len(self.ma_short_indicator) < 1 or len(self.ma_long_indicator) < 1:
            return {"signal": "none", "confidence": 0.0}
            
        ma_short = self.ma_short_indicator[0]
        ma_long = self.ma_long_indicator[0]
        
        # 简单的趋势判断逻辑
        if price > ma_short > ma_long:
            return {"signal": "buy", "confidence": 0.7}
        elif price < ma_short < ma_long:
            return {"signal": "sell", "confidence": 0.7}
        else:
            return {"signal": "none", "confidence": 0.3}
    
    def _get_tech_advisory_signal(self):
        """模拟技术分析advisor信号"""
        if len(self.datas[0]) < self.params.rsi_period:
            return {"signal": "none", "confidence": 0.0}
            
        if len(self.rsi_indicator) < 1:
            return {"signal": "none", "confidence": 0.0}
            
        rsi = self.rsi_indicator[0]
        
        if rsi < self.params.rsi_oversold:  # 超卖区域
            return {"signal": "buy", "confidence": 0.6}
        elif rsi > self.params.rsi_overbought:  # 超买区域
            return {"signal": "sell", "confidence": 0.6}
        else:
            return {"signal": "none", "confidence": 0.4}
    
    def _get_reversal_advisory_signal(self):
        """模拟反转advisor信号"""
        if len(self.datas[0]) < max([self.params.trend_short_ma_period, self.params.trend_long_ma_period, self.params.rsi_period]):
            return {"signal": "none", "confidence": 0.0}
            
        current_price = self.datas[0].close[0]
        prev_price = self.datas[0].close[-1]
        prev2_price = self.datas[0].close[-2]
            
        # 简单反转信号逻辑
        if current_price > prev_price > prev2_price:  # 连续上涨
            return {"signal": "sell", "confidence": 0.5}
        elif current_price < prev_price < prev2_price:  # 连续下跌
            return {"signal": "buy", "confidence": 0.5}
        else:
            return {"signal": "none", "confidence": 0.3}
    
    def next(self):
        """交易逻辑 - 完全基于advisory信号"""
        if self.order:
            return  # 有未完成订单，跳过
        
        # 获取advisory信号
        advisory_result = self._get_advisory_signal()
        signal = advisory_result["signal"]
        confidence = advisory_result["confidence"]
        
        self.last_advisory_signal = signal
        self.last_confidence = confidence
        
        # 记录信号状态
        if len(self) % 10 == 0:
            self.log(f"Advisory信号: {signal}, 置信度: {confidence:.2f}")
        
        # 执行交易决策
        if signal == "buy" and not self.position and confidence > 0.5:
            # 买入信号 - 置信度高于阈值且无持仓
            self.order = self.buy()
            self.log(f"Advisory买入信号触发 - 价格: {self.datas[0].close[0]:.2f}, 置信度: {confidence:.2f}")
            
        elif signal == "sell" and self.position and confidence > 0.5:
            # 卖出信号 - 置信度高于阈值且有持仓
            self.order = self.sell()
            self.log(f"Advisory卖出信号触发 - 价格: {self.datas[0].close[0]:.2f}, 置信度: {confidence:.2f}")
    
    def stop(self):
        """结束时的统计"""
        if self.trade_count > 0:
            avg_confidence = self.total_confidence / self.trade_count
        else:
            avg_confidence = 0.0
            
        final_value = self.broker.getvalue()
        initial_cash = self.params.broker_starting_cash if hasattr(self.params, 'broker_starting_cash') else 10000
        
        self.log(f"策略结束 - 最终资产: {final_value:.2f}")
        self.log(f"总交易次数: {self.trade_count}")
        self.log(f"平均置信度: {avg_confidence:.2f}")
        self.log(f"收益率: {(final_value - initial_cash) / initial_cash * 100:.2f}%")


def run_advisory_signal_demo():
    """运行advisory信号策略演示"""
    print("=== LLM Advisory 信号交易策略演示 ===")
    
    cerebro = bt.Cerebro()
    
    # 设置初始参数
    initial_cash = 10000.0
    cerebro.broker.setcash(initial_cash)
    cerebro.broker.setcommission(0.001)
    
    # 添加数据
    symbol = 'INTC'  # 股票代码
    start_date = datetime(2023, 1, 1)
    end_date = datetime(2024, 6, 30)
    
    print(f"获取 {symbol} 数据...")
    data = get_yfinance_data(symbol, start_date, end_date)
    cerebro.adddata(data)
    cerebro.addsizer(bt.sizers.FixedReverser, stake=100)
    # 添加策略 - 传递所有参数
    cerebro.addstrategy(AdvisorySignalStrategy, 
                       broker_starting_cash=initial_cash,
                       print_log=True,
                       trend_short_ma_period=10,
                       trend_long_ma_period=30,
                       trend_lookback_period=20,
                       rsi_period=14,
                       rsi_oversold=30,
                       rsi_overbought=70)
    
    # 分析器
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name="sharpe")
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name="drawdown")
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name="trades")
    
    print("运行advisory信号策略回测...")
    results = cerebro.run()
    
    # 输出结果
    strat = results[0]
    final_value = cerebro.broker.getvalue()
    roi = (final_value - initial_cash) / initial_cash * 100
    
    print(f"\n策略结果:")
    print(f"起始资金: {initial_cash:,.2f}")
    print(f"最终资产: {final_value:,.2f}")
    print(f"总收益率: {roi:.2f}%")
    print(f"交易次数: {strat.trade_count}")
    
    # 输出分析器结果
    sharpe = strat.analyzers.sharpe.get_analysis()
    drawdown = strat.analyzers.drawdown.get_analysis()
    
    print(f"夏普比率: {sharpe['sharperatio']:.2f}" if 'sharperatio' in sharpe else "夏普比率: 无数据")
    print(f"最大回撤: {drawdown['max']['drawdown']:.2f}%" if 'max' in drawdown else "最大回撤: 无数据")
    
    # 绘制图表
    cerebro.plot(style='candle')


if __name__ == "__main__":
    run_advisory_signal_demo()