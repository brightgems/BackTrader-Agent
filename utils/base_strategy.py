import backtrader as bt


class BaseStrategy(bt.Strategy):
    """基于LLM Advisory信号的全新交易策略"""
    
    params = (
        ("print_log", True),
        ("broker_starting_cash", 10000),  # 每次交易股数
    )
    
    def log(self, txt, dt=None):
        """日志记录"""
        if self.params.print_log:
            dt = dt or self.datas[0].datetime.date(0)
            print(f"{dt.isoformat()}, {txt}")

    def __init__(self):
        self.order = None
        self.trade_count = 0
        
    def notify_order(self, order):
        """订单处理"""
        if order.status in [order.Submitted, order.Accepted]:
            return  # 订单已提交或接受，无需操作
        
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(f"多头信号 - 买入成交: {order.executed.price:.2f}, 数量: {order.executed.size}")
            else:
                self.log(f"空头信号 - 卖出成交: {order.executed.price:.2f}, 数量: {order.executed.size}")
            
            self.trade_count += 1
            
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log(f"订单失败: {order.status}")
            
        self.order = None
        
    def notify_trade(self, trade):
        # 检查交易trade是关闭
        if not trade.isclosed:
            return

        self.log(
            "交易操盘利润OPERATION PROFIT, 毛利GROSS %.2f, 净利NET %.2f"
            % (trade.pnl, trade.pnlcomm)
        )
        
    def stop(self):
        """结束时的统计"""
        final_value = self.broker.getvalue()
        initial_cash = self.params.broker_starting_cash
        
        self.log(f"策略结束 - 最终资产: {final_value:.2f}")
        self.log(f"总交易次数: {self.trade_count}")
        self.log(f"收益率: {(final_value - initial_cash) / initial_cash * 100:.2f}%")

