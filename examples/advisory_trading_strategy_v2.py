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


class AdvisoryTradingStrategyV2(bt.Strategy):
    """第二版优化：增加止损止盈和自动卖出机制"""
    
    params = (
        ("print_log", True),
        ("trade_size", 100),
        ("signal_confidence_threshold", 0.28),  # 降低阈值增加交易机会
        ("max_position_ratio", 0.8),
        ("min_trade_value", 1000),
        ("stop_loss_pct", 0.04),  # 适中止损，避免过早止损
        ("take_profit_pct", 0.12),  # 提高止盈目标
        ("trailing_stop_pct", 0.025),  # 适中移动止损
        ("allow_short_selling", False),  # 暂时禁用卖空
        
        # 技术指标参数
        ("rsi_period", 14),  # RSI周期
        ("rsi_oversold", 40),  # 放宽RSI超卖线
        ("rsi_overbought", 60),  # 放宽RSI超买线
        ("sma_short_period", 10),  # 短期均线周期
        ("sma_long_period", 30),  # 长期均线周期
        ("bollinger_upper_threshold", 0.985),  # 放宽布林带上轨阈值
        ("bollinger_lower_threshold", 1.015),  # 放宽布林带下轨阈值
        ("kdj_oversold", 25),  # 放宽KDJ超卖线
        ("kdj_overbought", 75),  # 放宽KDJ超买线
        ("volume_sma_period", 5),  # 成交量均线周期
        ("volume_breakout_ratio", 1.4),  # 放宽成交量突破比率
        ("momentum_threshold", 0.8),  # 降低动量阈值
        ("trend_threshold", 0.4),  # 降低趋势阈值
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
        
        self.advisory.init_strategy(self)
        
        # 跟踪状态
        self.order = None
        self.current_signal = "none"
        self.current_confidence = 0.0
        self.entry_price = 0.0
        self.highest_price = 0.0
        
        # 性能统计
        self.trade_count = 0
        self.buy_count = 0
        self.sell_count = 0
        self.successful_trades = 0
        
        # 技术指标
        self.rsi = bt.ind.RSI(self.datas[0], period=self.params.rsi_period)
        self.sma_short = bt.ind.SMA(self.datas[0], period=self.params.sma_short_period)
        self.sma_long = bt.ind.SMA(self.datas[0], period=self.params.sma_long_period)
        self.macd = bt.ind.MACD(self.datas[0])
        self.atr = bt.ind.ATR(self.datas[0], period=14)
        self.upper_bb = bt.ind.BollingerBands(self.datas[0]).top
        self.lower_bb = bt.ind.BollingerBands(self.datas[0]).bot
        # 新增指标
        self.kd = bt.ind.Stochastic(self.datas[0])  # KDJ指标
        self.volume_sma = bt.ind.SMA(self.datas[0].volume, period=self.params.volume_sma_period)  # 成交量均线
        # 移除OBV指标，改用成交量突破判断
        self.volume_break = bt.indicators.CrossOver(self.datas[0].volume, self.volume_sma)  # 成交量突破信号
        
    def notify_order(self, order):
        """订单处理"""
        if order.status in [order.Submitted, order.Accepted]:
            return
            
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(f"ADVISORY买入 - 价格: {order.executed.price:.2f}, 数量: {order.executed.size}")
                self.entry_price = order.executed.price
                self.highest_price = order.executed.price
            else:
                self.log(f"ADVISORY卖出 - 价格: {order.executed.price:.2f}, 数量: {order.executed.size}")
                # 计算交易结果
                if self.position:  # 只有在仓位存在时才计算收益
                    profit_pct = (order.executed.price - self.entry_price) / self.entry_price * 100
                    if profit_pct > 0:
                        self.successful_trades += 1
                        self.log(f"💰 盈利交易: +{profit_pct:.2f}%")
                    else:
                        self.log(f"📉 亏损交易: {profit_pct:.2f}%")
            
            self.trade_count += 1
            if order.isbuy():
                self.buy_count += 1
            else:
                self.sell_count += 1
                
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log(f"ADVISORY订单失败: {order.status}")
            
        self.order = None
    
    def _should_sell_due_to_risk(self, current_price):
        """风险控制卖出判断"""
        if not self.position:
            return False
            
        # 止损检查
        if current_price <= self.entry_price * (1 - self.params.stop_loss_pct):
            self.log(f"🛑 触发止损: {current_price:.2f} (买入价: {self.entry_price:.2f})")
            return True
            
        # 止盈检查
        if current_price >= self.entry_price * (1 + self.params.take_profit_pct):
            self.log(f"🎯 触发止盈: {current_price:.2f} (买入价: {self.entry_price:.2f})")
            return True
            
        # 移动止损检查
        if current_price > self.highest_price:
            self.highest_price = current_price
            
        trailing_stop_price = self.highest_price * (1 - self.params.trailing_stop_pct)
        if current_price <= trailing_stop_price:
            self.log(f"📉 触发移动止损: {current_price:.2f} (最高价: {self.highest_price:.2f})")
            return True
            
        return False
    
    def _generate_advisory_signal(self):
        """生成交易信号"""
        if len(self.datas[0]) < 15:
            return {"signal": "none", "confidence": 0.0, "reasoning": "数据不足"}
        
        current_price = self.datas[0].close[0]
        signals = []
        
        # 趋势信号
        trend_signal = self._generate_trend_signal(current_price)
        signals.append(trend_signal)
        
        # RSI信号
        rsi_signal = self._generate_rsi_signal()
        signals.append(rsi_signal)
        
        # MACD信号
        macd_signal = self._generate_macd_signal()
        signals.append(macd_signal)
        
        # 布林带信号
        bb_signal = self._generate_bollinger_signal(current_price)
        signals.append(bb_signal)
        
        # 动量信号
        momentum_signal = self._generate_momentum_signal()
        signals.append(momentum_signal)
        
        # KDJ信号
        kdj_signal = self._generate_kdj_signal()
        signals.append(kdj_signal)
        
        # 成交量信号
        volume_signal = self._generate_volume_signal()
        signals.append(volume_signal)
        
        signal_weights = {
            "trend": 0.25,  # 降低趋势权重
            "rsi": 0.2,     # 降低RSI权重
            "macd": 0.15,   # 降低MACD权重
            "bollinger": 0.1,  # 降低布林带权重
            "momentum": 0.1,  # 保持动量权重
            "kdj": 0.1,     # 新增KDJ指标权重
            "volume": 0.1   # 新增成交量指标权重
        }
        
        return self._combine_signals(signals, signal_weights)
    
    def _generate_trend_signal(self, current_price):
        """生成趋势信号"""
        if len(self.sma_short) < 1 or len(self.sma_long) < 1:
            return {"signal": "none", "confidence": 0.0, "type": "trend"}
            
        diff_pct = (self.sma_short[0] - self.sma_long[0]) / self.sma_long[0] * 100
        
        if diff_pct > self.params.trend_threshold:
            confidence = min(0.8, diff_pct * 0.1 + 0.35)
            return {"signal": "buy", "confidence": confidence, "type": "trend"}
        elif diff_pct < -self.params.trend_threshold:
            confidence = min(0.8, abs(diff_pct) * 0.1 + 0.35)
            return {"signal": "sell", "confidence": confidence, "type": "trend"}
        else:
            return {"signal": "none", "confidence": 0.25, "type": "trend"}
    
    def _generate_rsi_signal(self):
        """生成RSI信号"""
        if len(self.rsi) < 1:
            return {"signal": "none", "confidence": 0.0, "type": "rsi"}
            
        rsi_value = self.rsi[0]
        if rsi_value < self.params.rsi_oversold:
            confidence = min(0.8, (self.params.rsi_oversold - rsi_value) / self.params.rsi_oversold * 0.8 + 0.2)
            return {"signal": "buy", "confidence": confidence, "type": "rsi"}
        elif rsi_value > self.params.rsi_overbought:
            confidence = min(0.8, (rsi_value - self.params.rsi_overbought) / (100 - self.params.rsi_overbought) * 0.8 + 0.2)
            return {"signal": "sell", "confidence": confidence, "type": "rsi"}
        else:
            return {"signal": "none", "confidence": 0.3, "type": "rsi"}
    
    def _generate_macd_signal(self):
        """生成MACD信号"""
        if len(self.macd.macd) < 2 or len(self.macd.signal) < 2:
            return {"signal": "none", "confidence": 0.0, "type": "macd"}
            
        macd_line = self.macd.macd[0]
        signal_line = self.macd.signal[0]
        
        if macd_line > signal_line:
            confidence = min(0.7, (macd_line - signal_line) / max(abs(signal_line), 0.001) * 0.4 + 0.3)
            return {"signal": "buy", "confidence": confidence, "type": "macd"}
        elif macd_line < signal_line:
            confidence = min(0.7, (signal_line - macd_line) / max(abs(macd_line), 0.001) * 0.4 + 0.3)
            return {"signal": "sell", "confidence": confidence, "type": "macd"}
        else:
            return {"signal": "none", "confidence": 0.25, "type": "macd"}
    
    def _generate_bollinger_signal(self, current_price):
        """生成布林带信号"""
        if len(self.upper_bb) < 1 or len(self.lower_bb) < 1:
            return {"signal": "none", "confidence": 0.0, "type": "bollinger"}
            
        upper_bb = self.upper_bb[0]
        lower_bb = self.lower_bb[0]
        
        if current_price > upper_bb * self.params.bollinger_upper_threshold:
            confidence = min(0.6, (current_price - upper_bb) / upper_bb * 8 + 0.3)
            return {"signal": "sell", "confidence": confidence, "type": "bollinger"}
        elif current_price < lower_bb * self.params.bollinger_lower_threshold:
            confidence = min(0.6, (lower_bb - current_price) / lower_bb * 8 + 0.3)
            return {"signal": "buy", "confidence": confidence, "type": "bollinger"}
        else:
            return {"signal": "none", "confidence": 0.2, "type": "bollinger"}
    
    def _generate_momentum_signal(self):
        """生成动量信号"""
        if len(self.datas[0]) < 3:
            return {"signal": "none", "confidence": 0.0, "type": "momentum"}
            
        price_change_pct = (self.datas[0].close[0] - self.datas[0].close[-2]) / self.datas[0].close[-2] * 100
        
        if price_change_pct > self.params.momentum_threshold:
            confidence = min(0.6, price_change_pct * 0.15 + 0.2)
            return {"signal": "buy", "confidence": confidence, "type": "momentum"}
        elif price_change_pct < -self.params.momentum_threshold:
            confidence = min(0.6, abs(price_change_pct) * 0.15 + 0.2)
            return {"signal": "sell", "confidence": confidence, "type": "momentum"}
        else:
            return {"signal": "none", "confidence": 0.15, "type": "momentum"}
    
    def _generate_kdj_signal(self):
        """生成KDJ信号"""
        if len(self.kd) < 1:
            return {"signal": "none", "confidence": 0.0, "type": "kdj"}
            
        k = self.kd.percK[0]
        d = self.kd.percD[0]
        
        if k < self.params.kdj_oversold and d < self.params.kdj_oversold and k > d:
            confidence = min(0.7, (self.params.kdj_oversold - min(k, d)) / self.params.kdj_oversold * 0.7 + 0.2)
            return {"signal": "buy", "confidence": confidence, "type": "kdj"}
        elif k > self.params.kdj_overbought and d > self.params.kdj_overbought and k < d:
            confidence = min(0.7, (min(k, d) - self.params.kdj_overbought) / (100 - self.params.kdj_overbought) * 0.7 + 0.2)
            return {"signal": "sell", "confidence": confidence, "type": "kdj"}
        else:
            return {"signal": "none", "confidence": 0.2, "type": "kdj"}
    
    def _generate_volume_signal(self):
        """生成成交量信号"""
        if len(self.volume_break) < 1:
            return {"signal": "none", "confidence": 0.0, "type": "volume"}
            
        # 成交量上穿均线
        if self.volume_break[0] == 1:
            confidence = min(0.6, (self.datas[0].volume[0] / self.volume_sma[0] - 1) * 0.2 + 0.3)
            return {"signal": "buy", "confidence": confidence, "type": "volume"}
        # 成交量下穿均线
        elif self.volume_break[0] == -1:
            confidence = min(0.6, (self.volume_sma[0] / self.datas[0].volume[0] - 1) * 0.2 + 0.3)
            return {"signal": "sell", "confidence": confidence, "type": "volume"}
        else:
            return {"signal": "none", "confidence": 0.15, "type": "volume"}
    
    def _combine_signals(self, signals, weights):
        """整合信号"""
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
        
        # 只要有信号且置信度达标即可
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
        min_shares = max(1, int(self.params.min_trade_value / current_price))
        max_shares = int(self.broker.cash * self.params.max_position_ratio / current_price)
        
        return max_shares >= min_shares
    
    def next(self):
        """交易逻辑"""
        if not self._can_trade():
            return
        
        current_price = self.datas[0].close[0]
        
        # 风险控制卖出检查
        if self.position and self._should_sell_due_to_risk(current_price):
            self.order = self.sell(size=self.position.size)
            return
        
        # 生成advisory信号
        advisory_result = self._generate_advisory_signal()
        signal = advisory_result["signal"]
        confidence = advisory_result["confidence"]
        
        self.current_signal = signal
        self.current_confidence = confidence
        
        # 记录信号
        if len(self) % 3 == 0:  # 更频繁记录
            self.log(f"ADVISORY信号 - {signal.upper()}, 置信度: {confidence:.2f}")
            if signal != "none":
                self.log(f"   理由: {advisory_result['reasoning']}")
        
        # 执行交易决策
        max_shares = int(self.broker.cash * self.params.max_position_ratio / current_price)
        
        if signal == "buy" and not self.position:
            size = min(self.params.trade_size, max_shares)
            if size > 0:
                self.order = self.buy(size=size)
                self.log(f"⚡ ADVISORY买入执行 - 价格: {current_price:.2f}, 数量: {size}")
                self.log(f"   信号置信度: {confidence:.2f}")
            
        elif signal == "sell":
            if self.position:
                # 有持仓时平仓卖出
                self.order = self.sell(size=self.position.size)
                self.log(f"⚡ ADVISORY平仓卖出 - 价格: {current_price:.2f}")
                self.log(f"   信号置信度: {confidence:.2f}")
            elif self.params.allow_short_selling:
                # 无持仓且允许卖空时开仓卖空
                size = min(self.params.trade_size, max_shares)
                if size > 0:
                    self.order = self.sell(size=size)
                    self.log(f"⚡ ADVISORY卖空开仓 - 价格: {current_price:.2f}, 数量: {size}")
                    self.log(f"   信号置信度: {confidence:.2f}")
    
    def stop(self):
        """策略结束时的统计"""
        final_value = self.broker.getvalue()
        initial_cash = 50000.0
        
        self.log("=" * 60)
        self.log("🚀 第二版优化策略结果")
        self.log("=" * 60)
        self.log(f"策略起始资金: {initial_cash:,.2f}")
        self.log(f"策略最终资产: {final_value:,.2f}")
        self.log(f"总收益率: {(final_value - initial_cash) / initial_cash * 100:.2f}%")
        self.log(f"总交易次数: {self.trade_count}")
        self.log(f"买入次数: {self.buy_count}")
        self.log(f"卖出次数: {self.sell_count}")
        
        if self.trade_count > 0:
            win_rate = self.successful_trades / self.trade_count * 100
            self.log(f"胜率: {win_rate:.1f}%")
            avg_profit = (final_value - initial_cash) / self.trade_count
            self.log(f"平均每笔收益: {avg_profit:.2f}")
        else:
            self.log("⚠️ 无交易执行")
        
        self.log("风险控制统计:")
        self.log(f"  止损设置: {self.params.stop_loss_pct * 100:.1f}%")
        self.log(f"  止盈设置: {self.params.take_profit_pct * 100:.1f}%")
        self.log(f"  移动止损: {self.params.trailing_stop_pct * 100:.1f}%")
        self.log(f"  卖空允许: {'是' if self.params.allow_short_selling else '否'}")
        
        self.log("ADVISORY信号统计:")
        self.log(f"  最后信号: {self.current_signal}")
        self.log(f"  最后置信度: {self.current_confidence:.2f}")


def run_advisory_trading_v2_demo():
    """运行第二版优化策略演示"""
    print("🤖 === 第二版 LLM Advisory 交易策略演示 ===")
    print("💡 新增功能: 止损止盈 + 移动止损 + 风险控制")
    
    cerebro = bt.Cerebro()
    
    # 设置初始参数
    initial_cash = 50000.0
    cerebro.broker.setcash(initial_cash)
    cerebro.broker.setcommission(0.001)
    
    # 添加数据
    symbol = 'AAPL'
    start_date = datetime(2023, 1, 1)
    end_date = datetime(2024, 6, 30)
    
    print(f"📊 获取 {symbol} 数据...")
    try:
        data = get_yfinance_data(symbol, start_date, end_date)
        cerebro.adddata(data)
        print(f"✅ 数据加载成功: {symbol}")
    except Exception as e:
        print(f"❌ 数据加载失败: {e}")
        return
    
    # 添加第二版策略
    cerebro.addstrategy(AdvisoryTradingStrategyV2)
    
    # 添加分析器
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name="sharpe")
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name="drawdown")
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name="trades")
    cerebro.addanalyzer(bt.analyzers.AnnualReturn, _name="annual")
    
    print("🚀 运行第二版优化策略回测...")
    try:
        results = cerebro.run()
        
        # 输出结果
        strat = results[0]
        final_value = cerebro.broker.getvalue()
        roi = (final_value - initial_cash) / initial_cash * 100
        
        print("\n📈 第二版策略结果:")
        print(f"  起始资金: {initial_cash:,.2f}")
        print(f"  最终资产: {final_value:,.2f}")
        print(f"  总收益率: {roi:.2f}%")
        print(f"  交易次数: {strat.trade_count}")
        print(f"  胜率: {strat.successful_trades / strat.trade_count * 100:.1f}%" if strat.trade_count > 0 else "  胜率: N/A")
        
        # 输出详细分析
        sharpe = strat.analyzers.sharpe.get_analysis()
        drawdown = strat.analyzers.drawdown.get_analysis()
        
        if 'sharpe' in sharpe:
            print(f"  夏普比率: {sharpe['sharpe']:.2f}")
        if 'max' in drawdown:
            print(f"  最大回撤: {drawdown['max']['drawdown']:.2f}%")
        
        print("\n🎯 策略评估:")
        if strat.trade_count >= 2:  # 至少完成买入卖出完整交易
            if roi > 5:
                print("  ✅ 优秀表现！策略运行良好")
            elif roi > 0:
                print("  ✅ 稳定盈利，建议继续优化")
            else:
                print("  ⚠️ 需要进一步调整参数")
        elif strat.trade_count == 1:
            print("  ⚠️ 只有部分交易，建议观察完整交易周期")
        else:
            print("  ❌ 无交易，需要大幅降低阈值")
        
        # 绘制图表
        print("\n📊 生成分析图表...")
        cerebro.plot(style='candle', volume=True)
        
    except Exception as e:
        print(f"❌ 回测执行失败: {e}")


if __name__ == "__main__":
    run_advisory_trading_v2_demo()