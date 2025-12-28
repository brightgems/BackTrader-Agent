# coding: utf-8
import argparse
import datetime
import backtrader as bt
import backtrader.indicators as btind
from utils.fetch_data import get_yfinance_data

class SafePairTradingStrategy(bt.Strategy):
    params = dict(
        period=25,           # OLS/滚动窗口
        zentry=2.43,          # 开仓阈值
        zexit=0.75,           # 平仓阈值
        stake=10,            # 每次开仓最小股数
        printout=True
    )

    def log(self, txt, dt=None):
        if self.p.printout:
            dt = dt or self.data0.datetime[0]
            dt = bt.num2date(dt)
            print(f'{dt.isoformat()}, {txt}')

    def __init__(self):
        # OLS 计算残差
        self.ols = btind.OLS_TransformationN(self.data0, self.data1, period=self.p.period)
        spread = self.data0.close - self.ols
        self.zscore = (spread - btind.SMA(spread, period=self.p.period)) / btind.StdDev(spread, period=self.p.period)

        # 当前持仓状态: 0=无仓位, 1=short spread, 2=long spread
        self.status = 0

    def next(self):
        z = self.zscore[0]

        # 获取当前账户净值，计算每条腿可分配资金
        cash = self.broker.getvalue() * 0.5
        size0 = max(int(cash / self.data0.close[0]), self.p.stake)
        size1 = max(int(cash / self.data1.close[0]), self.p.stake)

        # 平仓逻辑
        if self.status != 0 and abs(z) < self.p.zexit:
            self.log(f'CLOSE POSITION, zscore={z:.2f}')
            self.close(data=self.data0)
            self.close(data=self.data1)
            self.status = 0
            return

        # 开仓逻辑
        if z > self.p.zentry and self.status != 1:
            # short spread: sell data0, buy data1
            self.log(f'SHORT SPREAD, zscore={z:.2f}, SELL {size0} of {self.data0._name}, BUY {size1} of {self.data1._name}')
            self.sell(data=self.data0, size=size0)
            self.buy(data=self.data1, size=size1)
            self.status = 1

        elif z < -self.p.zentry and self.status != 2:
            # long spread: buy data0, sell data1
            self.log(f'LONG SPREAD, zscore={z:.2f}, BUY {size0} of {self.data0._name}, SELL {size1} of {self.data1._name}')
            self.buy(data=self.data0, size=size0)
            self.sell(data=self.data1, size=size1)
            self.status = 2

    def stop(self):
        start = self.broker.startingcash
        end = self.broker.getvalue()
        print('==============================')
        print(f'Starting Value: {start:.2f}')
        print(f'Ending   Value: {end:.2f}')
        print('==============================')


def run_strategy(stock0='PEP', stock1='KO',
                 fromdate='2014-01-01', todate='2024-12-31',
                 cash=10000, comm=0.005, plot=False):

    cerebro = bt.Cerebro()
    cerebro.broker.setcash(cash)
    cerebro.broker.setcommission(commission=comm)

    # 获取数据
    d0 = get_yfinance_data(stock0, datetime.datetime.strptime(fromdate, '%Y-%m-%d'),
                                  datetime.datetime.strptime(todate, '%Y-%m-%d'))
    d0._name = stock0
    cerebro.adddata(d0)

    d1 = get_yfinance_data(stock1, datetime.datetime.strptime(fromdate, '%Y-%m-%d'),
                                  datetime.datetime.strptime(todate, '%Y-%m-%d'))
    d1._name = stock1
    cerebro.adddata(d1)

    # 添加策略
    cerebro.addstrategy(SafePairTradingStrategy)

    # 运行回测
    cerebro.run()
    if plot:
        cerebro.plot()

def parse_args():
    parser = argparse.ArgumentParser(description='MultiData Strategy')

    parser.add_argument('--stock0', '-s0',
                        default='NVDA',
                        help='1st data into the system')

    parser.add_argument('--stock1', '-s1',
                        default='AMD',
                        help='2nd data into the system')

    parser.add_argument('--fromdate', '-f',
                        default='2014-01-01',
                        help='Starting date in YYYY-MM-DD format')

    parser.add_argument('--todate', '-t',
                        default='2024-12-31',
                        help='Starting date in YYYY-MM-DD format')

    parser.add_argument('--period', default=10, type=int,
                        help='Period to apply to the Simple Moving Average')

    parser.add_argument('--cash', default=10000, type=int,
                        help='Starting Cash')

    parser.add_argument('--commperc', default=0.005, type=float,
                        help='Percentage commission (0.005 is 0.5%%')

    parser.add_argument('--stake', default=10, type=int,
                        help='Stake to apply in each operation')

    parser.add_argument('--plot', '-p', default=True, action='store_true',
                        help='Plot the read data')

    return parser.parse_args()

if __name__ == '__main__':
    args = parse_args()
    run_strategy(stock0=args.stock0,
                 stock1=args.stock1,
                 fromdate=args.fromdate,
                 todate=args.todate,
                 cash=args.cash,
                 comm=args.commperc,
                 plot=args.plot)
    
    
    