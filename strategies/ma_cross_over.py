import backtrader as bt
from backtrader_plotting import Bokeh
from backtrader_plotting.schemes import Tradimo
import yfinance as yf
from utils.fetch_data import get_yfinance_data, get_tushare_data


class SmaCross(bt.Strategy):
    # list of parameters which are configurable for the strategy
    params = dict(
        pfast=14,  # period for the fast moving average
        pslow=43   # period for the slow moving average
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

def run_backtest(plot=True):
    cerebro = bt.Cerebro()  # create a "Cerebro" engine instance

    # Create a data feed
    # data = get_yfinance_data("INTL", "2014-01-01", "2025-11-30")
    data = get_tushare_data("INTL", "2014-01-01", "2025-11-30")

    cerebro.adddata(data)  # Add the data feed

    cerebro.addstrategy(SmaCross)  # Add the trading strategy
    print("\n\t#2-6,设置addanalyzer分析参数")
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name="SharpeRatio", timeframe=bt.TimeFrame.Days,
        annualize=True)
    cerebro.addanalyzer(bt.analyzers.AnnualReturn, _name="AnnualReturn")
    #
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name="TradeAnalyzer")
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name="DW")

    results = cerebro.run()  # run it all
    print("\n#4,完成回测运算")
    print("\n#5,analyzer分析BT量化回测数据")
    strat = results[0]
    anzs = strat.analyzers
    #
    dsharp = anzs.SharpeRatio.get_analysis()["sharperatio"]
    #
    dw = anzs.DW.get_analysis()
    max_drowdown_len = dw["max"]["len"]
    max_drowdown = dw["max"]["drawdown"]
    max_drowdown_money = dw["max"]["moneydown"]
    print("\t5-1夏普指数SharpeRatio : ", dsharp)
    print("\t最大回撤周期 max_drowdown_len : ", max_drowdown_len)
    print("\t最大回撤 max_drowdown : ", max_drowdown)
    print("\t最大回撤(资金)max_drowdown_money : ", max_drowdown_money)
    if plot==True:
        cerebro.plot(style="lines")
    
if __name__ == '__main__':
    run_backtest()