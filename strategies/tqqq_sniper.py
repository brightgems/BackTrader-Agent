import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import backtrader as bt
from utils.base_strategy import BaseStrategy
from utils.runer import run_strategy

class TQQQSniperStrategy(BaseStrategy):
    params = (
        ('ma_period', 200),      # 200日均线 [1]
        ('entry_buffer', 1.04),  # 站上均线4%才入场 [1, 3]
        ('exit_buffer', 0.97),   # 跌破均线3%全清仓 [1, 3]
        ('dip_threshold', 0.99), # 单日回调超过1% [1]
        ('batch_size', 0.2),     # 20%仓位分批建仓 [1]
    )

    def __init__(self):
        BaseStrategy.__init__(self)
        # data0 是 QQQ (参照物)，data1 是 TQQQ (交易标的)
        self.qqq = self.datas[0]
        self.tqqq = self.datas[1]
        
        # 计算 QQQ 的 200日均线 [1]
        self.sma = bt.indicators.SimpleMovingAverage(self.qqq.close, period=self.params.ma_period)
        
        # 用于记录当前 TQQQ 的建仓进度
        self.current_pos_ratio = 0.0

    def next(self):
        # 获取当前 QQQ 价格和均线值
        qqq_price = self.qqq.close
        ma_val = self.sma
        
        # --- 防御清仓逻辑 ---
        # 只要 QQQ 价格跌破 200MA 再减 3% 的缓冲区，立即 100% 卖出 [1]
        if qqq_price < ma_val * self.params.exit_buffer:
            if self.getposition(self.tqqq).size > 0:
                self.close(data=self.tqqq)
                self.current_pos_ratio = 0.0
                print(f"清仓信号：QQQ跌破均线安全区，全仓撤退至现金 [1, 5]")
            return

        # --- 狙击买入逻辑 ---
        # 条件1：趋势要强（QQQ > 200MA + 4%）[1]
        trend_is_strong = qqq_price > ma_val * self.params.entry_buffer
        
        # 条件2：时机要准（单日回调超过 1%）[1]
        is_dip = qqq_price < self.qqq.close[-1] * self.params.dip_threshold
        
        if trend_is_strong and is_dip:
            # 如果还没建满仓（分 5 笔，每笔 20%）[1, 2]
            if self.current_pos_ratio < 1.0:
                # 计算目标仓位，确保不超过1.0
                target = min(self.current_pos_ratio + self.params.batch_size, 1.0)
                # 计算目标仓位对应的股数（仅针对分配给此策略的资金）
                # 注意：来源建议此策略占总资产的 25% [6]
                self.order_target_percent(data=self.tqqq, target=target)
                self.current_pos_ratio = target
                print(f"买入信号：趋势走强且回调，加仓 20%，当前仓位: {self.current_pos_ratio*100:.1f}% [1]")
                
if __name__ == "__main__":
    # 运行策略
    cerebo = run_strategy(TQQQSniperStrategy, symbol=['QQQ', 'TQQQ'], start_date='2010-01-01', end_date='2025-06-30')
    cerebo.plot()