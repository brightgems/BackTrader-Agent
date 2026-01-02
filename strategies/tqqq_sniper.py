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

"""
TQQQ 狙击手策略 - 多目标优化版本
策略逻辑：
1. 以 QQQ 为参照物，TQQQ 为交易标的
2. 当 QQQ 价格站上 200日均线 + 4% 才入场
3. 当 QQQ 价格跌破 200日均线 - 3% 全清仓
4. 当 QQQ 单日回调超过1%时，视为回调机会
5. 分批建仓，每次加仓20%，最多5次

可选标的：
- QQQ / TQQQ
- GLD / UGL
"""

class TQQQSniperStrategy(BaseStrategy):
    params = (
        ('ma_period', 200),      # 200日均线 [1]
        ('entry_buffer', 1.06),  # 站上均线4%才入场 [1, 3]
        ('exit_buffer', 0.93),   # 跌破均线3%全清仓 [1, 3]
        ('dip_threshold', 0.99), # 单日回调超过1% [1]
        ('batch_size', 0.25),     # 20%仓位分批建仓 [1]
        ('max_pos_pct', 0.95),     # 20%仓位分批建仓 [1]
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
                print(f"清仓信号：现金{self.broker.getcash():.2f}")
                self.close(data=self.tqqq)
                self.current_pos_ratio = 0.0
                print(f"清仓信号：QQQ跌破均线安全区，全仓撤退至现金{self.broker.getcash():.2f}")
            return

        # --- 狙击买入逻辑 ---
        # 条件1：趋势要强（QQQ > 200MA + 4%）[1]
        trend_is_strong = qqq_price > ma_val * self.params.entry_buffer
        
        # 条件2：时机要准（单日回调超过 1%）[1]
        is_dip = qqq_price < self.qqq.close[-1] * self.params.dip_threshold
        
        if trend_is_strong and is_dip:
            # 如果还没建满仓（分 5 笔，每笔 20%）[1, 2]
            if self.current_pos_ratio < self.params.max_pos_pct:
                # 计算目标仓位，确保不超过1.0
                target = min(self.current_pos_ratio + self.params.batch_size, self.params.max_pos_pct)
                # 计算目标仓位对应的股数（仅针对分配给此策略的资金）
                # 注意：来源建议此策略占总资产的 25% [6]
                self.order_target_percent(data=self.tqqq, target=target)
                self.current_pos_ratio = target
                print(f"买入信号：趋势走强且回调，加仓 {self.params.batch_size*100:.1f}%，当前仓位: {self.current_pos_ratio*100:.1f}% [1]")
                
def run_tqqq_strategy(strategy_args={}, symbol=['QQQ', 'TQQQ'], start_date='2010-01-01', end_date='2025-06-30'):
    # 运行策略
    cerebro = run_strategy(TQQQSniperStrategy, strategy_args=strategy_args, symbol=symbol, start_date=start_date, end_date=end_date)
    cerebro.plot()
    return cerebro



def objective(trial, args):
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
    batch_size = trial.suggest_float('batch_size', 0.1, 0.5)
    
    # 参数约束：入场缓冲必须大于出场缓冲
    if entry_buffer <= exit_buffer:
        return 0
    
    # 参数约束：入场缓冲必须大于1，出场缓冲必须小于1
    if entry_buffer <= 1.0 or exit_buffer >= 1.0:
        return 0

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
        args.fromdate,
        args.todate
    )
    tqqq_data = get_yfinance_data(
        args.stock1,
        args.fromdate,
        args.todate
    )
    
    cerebro.adddata(qqq_data)
    cerebro.adddata(tqqq_data)

    cerebro.broker.setcash(10000)

    # 添加多个性能指标
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe', timeframe=bt.TimeFrame.Days, annualize=True)
    cerebro.addanalyzer(bt.analyzers.AnnualReturn, _name='returns')
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')

    try:
        strats = cerebro.run()
        strat = strats[0]
        
        # 获取各项指标
        sharpe_ratio = strat.analyzers.sharpe.get_analysis().get('sharperatio', 0)
        returns_analysis = strat.analyzers.returns.get_analysis()
        annual_return = returns_analysis.get('rnorm100', 0)  # 年化收益率百分比
        
        trades_analysis = strat.analyzers.trades.get_analysis()
        total_trades = trades_analysis.get('total', {}).get('total', 0)
        print("总交易次数:", total_trades)
        win_rate = trades_analysis.get('won', {}).get('total', 0) / max(total_trades, 1)
        drawdown = strat.analyzers.drawdown.get_analysis()
        max_drawdown = drawdown.get('max', {}).get('drawdown', 100)  # 最大回撤
        # 处理缺失值
        sharpe_ratio = sharpe_ratio if sharpe_ratio is not None else -2
        annual_return = annual_return if annual_return is not None else -100
        
        # 如果夏普比率为None，返回一个较差的值
        # # 设置约束条件（硬性要求）: 最大回撤超过30%，直接淘汰
        # if max_drawdown > 30 or total_trades < 6:  
        #     return 0
        # if annual_return < 0:  # 负收益
        #     return -1e5 + annual_return
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
    print("开始 TQQQ Sniper 策略多目标优化（夏普比率 + 平均年化收益率）...")
    print("优化目标权重：夏普比率 60%，年化收益率 40%")
    
    study.optimize(lambda trial: objective(trial, args), n_trials=100, n_jobs=6)  # 减少试次数，提高稳定性

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
    print("最优组合得分（夏普比率）:", study.best_value)
    
    # 显示最佳试验的详细信息
    best_trial = study.best_trial
    print(f"最佳试验编号: {best_trial.number}")
    print(f"试验开始时间: {best_trial.datetime_start}")
    print(f"试验结束时间: {best_trial.datetime_complete}")
    
    # 显示所有试验结果的统计信息
    print(f"\n所有试验统计:")
    print(f"已完成试验数: {len(study.trials)}")
    
    # 显示最佳试验的详细指标
    print(f"\n最佳试验详细指标:")
    # 运行一次最佳参数获取详细指标
    from copy import deepcopy
    best_params = deepcopy(study.best_params)
    
    # 创建一个临时函数来获取详细指标
    def get_detailed_metrics(params):
        cerebro = bt.Cerebro()
        cerebro.addstrategy(TQQQSniperStrategy, **params)

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

        cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe', timeframe=bt.TimeFrame.Days, annualize=True)
        cerebro.addanalyzer(bt.analyzers.AnnualReturn, _name='annual_return')
        cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
        cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')

        result = cerebro.run()
        
        sharpe = result[0].analyzers.sharpe.get_analysis().get('sharperatio', 0)
        annual_return_data = result[0].analyzers.annual_return.get_analysis()
        avg_annual_return = sum(annual_return_data.values()) / len(annual_return_data) if annual_return_data else 0
        
        return {
            'sharpe': sharpe,
            'avg_annual_return': avg_annual_return,
            'final_value': cerebro.broker.getvalue()
        }
    
    metrics = get_detailed_metrics(best_params)
    print(f"夏普比率: {metrics['sharpe']:.4f}")
    print(f"平均年化收益率: {metrics['avg_annual_return']:.4f} ({metrics['avg_annual_return']*100:.2f}%)")
    print(f"最终资产价值: {metrics['final_value']:.2f}")
    
    # 显示前3个最佳参数组合
    trials_df = study.trials_dataframe()
    if len(trials_df) > 0:
        sorted_trials = trials_df.nlargest(3, 'value')
        print("\n前三名参数组合:")
        
        # 获取实际存在于DataFrame中的参数列
        available_columns = []
        param_keys = list(study.best_params.keys())
        for param in param_keys:
            param = f'params_{param}'
            if param in trials_df.columns:
                available_columns.append(param)
        
        # 只显示存在的列
        if available_columns:
            display_columns = ['number', 'value'] + available_columns
            print(sorted_trials[display_columns])
        else:
            print("无可用参数列显示")

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
                        default='2010-01-01',
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

    parser.add_argument('--plot', '-p', default=False, action='store_true',
                        help='Plot the read data')
    
    parser.add_argument('--optimize', '-o', default=False, action='store_true',
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
