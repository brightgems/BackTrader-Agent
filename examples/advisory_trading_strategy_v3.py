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


class AdvisoryTradingStrategyV3(bt.Strategy):
    """第三版优化：技术指标权重优化 + 新增成交量指标"""
    
    params = (
        ("print_log", True),
        ("trade_size", 100),
        ("signal_confidence_threshold", 0.38),  # 微调阈值
        ("max_position_ratio", 0.8),
        ("min_trade_value", 1000),
        ("stop_loss_pct", 0.05),
        ("take_profit_pct", 0.12),  # 提高止盈到12%
        ("trailing_stop_pct", 0.04),  # 放宽移动止损到4%
        ("volume_threshold", 1.2),  # 成交量阈值
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
        
        # 技术指标 - 基础指标（权重优化）
        self.rsi = bt.ind.RSI(self.datas[0], period=14)
        self.sma_short = bt.ind.SMA(self.datas[0], period=10)
        self.sma_long = bt.ind.SMA(self.datas[0], period=30)
        self.macd = bt.ind.MACD(self.datas[0])
        self.atr = bt.ind.ATR(self.datas[0], period=14)
        self.upper_bb = bt.ind.BollingerBands(self.datas[0]).top
        self.lower_bb = bt.ind.BollingerBands(self.datas[0]).bot
        
        # 新增技术指标
        # 1. OBV (能量潮指标) - 成交量确认
        self.obv = bt.ind.OnBalanceVolume(self.datas[0])
        # 2. Volume SMA (成交量均线)
        self.volume_sma = bt.ind.SMA(self.datas[0].volume, period=20)
        # 3. Stochastic (随机指标)
        self.stoch = bt.ind.Stochastic(self.datas[0])
        # 4. ADX (平均趋向指数) - 趋势强度
        self.adx = bt.ind.ADX(self.datas[0])
        # 5. Ichimoku Cloud (一目均衡表)
        self.ichi_tenkan = bt.ind.IchimokuTenkanSen(self.datas[0])
        self.ichi_kijun = bt.ind.IchimokuKijunSen(self.datas[0])
        self.ichi_senkou_a = bt.ind.IchimokuSenkouSpanA(self.datas[0])
        self.ichi_senkou_b = bt.ind.IchimokuSenkouSpanB(self.datas[0])
        
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
    
    def _check_volume_confirmation(self):
        """成交量确认检查"""
        if len(self.datas[0]) < 20:
            return True  # 数据不足时跳过检查
            
        current_volume = self.datas[0].volume[0]
        volume_avg = self.volume_sma[0]
        
        # 成交量超过平均成交量的阈值才确认信号
        if current_volume > volume_avg * self.params.volume_threshold:
            return True
        return False
    
    def _generate_advisory_signal(self):
        """生成优化版交易信号"""
        if len(self.datas[0]) < 25:  # 增加数据要求
            return {"signal": "none", "confidence": 0.0, "reasoning": "数据不足"}
        
        current_price = self.datas[0].close[0]
        signals = []
        
        # 基础指标信号 (权重优化)
        trend_signal = self._generate_trend_signal(current_price)
        signals.append(trend_signal)
        
        rsi_signal = self._generate_rsi_signal()
        signals.append(rsi_signal)
        
        macd_signal = self._generate_macd_signal()
        signals.append(macd_signal)
        
        bb_signal = self._generate_bollinger_signal(current_price)
        signals.append(bb_signal)
        
        momentum_signal = self._generate_momentum_signal()
        signals.append(momentum_signal)
        
        # 新增指标信号
        obv_signal = self._generate_obv_signal()
        signals.append(obv_signal)
        
        stoch_signal = self._generate_stoch_signal()
        signals.append(stoch_signal)
        
        adx_signal = self._generate_adx_signal()
        signals.append(adx_signal)
        
        ichimoku_signal = self._generate_ichimoku_signal(current_price)
        signals.append(ichimoku_signal)
        
        # 优化后的权重分配 - 给予趋势和成交量更高权重
        signal_weights = {
            "trend": 0.25,      # 趋势指标权重降低但保持重要
            "rsi": 0.15,        # RSI权重降低
            "macd": 0.12,       # MACD权重降低
            "bollinger": 0.10,  # 布林带权重降低
            "momentum": 0.08,   # 动量指标权重降低
            "obv": 0.12,        # 新增OBV权重
            "stoch": 0.08,      # 随机指标权重
            "adx": 0.06,        # 趋势强度权重
            "ichimoku": 0.04,   # 一目均衡表权重
        }
        
        return self._combine_signals(signals, signal_weights)
    
    def _generate_trend_signal(self, current_price):
        """生成趋势信号"""
        if len(self.sma_short) < 1 or len(self.sma_long) < 1:
            return {"signal": "none", "confidence": 0.0, "type": "trend"}
            
        # 使用更严格的趋势判断
        diff_pct = (self.sma_short[0] - self.sma_long[0]) / self.sma_long[0] * 100
        adx_value = self.adx[0] if len(self.adx) > 0 else 0
        
        # 只有当ADX显示强趋势时才给予高置信度
        if diff_pct > 1.5 and adx_value > 25:  # 强上涨趋势
            confidence = min(0.85, diff_pct * 0.05 + 0.5)
            return {"signal": "buy", "confidence": confidence, "type": "trend"}
        elif diff_pct < -1.5 and adx_value > 25:  # 强下跌趋势
            confidence = min(0.85, abs(diff_pct) * 0.05 + 0.5)
            return {"signal": "sell", "confidence": confidence, "type": "trend"}
        else:
            return {"signal": "none", "confidence": 0.15, "type": "trend"}
    
    def _generate_rsi_signal(self):
        """生成RSI信号（优化）"""
        if len(self.rsi) < 1:
            return {"signal": "none", "confidence": 0.0, "type": "rsi"}
            
        rsi_value = self.rsi[0]
        # 更严格的超买超卖区域
        if rsi_value < 28:
            confidence = min(0.8, (28 - rsi_value) / 28 * 0.8 + 0.3)
            return {"signal": "buy", "confidence": confidence, "type": "rsi"}
        elif rsi_value > 72:
            confidence = min(0.8, (rsi_value - 72) / 28 * 0.8 + 0.3)
            return {"signal": "sell", "confidence": confidence, "type": "rsi"}
        else:
            return {"signal": "none", "confidence": 0.2, "type": "rsi"}
    
    def _generate_macd_signal(self):
        """生成MACD信号（优化）"""
        if len(self.macd.macd) < 3 or len(self.macd.signal) < 3:
            return {"signal": "none", "confidence": 0.0, "type": "macd"}
            
        macd_line = self.macd.macd[0]
        signal_line = self.macd.signal[0]
        hist_line = self.macd.histo[0]
        
        # 需要MACD柱状图确认
        if macd_line > signal_line and hist_line > 0:
            confidence = min(0.7, (macd_line - signal_line) / max(abs(signal_line), 0.001) * 0.3 + 0.4)
            return {"signal": "buy", "confidence": confidence, "type": "macd"}
        elif macd_line < signal_line and hist_line < 0:
            confidence = min(0.7, (signal_line - macd_line) / max(abs(macd_line), 0.001) * 0.3 + 0.4)
            return {"signal": "sell", "confidence": confidence, "type": "macd"}
        else:
            return {"signal": "none", "confidence": 0.2, "type": "macd"}
    
    def _generate_bollinger_signal(self, current_price):
        """生成布林带信号"""
        if len(self.upper_bb) < 1 or len(self.lower_bb) < 1:
            return {"signal": "none", "confidence": 0.0, "type": "bollinger"}
            
        upper_bb = self.upper_bb[0]
        lower_bb = self.lower_bb[0]
        
        # 更严格的布林带边界
        if current_price > upper_bb * 0.99:
            confidence = min(0.7, (current_price - upper_bb) / upper_bb * 5 + 0.4)
            return {"signal": "sell", "confidence": confidence, "type": "bollinger"}
        elif current_price < lower_bb * 1.01:
            confidence = min(0.7, (lower_bb - current_price) / lower_bb * 5 + 0.4)
            return {"signal": "buy", "confidence": confidence, "type": "bollinger"}
        else:
            return {"signal": "none", "confidence": 0.15, "type": "bollinger"}
    
    def _generate_momentum_signal(self):
        """生成动量信号"""
        if len(self.datas[0]) < 5:
            return {"signal": "none", "confidence": 0.0, "type": "momentum"}
            
        # 使用5日动量，更稳定
        price_change_pct = (self.datas[0].close[0] - self.datas[0].close[-5]) / self.datas[0].close[-5] * 100
        
        if price_change_pct > 3.0:  # 更强的动量要求
            confidence = min(0.6, price_change_pct * 0.1 + 0.2)
            return {"signal": "buy", "confidence": confidence, "type": "momentum"}
        elif price_change_pct < -3.0:
            confidence = min(0.6, abs(price_change_pct) * 0.1 + 0.2)
            return {"signal": "sell", "confidence": confidence, "type": "momentum"}
        else:
            return {"signal": "none", "confidence": 0.1, "type": "momentum"}
    
    def _generate_obv_signal(self):
        """生成OBV信号"""
        if len(self.obv) < 2:
            return {"signal": "none", "confidence": 0.0, "type": "obv"}
            
        obv_trend = self.obv[0] - self.obv[-5] if len(self.obv) >= 5 else 0
        
        if obv_trend > 0:
            # OBV上升，看涨信号
            confidence = min(0.6, obv_trend / max(abs(self.obv[-5]), 1) * 100 + 0.3)
            return {"signal": "buy", "confidence": confidence, "type": "obv"}
        elif obv_trend < 0:
            # OBV下降，看跌信号
            confidence = min(0.6, abs(obv_trend) / max(abs(self.obv[-5]), 1) * 100 + 0.3)
            return {"signal": "sell", "confidence": confidence, "type": "obv"}
        else:
            return {"signal": "none", "confidence": 0.15, "type": "obv"}
    
    def _generate_stoch_signal(self):
        """生成随机指标信号"""
        if len(self.stoch) < 1:
            return {"signal": "none", "confidence": 0.0, "type": "stoch"}
            
        stoch_k = self.stoch.percK[0]
        stoch_d = self.stoch.percD[0]
        
        if stoch_k < 20 and stoch_k > stoch_d:
            confidence = min(0.7, (20 - stoch_k) / 20 * 0.7 + 0.2)
            return {"signal": "buy", "confidence": confidence, "type": "stoch"}
        elif stoch_k > 80 and stoch_k < stoch_d:
            confidence = min(0.7, (stoch_k - 80) / 20 * 0.7 + 0.2)
            return {"signal": "sell", "confidence": confidence, "type": "stoch"}
        else:
            return {"signal": "none", "confidence": 0.1, "type": "stoch"}
    
    def _generate_adx_signal(self):
        """生成ADX趋势强度信号"""
        if len(self.adx) < 1:
            return {"signal": "none", "confidence": 0.0, "type": "adx"}
            
        adx_value = self.adx[0]
        
        # ADX > 25表示强趋势，但本身不提供方向
        if adx_value > 25:
            return {"signal": "trend_strong", "confidence": min(0.6, (adx_value - 25) / 25 * 0.6 + 0.2), "type": "adx"}
        else:
            return {"signal": "trend_weak", "confidence": 0.1, "type": "adx"}
    
    def _generate_ichimoku_signal(self, current_price):
        """生成一目均衡表信号"""
        if (len(self.ichi_tenkan) < 1 or len(self.ichi_kijun) < 1 or 
            len(self.ichi_senkou_a) < 1 or len(self.ichi_senkou_b) < 1):
            return {"signal": "none", "confidence": 0.0, "type": "ichimoku"}
        
        tenkan = self.ichi_tenkan[0]
        kijun = self.ichi_kijun[0]
        senkou_a = self.ichi_senkou_a[0]
        senkou_b = self.ichi_senkou_b[0]
        
        # 转换线 > 基准线: 看涨
        if tenkan > kijun and current_price > max(senkou_a, senkou_b):
            confidence = min(0.5, (tenkan - kijun) / kijun * 100 + 0.2)
            return {"signal": "buy", "confidence": confidence, "type": "ichimoku"}
        # 转换线 < 基准线: 看跌
        elif tenkan < kijun and current_price < min(senkou_a, senkou_b):
            confidence = min(0.5, (kijun - tenkan) / tenkan * 100 + 0.2)
            return {"signal": "sell", "confidence": confidence, "type": "ichimoku"}
        else:
            return {"signal": "none", "confidence": 0.05, "type": "ichimoku"}
    
    def _combine_signals(self, signals, weights):
        """优化信号整合"""
        buy_votes = 0
        sell_votes = 0
        total_buy_confidence = 0
        total_sell_confidence = 0
        reasoning = []
        
        for signal in signals:
            weight = weights.get(signal["type"], 0.05)  # 默认权重降低
            
            if signal["signal"] in ["buy", "trend_strong"]:
                buy_votes += 1
                total_buy_confidence += signal["confidence"] * weight
                reasoning.append(f"{signal['type']}: bullish (conf: {signal['confidence']:.2f})")
            elif signal["signal"] in ["sell"]:
                sell_votes += 1
                total_sell_confidence += signal["confidence"] * weight
                reasoning.append(f"{signal['type']}: bearish (conf: {signal['confidence']:.2f})")
            elif signal["signal"] == "trend_weak":
                # 弱趋势降低整体信心但不改变方向
                total_buy_confidence *= 0.8
                total_sell_confidence *= 0.8
                reasoning.append(f"{signal['type']}: weak trend (conf: {signal['confidence']:.2f})")
            else:
                reasoning.append(f"{signal['type']}: neutral (conf: {signal['confidence']:.2f})")
        
        # 成交量确认
        volume_confirm = self._check_volume_confirmation()
        if not volume_confirm:
            total_buy_confidence *= 0.7  # 成交量不足时降低信心
            total_sell_confidence *= 0.7
            reasoning.append("volume: weak confirmation")
        
        # 更严格的信号要求
        min_votes = 2  # 需要至少2个指标确认
        if (buy_votes >= min_votes and total_buy_confidence > self.params.signal_confidence_threshold and 
            total_buy_confidence > total_sell_confidence * 1.2):  # 买入信号需要明显优势
            final_signal = "buy"
            confidence = total_buy_confidence
        elif (sell_votes >= min_votes and total_sell_confidence > self.params.signal_confidence_threshold and 
              total_sell_confidence > total_buy_confidence * 1.2):  # 卖出信号需要明显优势
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
        
        # 更智能的信号记录
        if signal != "none" or len(self) % 5 == 0:
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
            
        elif signal == "sell" and self.position:
            self.order = self.sell(size=self.position.size)
            self.log(f"⚡ ADVISORY卖出执行 - 价格: {current_price:.2f}")
            self.log(f"   信号置信度: {confidence:.2f}")
    
    def stop(self):
        """策略结束时的统计"""
        final_value = self.broker.getvalue()
        initial_cash = 50000.0
        
        self.log("=" * 60)
        self.log("🚀 第三版技术指标优化策略结果")
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
        
        self.log("第三版优化特点:")
        self.log("  • 新增OBV、随机指标、ADX、一目均衡表")
        self.log("  • 优化指标权重分配")
        self.log("  • 添加成交量确认机制")
        self.log("  • 严格信号过滤")
        
        self.log("ADVISORY信号统计:")
        self.log(f"  最后信号: {self.current_signal}")
        self.log(f"  最后置信度: {self.current_confidence:.2f}")


def run_advisory_trading_v3_demo():
    """运行第三版技术指标优化策略演示"""
    print("🤖 === 第三版 LLM Advisory 技术指标优化演示 ===")
    print("💡 优化内容: 新增OBV/ADX/Stochastic指标 + 权重优化 + 成交量确认")
    
    cerebro = bt.Cerebro()
    
    # 设置初始参数
    initial_cash = 50000.0
    cerebro.broker.setcash(initial_cash)
    cerebro.broker.setcommission(0.001)
    
    # 添加数据
    symbol = 'AAPL'
    start_date = datetime(2024, 1, 1)
    end_date = datetime(2024, 6, 30)
    
    print(f"📊 获取 {symbol} 数据...")
    try:
        data = get_yfinance_data(symbol, start_date, end_date)
        cerebro.adddata(data)
        print(f"✅ 数据加载成功: {symbol}")
    except Exception as e:
        print(f"❌ 数据加载失败: {e}")
