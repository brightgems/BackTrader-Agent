import os
import backtrader as bt
from backtrader import *
from datetime import datetime
from lib.fetch_data import download_instrument_data
import pandas as pd

# Create a subclass of Strategy to define the indicators and logic
class TripleDropStrategy(bt.Strategy):
    def log(self, txt, dt=None):
        # log记录函数
        dt = dt or self.datas[0].datetime.date(0)
        print('%s, %s' % (dt.isoformat(), txt))

    def __init__(self):
        # 默认数据，一般使用股票池当中，下标为0的股票，
        # 通常使用close收盘价，作为主要分析数据字段
        self.dataclose = self.datas[0].close

        # 跟踪track交易中的订单（pending orders），成交价格，佣金费用
        self.order = None
        self.buyprice = None
        self.buycomm = None

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            # 检查订单执行状态order.status：
            # Buy/Sell order submitted/accepted to/by broker
            # broker经纪人：submitted提交/accepted接受,Buy买单/Sell卖单
            # 正常流程，无需额外操作
            return

        # 检查订单order是否完成
        # 注意: 如果现金不足，经纪人broker会拒绝订单reject order
        # 可以修改相关参数，调整进行空头交易
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log('买单执行BUY EXECUTED,成交价： %.2f,小计 Cost: %.2f,佣金 Comm %.2f'
                         % (order.executed.price,order.executed.value,order.executed.comm))
                self.buyprice = order.executed.price
                self.buycomm = order.executed.comm
            elif order.issell():
                self.log('卖单执行SELL EXECUTED,成交价： %.2f,小计 Cost: %.2f,佣金 Comm %.2f'
                         % (order.executed.price,order.executed.value,order.executed.comm))

            self.bar_executed = len(self)

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('订单Order： 取消Canceled/保证金Margin/拒绝Rejected')

        # 检查完成，没有交易中订单（pending order）
        self.order = None

    def notify_trade(self, trade):
        # 检查交易trade是关闭
        if not trade.isclosed:
            return

        self.log('交易利润OPERATION PROFIT, 毛利GROSS %.2f, 净利NET %.2f' %
                 (trade.pnl, trade.pnlcomm))

    def next(self):
        # next函数是最重要的trade交易（运算分析）函数，
        # 调用log函数，输出BT回溯过程当中，工作节点数据包BAR，对应的close收盘价
        self.log('收盘价Close, %.2f' % self.dataclose[0])

        # 检查订单执行情况，默认每次只能执行一张order订单交易，可以修改相关参数，进行调整
        if self.order:
            return

        # 检查当前股票的仓位position
        if not self.position:
            # 如果该股票仓位为0 ，可以进行BUY买入操作，
            # 这个仓位设置模式，也可以修改相关参数，进行调整
            # 使用经典的"三连跌"买入策略
            cash = self.broker.getcash()
            current_price = self.data.close[0]
            
            # 按资金比例（例如20%）
            position_percent = 0.9
            size_by_percent = int((cash * position_percent) / current_price)
            if len(self) > 21 and self.dataclose[-1] < self.dataclose[-21]:
                # 当前close价格，低于昨天（前一天，[-1]）
                if self.dataclose[-1] < self.dataclose[-2]:
                    # 昨天的close价格（前一天，[-1]），低于前天（前两天，[-2]）
                    # "三连跌"买入信号成立:
                    # BUY, BUY, BUY!!!，买！买！买！使用默认参数交易：数量、佣金等
                    self.log('设置买单 BUY CREATE, %.2f' % self.dataclose[0])
                    # 采用track模式，设置order订单，回避第二张订单2nd order，连续交易问题
                    self.order = self.buy(size=size_by_percent)

        else:
            # 如果该股票仓位>0 ，可以进行SELL卖出操作
            if len(self) >= ( self.bar_executed + 1) and  (self.dataclose[0] > self.position.price * 1.13  or \
                self.dataclose[0] < self.position.price * 0.95):
                # SELL, SELL, SELL!!! 卖！卖！卖！
                # 默认卖出该股票全部数额，使用默认参数交易：数量、佣金等
                self.log('设置卖单SELL CREATE, %.2f' % self.dataclose[0])

                # 采用track模式，设置order订单，回避第二张订单2nd order，连续交易问题
                self.order = self.close()

print('\n#1，设置 BT 量化回测程序入口')
cerebro = bt.Cerebro()  # create a "Cerebro" engine instance

print('\n#2，设置BT回测初始参数及策略')
print('\n\t#2-1，设置BT回测初始参数：起始资金等')
dmoney0 = 100000.0
cerebro.broker.setcash(dmoney0)
dcash0 = cerebro.broker.startingcash

print('\n\t#2-2，设置数据文件，需要按时间字段正序排序')
print('\t 使用 lib.fetch_data.download_instrument_data 下载数据（替换原 CSV 文件）')
symbol = '002046.SZ'
print('\t@数据代码：', symbol)

print('\t 设置数据BT回测运算：起始时间、结束时间')
print('\t 数据文件，可以是股票期货、外汇黄金、数字货币等交易数据')
print('\t 格式为：标准OHLC格式，可以是日线、分时数据')

t0stx,t9stx = datetime(2018, 1, 1),datetime(2025, 11, 30)
dpath = download_instrument_data(symbol, t0stx.strftime('%Y-%m-%d'), t9stx.strftime('%Y-%m-%d'))
data = bt.feeds.GenericCSVData(dataname=dpath,
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


print('\n\t#2-3，添加BT量化回测程序，对应的策略参数')
cerebro.addstrategy(TripleDropStrategy)

print('\n\t#2-4，添加broker经纪人佣金，默认为：千一')
cerebro.broker.setcommission(commission=0.001)

print('\n#3，调用BT回测入口程序，开始执行run量化回测运算')
print('\t注意输出信息的变化，增加了佣金信息')      
cerebro.run()

print('\n#4，完成BT量化回测运算')
dval9 = cerebro.broker.getvalue()
kret=(dval9-dcash0)/dcash0*100

print('\t 起始资金Starting Portfolio Value:%.2f' % dcash0)
print('\t 资产总值Final Portfolio Value:%.2f' % dval9)
print('\t ROI投资回报率Return on investment: %.2f %%' % kret)

print('\n#5，绘制BT量化分析图形')
print('\t 注意图形当中最上面的现金、资产曲线')
print('\t 注意图形当中的买点图标，以及对应的正负收益图标')
try:
    cerebro.plot(style='candlestick')  # 使用更明确的绘图风格
except AttributeError as ex:
    print("绘图功能不可用，请检查Backtrader版本和matplotlib安装")
    raise ex
