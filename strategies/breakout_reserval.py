import backtrader as bt
from utils.base_strategy import BaseStrategy
from utils.runer import run_strategy
import sys
sys.path.append('../')


class BreakoutReversalStrategy(BaseStrategy):
    params = (
        ('breakout_period', 20),  # 增加突破周期减少假突破
        ('breakout_confirmation', 1),  # 突破确认天数
        ('atr_period', 14),  # ATR计算周期
        ('stop_loss_atr_multiplier', 2.0),  # ATR止损倍数
        ('take_profit_atr_multiplier', 3.0),  # ATR止盈倍数
        ('volume_filter_multiplier', 1.5),  # 成交量过滤倍数
    )
    
    def __init__(self):
        super().__init__()
        # 添加技术指标
        self.atr = bt.indicators.ATR(self.data, period=self.params.atr_period)
        
        # 突破确认计数器
        self.breakout_up_count = 0
        self.breakout_down_count = 0
        
    def next(self):
        if len(self) < max(self.params.breakout_period, self.params.atr_period):
            return
        
        # 计算突破价格
        high_breakout = max(self.data.high.get(size=self.params.breakout_period)[:-1])
        low_breakout = min(self.data.low.get(size=self.params.breakout_period)[:-1])
        
        # 成交量过滤 - 平均成交量的1.5倍
        avg_volume = sum(self.data.volume.get(size=self.params.breakout_period)) / self.params.breakout_period
        volume_ok = self.data.volume[0] > avg_volume * self.params.volume_filter_multiplier
        
        # 更新突破确认计数器
        if self.data.close[0] > high_breakout:
            self.breakout_up_count += 1
            self.breakout_down_count = 0
        elif self.data.close[0] < low_breakout:
            self.breakout_down_count += 1
            self.breakout_up_count = 0
        else:
            self.breakout_up_count = 0
            self.breakout_down_count = 0
        
        if not self.position:
            # 突破上轨开多（需要确认且成交量过滤）
            if (self.breakout_up_count >= self.params.breakout_confirmation and 
                volume_ok and 
                self.data.close[0] > high_breakout):
                self.buy()
                self.entry_price = self.data.close[0]
                self.stop_loss_price = self.entry_price - self.atr[0] * self.params.stop_loss_atr_multiplier
                self.take_profit_price = self.entry_price + self.atr[0] * self.params.take_profit_atr_multiplier
            
            # 突破下轨开空（需要确认且成交量过滤）
            elif (self.breakout_down_count >= self.params.breakout_confirmation and 
                  volume_ok and 
                  self.data.close[0] < low_breakout):
                self.sell()
                self.entry_price = self.data.close[0]
                self.stop_loss_price = self.entry_price + self.atr[0] * self.params.stop_loss_atr_multiplier
                self.take_profit_price = self.entry_price - self.atr[0] * self.params.take_profit_atr_multiplier
        
        else:
            current_price = self.data.close[0]
            
            if self.position.size > 0:  # 多头
                # 止盈或止损
                if current_price <= self.stop_loss_price or current_price >= self.take_profit_price:
                    self.close()
            
            else:  # 空头
                # 止盈或止损
                if current_price >= self.stop_loss_price or current_price <= self.take_profit_price:
                    self.close()
                    

if __name__ == '__main__':
    cerebro = run_strategy(BreakoutReversalStrategy, symbol='INTC', start_date='2023-01-01', end_date='2024-06-30',
                           sizer='fixed', sizer_params={'stake': 100})
    # 绘制图表
    cerebro.plot(style='candle')