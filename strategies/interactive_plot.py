import datetime
import backtrader as bt
from backtrader_plotting import Bokeh
import sys
from pathlib import Path
import sys
from lib.fetch_data import download_instrument_data


class TestStrategy(bt.Strategy):
    params = (
        ('buydate', 21),
        ('holdtime', 6),
    )

    def next(self):
        if len(self.data) == self.p.buydate:
            self.buy(self.datas[0], size=None)

        if len(self.data) == self.p.buydate + self.p.holdtime:
            self.sell(self.datas[0], size=None)


if __name__ == '__main__':
    cerebro = bt.Cerebro()

    cerebro.addstrategy(TestStrategy, buydate=3)
    filename = download_instrument_data("AAPL", "2022-01-01", "2024-12-31")
    data = bt.feeds.YahooFinanceCSVData(
        dataname=filename,
        # Do not pass values before this date
        fromdate=datetime.datetime(2000, 1, 1),
        # Do not pass values after this date
        todate=datetime.datetime(2001, 2, 28),
        reverse=False,
        )
    cerebro.adddata(data)
    cerebro.run()

    b = Bokeh(style='bar', plot_mode='single')
    cerebro.plot(b)