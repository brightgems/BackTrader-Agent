import argparse
from datetime import datetime
import sys
import os
import time
import optuna
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.fetch_data import get_yfinance_data

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
                
def run_tqqq_strategy(strategy_args={}, symbol=['QQQ', 'TQQQ'], start_date='2010-01-01', end_date='2025-06-30'):
    # 运行策略
    cerebro = run_strategy(TQQQSniperStrategy, strategy_args=strategy_args, symbol=symbol, start_date=start_date, end_date=end_date)
    cerebro.plot()
    return cerebro



def objective(trial):
    # ✅ TQQQ Sniper 策略参数优化
    # 均线周期
    ma_period = trial.suggest_int('ma_period', 66, 300)  # 100-300日均线范围
    
    # 入场缓冲比例 (1.01-1.10 = 1%-10%)
    entry_buffer = trial.suggest_float('entry_buffer', 1.01, 1.10)
    
    # 出场缓冲比例 (0.90-0.99 = 1%-10% 下跌)
    exit_buffer = trial.suggest_float('exit_buffer', 0.90, 0.99)
    
    # 回调阈值 (0.95-0.995 = 0.5%-5% 回调)
    dip_threshold = trial.suggest_float('dip_threshold', 0.95, 0.995)
    
    # 批次大小 (0.1-0.3 = 10%-30% 仓位)
    batch_size = trial.suggest_float('batch_size', 0.1, 0.3)

    # 参数约束：入场缓冲必须大于出场缓冲
    if entry_buffer <= exit_buffer:
        return -1e6
    
    # 参数约束：入场缓冲必须大于1，出场缓冲必须小于1
    if entry_buffer <= 1.0 or exit_buffer >= 1.0:
        return -1e6

    cerebro = bt.Cerebro()
    cerebro.addstrategy(TQQQSniperStrategy, 
                      ma_period=ma_period,
                      entry_buffer=entry_buffer,
                      exit_buffer=exit_buffer,
                      dip_threshold=dip_threshold,
                      batch_size=batch_size)

    # 使用 QQQ 作为参照物，TQQQ 作为交易标的
    qqq_data = get_yfinance_data(
        args.stock0,
        datetime(2014, 1, 1),
        datetime(2024, 12, 31)
    )
    tqqq_data = get_yfinance_data(
        args.stock1,
        datetime(2014, 1, 1),
        datetime(2024, 12, 31)
    )
    
    cerebro.adddata(qqq_data)
    cerebro.adddata(tqqq_data)

    cerebro.broker.setcash(10000)

    # 添加多个性能指标
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe', timeframe=bt.TimeFrame.Days, annualize=True)
    cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')

    try:
        result = cerebro.run()
        sharpe_ratio = result[0].analyzers.sharpe.get_analysis().get('sharperatio')
        
        # 如果夏普比率为None，返回一个较差的值
        if sharpe_ratio is None:
            return -1e6

        return float(sharpe_ratio)
        
    except Exception as e:
        # 如果策略运行出错，返回一个较差的值
        print(f"策略运行出错: {e}")
        return -1e6


def optimize_strategy():
    """
    python  strategies\tqqq_sniper.py -s0 UNG -s1 UGAZ --fromdate 2010-01-01 --todate 2025-12-31 --cash 10000 --commperc 0.005 
    """
    start_time = time.time()
    study = optuna.create_study(direction='maximize')
    print("开始 TQQQ Sniper 策略参数优化...")
    
    study.optimize(objective, n_trials=50, n_jobs=1)  # 减少试次数，提高稳定性

    end_time = time.time()
    print(f"优化耗时: {(end_time - start_time)/60:.2f} 分钟")

    # 调用结果展示函数
    _display_optimization_results(study)

def _display_optimization_results(study):
    """
    展示优化结果详细信息
    
    参数:
        study (optuna.study.Study): Optuna 优化研究结果对象
    
    返回:
        无
    """
    print("\n=== TQQQ Sniper 策略优化结果 ===")
    print("最优参数:", study.best_params)
    print("最优 Sharpe 比率:", study.best_value)
    
    # 显示最佳试验的详细信息
    best_trial = study.best_trial
    print(f"最佳试验编号: {best_trial.number}")
    print(f"试验开始时间: {best_trial.datetime_start}")
    print(f"试验结束时间: {best_trial.datetime_complete}")
    
    # 显示所有试验结果的统计信息
    print(f"\n所有试验统计:")
    print(f"已完成试验数: {len(study.trials)}")
    
    # 显示前3个最佳参数组合
    trials_df = study.trials_dataframe()
    if len(trials_df) > 0:
        sorted_trials = trials_df.nlargest(3, 'value')
        print("\n前三名参数组合:")
        print(sorted_trials[['number', 'value'] + list(study.best_params.keys())])

def parse_args():
    parser = argparse.ArgumentParser(description='MultiData Strategy')

    parser.add_argument('--stock0', '-s0',
                        default='QQQ',
                        help='symbol of the reference data')

    parser.add_argument('--stock1', '-s1',
                        default='TQQQ',
                        help='symbol of the trading data')
    
    parser.add_argument('--period', default=200, type=int,
                        help='Period to apply to the Simple Moving Average')
    
    parser.add_argument('--fromdate', '-f',
                        default='2000-01-01',
                        help='Starting date in YYYY-MM-DD format')

    parser.add_argument('--todate', '-t',
                        default='2025-12-25',
                        help='Starting date in YYYY-MM-DD format')

    parser.add_argument('--cash', default=10000, type=int,
                        help='Starting Cash')

    parser.add_argument('--commperc', default=0.005, type=float,
                        help='Percentage commission (0.005 is 0.5%%')

    parser.add_argument('--stake_pct', default=20, type=int,
                        help='Stake to apply in each operation')

    parser.add_argument('--plot', '-p', default=True, action='store_true',
                        help='Plot the read data')
    
    parser.add_argument('--optimize', '-o', default=True, action='store_true',
                        help='Run optimization process for this strategy')

    return parser.parse_args()

if __name__ == '__main__':
    args = parse_args()
    if args.optimize:
        optimize_strategy()
    else:
        run_tqqq_strategy(strategy_args={'ma_period': args.period, 'batch_size': args.stake_pct / 100.0},
                 symbol=[args.stock0, args.stock1],
                 start_date=args.fromdate,
                 end_date=args.todate)
