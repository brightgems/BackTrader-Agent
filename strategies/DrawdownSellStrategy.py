import os
import sys
import backtrader as bt
from backtrader import *
from datetime import datetime

# 添加当前目录到Python路径，确保lib模块能正确导入
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from lib.fetch_data import download_yfinance_data
import pandas as pd

# 回撤控制策略 - 当资产回撤超过5%时卖出
class DrawdownSellStrategy(bt.Strategy):
    params = (
        ('drawdown_threshold', 5.0),  # 回撤阈值百分比
    )

    def log(self, txt, dt=None):
        # log记录函数
        dt = dt or self.datas[0].datetime.date(0)
        print('%s, %s' % (dt.isoformat(), txt))

    def __init__(self):
        # 默认数据，一般使用股票池当中，下标为0的股票
        self.dataclose = self.datas[0].close
        
        # 跟踪交易中的订单
        self.order = None
        self.buyprice = None
        self.buycomm = None
        
        # 资产最高值和当前回撤
        self.peak_value = 0.0
        self.current_drawdown = 0.0
        
        # 买入执行bar
        self.bar_executed = 0
        self.stop_win_price = 0.0

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return

        if order.status in [order.Completed]:
            if order.isbuy():
                self.log('买单执行BUY EXECUTED,成交价： %.2f,小计 Cost: %.2f,佣金 Comm %.2f'
                         % (order.executed.price, order.executed.value, order.executed.comm))
                self.buyprice = order.executed.price
                self.buycomm = order.executed.comm
                
                # 记录买入时的bar
                self.bar_executed = len(self)
                
                # 重置持仓后的峰值
                self.peak_value = self.broker.getvalue()
                
            elif order.issell():
                self.log('卖单执行SELL EXECUTED,成交价： %.2f,小计 Cost: %.2f,佣金 Comm %.2f'
                         % (order.executed.price, order.executed.value, order.executed.comm))

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('订单Order： 取消Canceled/保证金Margin/拒绝Rejected')

        self.order = None

    def notify_trade(self, trade):
        if not trade.isclosed:
            return
        self.log('交易利润OPERATION PROFIT, 毛利GROSS %.2f, 净利NET %.2f' %
                 (trade.pnl, trade.pnlcomm))

    def next(self):
        current_value = self.broker.getvalue()
        
        # 更新资产峰值
        if current_value > self.peak_value:
            self.peak_value = current_value
        
        # 计算当前回撤（百分比）
        if self.peak_value > 0:
            self.current_drawdown = ((self.peak_value - current_value) / self.peak_value) * 100
        else:
            self.current_drawdown = 0.0
            
        self.log('当前资产: %.2f, 峰值: %.2f, 回撤: %.2f%%' % 
                (current_value, self.peak_value, self.current_drawdown))

        # 检查订单执行情况
        if self.order:
            return

        # 检查当前持仓
        if not self.position:
            # 如果没有持仓，使用三连跌策略买入
            cash = self.broker.getcash()
            current_price = self.datas[0].close[0]
            
            position_percent = 0.9
            size_by_percent = int((cash * position_percent) / current_price)
            
            if len(self) > 21 and self.dataclose[-1] < self.dataclose[-21]:
                if self.dataclose[-1] / self.dataclose[-2] < 0.98 and self.dataclose[-2] / self.dataclose[-3] < 0.98:
                    self.log('设置买单 BUY CREATE, %.2f' % self.dataclose[0])
                    self.order = self.buy(size=size_by_percent)
                    self.stop_win_price = self.dataclose[0]
        else:
            # 如果有持仓，检查回撤是否超过阈值
            if self.current_drawdown >= self.params.drawdown_threshold:
                self.log('回撤超过 %.1f%%，设置卖单 SELL CREATE, %.2f' % 
                        (self.params.drawdown_threshold, self.dataclose[0]))
                self.order = self.close()
            
            # 同时保留原有的止盈逻辑
            elif self.dataclose[0] > self.stop_win_price * 1.5:
                self.log('止盈卖出，设置卖单 SELL CREATE, %.2f' % self.dataclose[0])
                self.order = self.sell(price=self.dataclose[0], size=self.position.size // 2//100*100)
                self.stop_win_price = self.dataclose[0]
            elif self.dataclose[0] > self.position.price * 2:
                self.log('止盈卖出，设置卖单 SELL CREATE, %.2f' % self.dataclose[0])
                self.order = self.close()

def run_drawdown_strategy():
    print('\n#1，设置 BT 量化回测程序入口')
    cerebro = bt.Cerebro()

    print('\n#2，设置BT回测初始参数及策略')
    print('\n\t#2-1，设置BT回测初始参数：起始资金等')
    dmoney0 = 100000.0
    cerebro.broker.setcash(dmoney0)
    dcash0 = cerebro.broker.startingcash

    print('\n\t#2-2，设置数据文件')
    symbol = 'GOOG'
    print('\t@数据代码：', symbol)

    t0stx, t9stx = datetime(2018, 1, 1), datetime(2025, 11, 30)
    dpath = download_yfinance_data(symbol, t0stx.strftime('%Y-%m-%d'), t9stx.strftime('%Y-%m-%d'))
    data = bt.feeds.GenericCSVData(dataname=dpath,
            dtformat=("%Y-%m-%d"),
            datetime=0,
            close=1,
            high=2,
            low=3,
            open=4,
            volume=5,
            openinterest=-1,
        )
    cerebro.adddata(data)

    print('\n\t#2-3，添加回撤控制策略')
    cerebro.addstrategy(DrawdownSellStrategy, drawdown_threshold=5.0)

    print('\n\t#2-4，设置经纪人佣金')
    cerebro.broker.setcommission(commission=0.001)

    print('\n#3，执行回测运算')
    cerebro.run()

    print('\n#4，完成回测运算')
    dval9 = cerebro.broker.getvalue()
    kret = (dval9 - dcash0) / dcash0 * 100

    print('\t起始资金Starting Portfolio Value:%.2f' % dcash0)
    print('\t资产总值Final Portfolio Value:%.2f' % dval9)
    print('\t投资回报率Return on investment: %.2f %%' % kret)

    print('\n#5，绘制分析图形')
    try:
        cerebro.plot(style='candlestick')
    except AttributeError as ex:
        print("绘图功能不可用，请检查Backtrader版本和matplotlib安装")
        raise ex

if __name__ == '__main__':
    run_drawdown_strategy()