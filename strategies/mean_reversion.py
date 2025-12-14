import backtrader as bt
from utils.runer import run_strategy
from utils.base_strategy import BaseStrategy

class MeanReversionStrategy(BaseStrategy):
    params = (
        ('threshold', 2.0),  # 标准差阈值
        ('stop_loss_pct', 0.7),  # 止损比例4%
        ('take_profit_pct', 0.25),  # 止盈比例12%
        ('trailing_stop_pct', 0.05),  # 移动止损比例2.5%
    )
    
    def __init__(self):
        BaseStrategy.__init__(self)
        self.sma = bt.ind.SMA(self.data.close, period=20)
        self.std = bt.ind.StdDev(self.data.close, period=20)
        self.zscore = (self.data.close - self.sma) / self.std
        self.stop_order = None
        self.take_profit_order = None
        self.trailing_stop_order = None
        
    def next(self):
        if not self.position:  # 无持仓
            if self.zscore[0] > self.params.threshold:  # 超买，准备做空
                self.sell()
            elif self.zscore[0] < -self.params.threshold:  # 超卖，准备做多
                self.buy()
        
        elif self.position.size > 0:  # 持有多头
            # 检查是否已经有止损止盈订单，如果没有则创建
            if not self.stop_order and not self.take_profit_order:
                entry_price = self.position.price
                self.stop_order = self.sell(exectype=bt.Order.Stop, 
                                          price=entry_price * (1 - self.params.stop_loss_pct))
                self.take_profit_order = self.sell(exectype=bt.Order.Limit, 
                                                 price=entry_price * (1 + self.params.take_profit_pct))
                self.trailing_stop_order = self.sell(exectype=bt.Order.StopTrail, 
                                                   trailamount=entry_price * self.params.trailing_stop_pct)
            
            if self.zscore[0] > 0:  # 价格回归，准备反转
                self.cancel_orders()
                self.sell()  # FixedReverser会自动卖2倍
                
        elif self.position.size < 0:  # 持有空头
            # 检查是否已经有止损止盈订单，如果没有则创建
            if not self.stop_order and not self.take_profit_order:
                entry_price = self.position.price
                self.stop_order = self.buy(exectype=bt.Order.Stop, 
                                         price=entry_price * (1 + self.params.stop_loss_pct))
                self.take_profit_order = self.buy(exectype=bt.Order.Limit, 
                                                price=entry_price * (1 - self.params.take_profit_pct))
                self.trailing_stop_order = self.buy(exectype=bt.Order.StopTrail, 
                                                  trailamount=entry_price * self.params.trailing_stop_pct)
            
            if self.zscore[0] < 0:  # 价格回归，准备反转
                self.cancel_orders()
                self.buy()  # FixedReverser会自动买2倍

    def cancel_orders(self):
        """取消所有待处理的订单"""
        if self.stop_order:
            self.cancel(self.stop_order)
            self.stop_order = None
        if self.take_profit_order:
            self.cancel(self.take_profit_order)
            self.take_profit_order = None
        if self.trailing_stop_order:
            self.cancel(self.trailing_stop_order)
            self.trailing_stop_order = None

if __name__ == '__main__':
    cerebro = run_strategy(MeanReversionStrategy, symbol='INTC', start_date='2023-01-01', end_date='2024-06-30',
                           sizer='fixed', sizer_params={'stake': 100})
    # 绘制图表
    cerebro.plot(style='candle')