import backtrader as bt
from backtrader_plotting import Bokeh
from backtrader_plotting.schemes import Tradimo
import yfinance as yf
from utils.fetch_data import get_yfinance_data


class SmaCross(bt.Strategy):
    # list of parameters which are configurable for the strategy
    params = dict(
        pfast=19,  # period for the fast moving average
        pslow=98   # period for the slow moving average
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
data = get_yfinance_data("INTL", "2014-01-01", "2025-11-30")

cerebro.adddata(data)  # Add the data feed

cerebro.addstrategy(SmaCross)  # Add the trading strategy
cerebro.run()  # run it all
cerebro.plot(style="lines")