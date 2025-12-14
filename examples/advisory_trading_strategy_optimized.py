import os
import backtrader as bt
from datetime import datetime
import sys

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from llm_advisory.bt_advisory import BacktraderLLMAdvisory
from llm_advisory.advisors import (
    BacktraderTrendAdvisor,
    BacktraderTechnicalAnalysisAdvisor
)
from utils.fetch_data import get_yfinance_data


class AdvisoryTradingStrategyOptimized(bt.Strategy):
    """优化版LLM Advisory交易策略 - 降低阈值，提高交易频率"""
    
    params = (
        ("print_log", True),
        ("trade_size", 100),
        ("signal_confidence_threshold", 0.4),  # 降低置信度阈值，从0.6降到0.4
        ("max_position_ratio", 0.8),  # 最大仓位比例
        ("min_trade_value", 1000),  # 最小交易金额
    )
    
    def log(self, txt, dt=None):
        """日志记录"""
        if self.params.print_log:
            dt = dt or self.datas[0].datetime.date(0)
            print(f"{dt.isoformat()}, {txt}")
    
    def __init__(self):
        # 创建LLM Advisory系统
        self.advisory = BacktraderLLMAdvisory()
        
        # 添加多个advisor
        self.trend_advisor = BacktraderTrendAdvisor(
            short_ma_period=10,
            long_ma_period=30,
            lookback_period=15
        )
        self.advisory.add_advisor("trend", self.trend_advisor)
        
        self.tech_advisor = BacktraderTechnicalAnalysisAdvisor()
        self.advisory.add_advisor("technical", self.tech_advisor)
        
        # 初始化advisory系统
        self.advisory.init_strategy(self)
        
        # 跟踪状态
        self.order = None
        self.current_signal = "none"
        self.current_confidence = 0.0
        
        # 性能统计
        self.trade_count = 0
        self.buy_count = 0
        self.sell_count = 0
        self.successful_trades = 0
        
        # 技术指标（用于信号生成）
        self.rsi = bt.ind.RSI(self.datas[0], period=14)
        self.sma_short = bt.ind.SMA(self.datas[0], period=10)
        self.sma_long = bt.ind.SMA(self.datas[0], period=30)
        self.macd = bt.ind.MACD(self.datas[0])
        self.atr = bt.ind.ATR(self.datas[0], period=14)  # 添加ATR指标用于风险控制
        
        # 价格通道指标
        self.upper_bb = bt.ind.BollingerBands(self.datas[0]).top
        self.lower_bb = bt.ind.BollingerBands(self.datas[0]).bot
        
    def notify_order(self, order):
        """订单处理"""
        if order.status in [order.Submitted, order.Accepted]:
            return  # 正常流程
            
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(f"ADVISORY买入 - 价格: {order.executed.price:.2f}, 数量: {order.executed.size}")
            else:
                self.log(f"ADVISORY卖出 - 价格: {order.executed.price:.2f}, 数量: {order.executed.size}")
            
            self.trade_count += 1
            if order.isbuy():
                self.buy_count += 1
            else:
                self.sell_count += 1
                
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log(f"ADVISORY订单失败: {order.status}")
            
        self.order = None
    
    def _generate_advisory_signal(self):
        """生成优化版advisory交易信号"""
        if len(self.datas[0]) < 20:  # 减少最小数据要求
            return {"signal": "none", "confidence": 0.0, "reasoning": "数据不足"}
        
        current_price = self.datas[0].close[0]
        signals = []
        
        # 1. 趋势信号（降低要求）
        trend_signal = self._generate_trend_signal(current_price)
        signals.append(trend_signal)
        
        # 2. RSI信号（放宽超买超卖区域）
        rsi_signal = self._generate_rsi_signal()
        signals.append(rsi_signal)
        
        # 3. MACD信号
        macd_signal = self._generate_macd_signal()
        signals.append(macd_signal)
        
        # 4. 布林带信号（新增）
        bb_signal = self._generate_bollinger_signal(current_price)
        signals.append(bb_signal)
        
        # 5. 价格动量信号
        momentum_signal = self._generate_momentum_signal()
        signals.append(momentum_signal)
        
        # 调整信号权重，给予趋势更多权重
        signal_weights = {
            "trend": 0.35,     # 趋势信号权重
            "rsi": 0.2,
            "macd": 0.15,
            "bollinger": 0.15,  # 新增布林带权重
            "momentum": 0.15
        }
        
        return self._combine_signals(signals, signal_weights)
    
    def _generate_trend_signal(self, current_price):
        """生成趋势信号（放宽条件）"""
        if len(self.sma_short) < 1 or len(self.sma_long) < 1:
            return {"signal": "none", "confidence": 0.0, "type": "trend"}
            
        diff_pct = (self.sma_short[0] - self.sma_long[0]) / self.sma_long[0] * 100
        
        if diff_pct > 1.0:  # 放宽趋势判断条件
            confidence = min(0.8, diff_pct * 0.1 + 0.4)  # 降低置信度计算门槛
            return {"signal": "buy", "confidence": confidence, "type": "trend"}
        elif diff_pct < -1.0:  # 放宽趋势判断条件
            confidence = min(0.8, abs(diff_pct) * 0.1 + 0.4)  # 降低置信度计算门槛
            return {"signal": "sell", "confidence": confidence, "type": "trend"}
        else:
            return {"signal": "none", "confidence": 0.3, "type": "trend"}
    
    def _generate_rsi_signal(self):
        """生成RSI信号（放宽超买超卖区域）"""
        if len(self.rsi) < 1:
            return {"signal": "none", "confidence": 0.0, "type": "rsi"}
            
        rsi_value = self.rsi[0]
        if rsi_value < 35:  # 放宽超卖区域
            confidence = min(0.8, (35 - rsi_value) / 35 * 0.8 + 0.2)
            return {"signal": "buy", "confidence": confidence, "type": "rsi"}
        elif rsi_value > 65:  # 放宽超买区域
            confidence = min(0.8, (rsi_value - 65) / 35 * 0.8 + 0.2)
            return {"signal": "sell", "confidence": confidence, "type": "rsi"}
        else:
            return {"signal": "none", "confidence": 0.4, "type": "rsi"}
    
    def _generate_macd_signal(self):
        """生成MACD信号"""
        if len(self.macd.macd) < 2 or len(self.macd.signal) < 2:
            return {"signal": "none", "confidence": 0.0, "type": "macd"}
            
        macd_line = self.macd.macd[0]
        signal_line = self.macd.signal[0]
        
        # 放宽MACD信号条件
        if macd_line > signal_line:
            confidence = min(0.7, (macd_line - signal_line) / max(abs(signal_line), 0.001) * 0.5 + 0.3)
            return {"signal": "buy", "confidence": confidence, "type": "macd"}
        elif macd_line < signal_line:
            confidence = min(0.7, (signal_line - macd_line) / max(abs(macd_line), 0.001) * 0.5 + 0.3)
            return {"signal": "sell", "confidence": confidence, "type": "macd"}
        else:
            return {"signal": "none", "confidence": 0.3, "type": "macd"}
    
    def _generate_bollinger_signal(self, current_price):
        """生成布林带信号"""
        if len(self.upper_bb) < 1 or len(self.lower_bb) < 1:
            return {"signal": "none", "confidence": 0.0, "type": "bollinger"}
            
        upper_bb = self.upper_bb[0]
        lower_bb = self.lower_bb[0]
        
        # 价格接近布林带上轨 - 潜在卖出信号
        if current_price > upper_bb * 0.98:
            confidence = min(0.6, (current_price - upper_bb) / upper_bb * 10 + 0.3)
            return {"signal": "sell", "confidence": confidence, "type": "bollinger"}
        # 价格接近布林带下轨 - 潜在买入信号
        elif current_price < lower_bb * 1.02:
            confidence = min(0.6, (lower_bb - current_price) / lower_bb * 10 + 0.3)
            return {"signal": "buy", "confidence": confidence, "type": "bollinger"}
        else:
            return {"signal": "none", "confidence": 0.2, "type": "bollinger"}
    
    def _generate_momentum_signal(self):
        """生成价格动量信号"""
        if len(self.datas[0]) < 3:
            return {"signal": "none", "confidence": 0.0, "type": "momentum"}
            
        current_price = self.datas[0].close[0]
        # 使用更小的窗口判断动量
        price_change_pct = (current_price - self.datas[0].close[-2]) / self.datas[0].close[-2] * 100
        
        if price_change_pct > 1.5:  # 放宽动量阈值
            confidence = min(0.6, price_change_pct * 0.2 + 0.2)
            return {"signal": "buy", "confidence": confidence, "type": "momentum"}
        elif price_change_pct < -1.5:  # 放宽动量阈值
            confidence = min(0.6, abs(price_change_pct) * 0.2 + 0.2)
            return {"signal": "sell", "confidence": confidence, "type": "momentum"}
        else:
            return {"signal": "none", "confidence": 0.2, "type": "momentum"}
    
    def _combine_signals(self, signals, weights):
        """整合多个信号（降低投票门槛）"""
        buy_votes = 0
        sell_votes = 0
        total_buy_confidence = 0
        total_sell_confidence = 0
        reasoning = []
        
        for signal in signals:
            weight = weights.get(signal["type"], 0.1)
            if signal["signal"] == "buy":
                buy_votes += 1
                total_buy_confidence += signal["confidence"] * weight
                reasoning.append(f"{signal['type']}: bullish (conf: {signal['confidence']:.2f})")
            elif signal["signal"] == "sell":
                sell_votes += 1
                total_sell_confidence += signal["confidence"] * weight
                reasoning.append(f"{signal['type']}: bearish (conf: {signal['confidence']:.2f})")
            else:
                reasoning.append(f"{signal['type']}: neutral (conf: {signal['confidence']:.2f})")
        
        # 降低投票门槛：只要有1个信号且置信度达标即可
        if (buy_votes >= 1 and total_buy_confidence > self.params.signal_confidence_threshold and 
            total_buy_confidence > total_sell_confidence):
            final_signal = "buy"
            confidence = total_buy_confidence
        elif (sell_votes >= 1 and total_sell_confidence > self.params.signal_confidence_threshold and 
              total_sell_confidence > total_buy_confidence):
            final_signal = "sell"
            confidence = total_sell_confidence
        else:
            final_signal = "none"
            confidence = max(total_buy_confidence, total_sell_confidence)
        
        return {
            "signal": final_signal,
            "confidence": confidence,
            "reasoning": "; ".join(reasoning)
        }
    
    def _can_trade(self):
        """判断是否可以交易"""
        if self.order:
            return False
            
        current_price = self.datas[0].close[0]
        
        # 检查最小交易金额
        min_shares = self.params.min_trade_value / current_price
        if min_shares < 1:  # 最少1股
            min_shares = 1
            
        # 检查最大仓位比例
        max_position_value = self.broker.cash * self.params.max_position_ratio
        max_shares = int(max_position_value / current_price)
        
        return max_shares >= min_shares
    
    def next(self):
        """交易逻辑"""
        if not self._can_trade():
            return
        
        # 生成advisory信号
        advisory_result = self._generate_advisory_signal()
        signal = advisory_result["signal"]
        confidence = advisory_result["confidence"]
        
        self.current_signal = signal
        self.current_confidence = confidence
        
        # 更频繁地记录信号状态
        if len(self) % 5 == 0:  # 从10改为5，更频繁记录
            self.log(f"ADVISORY信号 - {signal.upper()}, 置信度: {confidence:.2f}")
            if signal != "none":
                self.log(f"   理由: {advisory_result['reasoning']}")
        
        # 执行交易决策
        current_price = self.datas[0].close[0]
        max_position_value = self.broker.cash * self.params.max_position_ratio
        max_shares = int(max_position_value / current_price)
        
        if signal == "buy" and not self.position:
            # 买入信号 - 无持仓时买入
            size = min(self.params.trade_size, max_shares)
            if size > 0:
                self.order = self.buy(size=size)
                self.log(f"⚡ ADVISORY买入执行 - 价格: {current_price:.2f}, 数量: {size}")
                self.log(f"   信号置信度: {confidence:.2f}")
            
        elif signal == "sell" and self.position:
            # 卖出信号 - 有持仓时卖出
            self.order = self.sell(size=self.position.size)
            self.log(f"⚡ ADVISORY卖出执行 - 价格: {current_price:.2f}")
            self.log(f"   信号置信度: {confidence:.2f}")
    
    def stop(self):
        """策略结束时的统计"""
        final_value = self.broker.getvalue()
        initial_cash = 50000.0  # 使用实际初始资金
        
        self.log("=" * 50)
        self.log("✅ 优化版 LLM ADVISORY 交易策略结果")
        self.log("=" * 50)
        self.log(f"策略起始资金: {initial_cash:,.2f}")
        self.log(f"策略最终资产: {final_value:,.2f}")
        self.log(f"总收益率: {(final_value - initial_cash) / initial_cash * 100:.2f}%")
        self.log(f"总交易次数: {self.trade_count}")
        self.log(f"买入次数: {self.buy_count}")
        self.log(f"卖出次数: {self.sell_count}")
        
        if self.trade_count > 0:
            win_rate = self.successful_trades / self.trade_count * 100
            self.log(f"胜率: {win_rate:.1f}%")
        else:
            self.log("⚠️ 无交易执行，建议进一步调整参数")
        
        self.log("ADVISORY信号统计:")
        self.log(f"  最后信号: {self.current_signal}")
        self.log(f"  最后置信度: {self.current_confidence:.2f}")


def run_optimized_advisory_trading_demo():
    """运行优化版advisory交易策略演示"""
    print("🤖 === 优化版 LLM Advisory 交易策略演示 ===")
    
    cerebro = bt.Cerebro()
    
    # 设置初始参数
    initial_cash = 50000.0
    cerebro.broker.setcash(initial_cash)
    cerebro.broker.setcommission(0.001)  # 0.1%佣金
    
    # 添加数据
    symbol = 'AAPL'  # 苹果公司
    start_date = datetime(2024, 1, 1)
    end_date = datetime(2024, 6, 30)
    
    print(f"📊 获取 {symbol} 数据...")
    try:
        data = get_yfinance_data(symbol, start_date, end_date)
        cerebro.adddata(data)
        print(f"✅ 数据加载成功: {symbol}")
    except Exception as e:
        print(f"❌ 数据加载失败: {e}")
        return
    
    # 添加优化策略
    cerebro.addstrategy(AdvisoryTradingStrategyOptimized)
    
    # 添加分析器
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name="sharpe")
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name="drawdown")
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name="trades")
    cerebro.addanalyzer(bt.analyzers.AnnualReturn, _name="annual")
    
    print("🚀 运行优化版Advisory交易策略回测...")
    try:
        results = cerebro.run()
        
        # 输出结果
        strat = results[0]
        final_value = cerebro.broker.getvalue()
        roi = (final_value - initial_cash) / initial_cash * 100
        
        print("\n📈 优化策略结果:")
        print(f"  起始资金: {initial_cash:,.2f}")
        print(f"  最终资产: {final_value:,.2f}")
        print(f"  总收益率: {roi:.2f}%")
        print(f"  交易次数: {strat.trade_count}")
        
        # 输出详细分析
        sharpe = strat.analyzers.sharpe.get_analysis()
        drawdown = strat.analyzers.drawdown.get_analysis()
        
        if 'sharpe' in sharpe:
            print(f"  夏普比率: {sharpe['sharpe']:.2f}")
        if 'max' in drawdown:
            print(f"  最大回撤: {drawdown['max']['drawdown']:.2f}%")
        
        print("\n?? 优化效果评估:")
        if strat.trade_count > 0:
            print(f"  ✅ 成功生成 {strat.trade_count} 次交易")
            if roi > 0:
                print("  ✅ 策略开始产生正收益")
            else:
                print("  ⚠️ 收益仍需改进，建议微调参数")
        else:
            print("  ❌ 仍无交易，建议进一步降低阈值")
        
        # 绘制图表
        print("\n📊 生成分析图表...")
        cerebro.plot(style='candle', volume=True)
        
    except Exception as e:
        print(f"❌ 回测执行失败: {e}")


if __name__ == "__main__":
    run_optimized_advisory_trading_demo()