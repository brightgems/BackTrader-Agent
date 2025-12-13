import backtrader as bt
from backtrader_plotting import Bokeh
from backtrader_plotting.schemes import Tradimo
import yfinance as yf
from lib.fetch_data import download_yfinance_data


class SmaCross(bt.Strategy):
    # list of parameters which are configurable for the strategy
    params = dict(
        pfast=10,  # period for the fast moving average
        pslow=30   # period for the slow moving average
    )

    def __init__(self):
        sma1 = bt.ind.SMA(period=self.p.pfast)  # fast moving average
        sma2 = bt.ind.SMA(period=self.p.pslow)  # slow moving average
        self.crossover = bt.ind.CrossOver(sma1, sma2)  # crossover signal

    def next(self):
        # 获取当前可用资金
        cash = self.broker.getcash()
        current_price = self.data.close[0]
        
        # 按资金比例（例如20%）
        position_percent = 0.9
        size_by_percent = int((cash * position_percent) / current_price)
        if not self.position:  # not in the market
            if self.crossover > 0:  # if fast crosses slow to the upside
                self.order = self.buy(price=None, exectype=bt.Order.Market, size=size_by_percent)

        elif self.crossover < 0:  # in the market & cross to the downside
            self.close()  # close long position


cerebro = bt.Cerebro()  # create a "Cerebro" engine instance

# Create a data feed
data_file = download_yfinance_data("AAPL", "2022-01-01", "2024-12-31")
data = bt.feeds.GenericCSVData(
        dataname=data_file,
        dtformat=("%Y-%m-%d"),
        datetime=0,      # 第0列为日期时间
        close=1,         # 第1列为收盘价
        high=2,          # 第2列为最高价
        low=3,           # 第3列为最低价
        open=4,          # 第4列为开盘价
        volume=5,        # 第5列为成交量
        openinterest=-1, # 无持仓量数据
    )

cerebro.adddata(data)  # Add the data feed

cerebro.addstrategy(SmaCross)  # Add the trading strategy
cerebro.run()  # run it all
cerebro.plot()  # and plot it with a single command