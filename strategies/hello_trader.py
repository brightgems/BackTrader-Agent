import backtrader as bt
from backtrader_plotting import Bokeh
from backtrader_plotting.schemes import Tradimo
import yfinance as yf
import sys
from pathlib import Path

# 添加lib目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent))

# 从lib目录导入
from utils.fetch_data import get_yfinance_data

# 或者使用内置的Sizer
class FixedPercentSizer(bt.sizers.PercentSizer):
    params = (
        ('percents', 20),  # 使用20%的权益
    )
    
class SmaCross(bt.Strategy):
    params = dict(
        pfast=10,
        pslow=30,
        max_position_percent=0.20,  # 最大仓位20%
        min_position_value=1000,    # 最小交易金额
    )

    def __init__(self):
        sma1 = bt.ind.SMA(period=self.p.pfast)
        sma2 = bt.ind.SMA(period=self.p.pslow)
        self.crossover = bt.ind.CrossOver(sma1, sma2)

    def next(self):
        if not self.position:
            if self.crossover > 0:
                self.calculate_and_buy()
        else:
            if self.crossover < 0:
                self.sell()
                
    def calculate_and_buy(self):
        cash = self.broker.getcash()
        price = self.data.close[0]
        
        # 计算最大可买数量
        max_position_value = cash * self.p.max_position_percent
        
        # 确保交易金额大于最小值
        if max_position_value < self.p.min_position_value:
            print(f"资金不足，需要至少{self.p.min_position_value}，当前可用{max_position_value}")
            return
        
        # 计算买入数量
        size = int(max_position_value / price)
        
        # 确保至少买入1股
        if size < 1:
            size = 1
        
        # 下单
        self.order = self.buy(size=size)
    

    def notify_order(self, order):
        if order.status in [order.Completed]:
            if order.isbuy():
                print(f'买入: 价格={order.executed.price:.2f}, '
                      f'数量={order.executed.size}, '
                      f'成本={order.executed.value:.2f}, '
                      f'佣金={order.executed.comm:.2f}')
            else:
                print(f'卖出: 价格={order.executed.price:.2f}, '
                      f'数量={order.executed.size}, '
                      f'收入={order.executed.value:.2f}, '
                      f'佣金={order.executed.comm:.2f}')
            self.order = None

def run_cerebro():
    """运行backtrader回测引擎
    
    Returns:
        第一个策略实例的返回结果
    """
    # 初始化Cerebro回测引擎
    cerebro = bt.Cerebro()
    # 设置初始资金为10000
    cerebro.broker.setcash(10000)

    # 设置交易佣金率为0.075%
    cerebro.broker.setcommission(commission=0.00075)
    # 设置滑点率为0.1%
    # cerebro.broker.set_slippage(slippage=0.001)
    # 使用自定义的百分比仓位管理
    cerebro.addsizer(FixedPercentSizer)

    # --- FIX 必须确保列名正确 ---
    # 加载CSV数据文件，指定列名映射
    data = get_yfinance_data(code="MSFT", start_date="2022-01-01", end_date="2024-12-31")
    # 添加数据到回测引擎
    cerebro.adddata(data)
    # 添加SMA交叉策略
    cerebro.addstrategy(SmaCross)

    # 运行回测，只运行一次
    result = cerebro.run()
    # --- FIX bokeh plot 正常工作 ---
    # 创建Bokeh图表，使用柱状图样式，单图模式
    # b = Bokeh(style="bar", plot_mode="single")
    # 绘制图表
    cerebro.plot()

    # 返回第一个策略实例的结果
    return result[0]


if __name__ == "__main__":
    strat = run_cerebro()
    print("Final Value:", strat.broker.getvalue())
