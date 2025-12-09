import backtrader as bt
import pandas as pd


class ReplayStrategy(bt.Strategy):
    params = (
        ('print_replay', True),
    )
    
    def __init__(self):
        self.last_bar_time = None
        
    def next(self):
        # 当前时间
        current_time = self.data.datetime.datetime()
        
        # 检查是否是新的bar
        if self.last_bar_time != current_time:
            if self.p.print_replay:
                print(f"=== 新Bar形成: {current_time} ===")
                print(f"开盘: {self.data.open[0]:.2f}")
                print(f"最高: {self.data.high[0]:.2f}")
                print(f"最低: {self.data.low[0]:.2f}")
                print(f"收盘: {self.data.close[0]:.2f}")
                print(f"成交量: {self.data.volume[0]}")
            
            self.last_bar_time = current_time

def run():
    # 创建Cerebro引擎
    cerebro = bt.Cerebro()
    
    # 添加策略
    cerebro.addstrategy(ReplayStrategy, print_replay=True)
    
    # 创建模拟的1分钟数据
    dates = pd.date_range('2023-01-01 09:30', '2023-01-01 10:00', freq='1min')
    data = pd.DataFrame({
        'open': range(100, 100 + len(dates)),
        'high': range(105, 105 + len(dates)),
        'low': range(95, 95 + len(dates)),
        'close': range(102, 102 + len(dates)),
        'volume': [1000] * len(dates)
    }, index=dates)
    
    # 创建数据馈送
    feed = bt.feeds.PandasData(
        dataname=data,
        timeframe=bt.TimeFrame.Minutes,
        compression=1
    )
    
    # 转换为5分钟回放
    replay_feed = cerebro.replaydata(
        feed,
        timeframe=bt.TimeFrame.Minutes,
        compression=5
    )
    
    # 添加数据
    cerebro.adddata(replay_feed)
    
    # 运行回放
    cerebro.run()
    
if __name__ == '__main__':
    run()