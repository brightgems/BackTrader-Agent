import backtrader as bt

class PercentSizer(bt.Sizer):
    params = (
        ('percents', 20),  # 默认使用20%的资金
    )
    
    def _getsizing(self, comminfo, cash, data, isbuy):
        if isbuy:
            # 计算买入数量
            price = data.close[0]
            position_value = cash * (self.p.percents / 100)
            size = int(position_value / price)
            
            # 确保size为正数且不超过最大可买数量
            max_size = int(cash / price)
            return min(size, max_size)
        else:
            # 卖出时使用全部持仓
            return self.broker.getposition(data).size

class RiskAwareSizer(bt.Sizer):
    """
    该Sizer根据每笔交易的风险水平调整头寸大小。
    Usage Example:
        添加资金管理Sizer
        cerebro.addsizer(bt.sizers.PercentSizer, percents=20)  # 每次使用20%的权益
    """
    params = (
        ('risk_per_trade', 0.01),  # 每笔交易风险1%
        ('stop_loss_pct', 0.05),   # 止损5%
    )
    
    def _getsizing(self, comminfo, cash, data, isbuy):
        if isbuy:
            price = data.close[0]
            if price <= 0 or cash <= 0 or self.p.stop_loss_pct <= 0:
                return 0
                
            stop_price = price * (1 - self.p.stop_loss_pct)
            risk_per_share = price - stop_price
            
            if risk_per_share <= 0:
                return 0
                
            position_size = (cash * self.p.risk_per_trade) / risk_per_share
            return max(0, int(position_size))
        else:
            position = self.broker.getposition(data)
            return position.size if position else 0