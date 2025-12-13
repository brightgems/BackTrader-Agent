import datetime
import time
import backtrader as bt
import optuna

from strategies.pair_trading import SafePairTradingStrategy
from utils.fetch_data import get_yfinance_data

STOCK0 = 'NVDA'
STOCK1 = 'AMD'

def objective(trial):
    # z-score 阈值参数优化
    zentry = trial.suggest_float('zentry', 1.5, 3.0)
    zexit = trial.suggest_float('zexit', 0.0, 1.0)
    period = trial.suggest_int('period', 5, 30)

    cerebro = bt.Cerebro()
    cerebro.broker.setcash(10000)
    
    # 获取数据
    data0 = get_yfinance_data(STOCK0, datetime.datetime(2014,1,1), datetime.datetime(2024,12,31))
    data0._name = STOCK0
    cerebro.adddata(data0)

    data1 = get_yfinance_data(STOCK1, datetime.datetime(2014,1,1), datetime.datetime(2024,12,31))
    data1._name = STOCK1
    cerebro.adddata(data1)

    # 添加策略
    cerebro.addstrategy(SafePairTradingStrategy, period=period, zentry=zentry, zexit=zexit)

    # 添加分析器
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe', timeframe=bt.TimeFrame.Days, annualize=True)

    try:
        result = cerebro.run()
        sharpe = result[0].analyzers.sharpe.get_analysis().get('sharperatio')
        if sharpe is None:
            return -1e6
        return float(sharpe)
    except Exception as e:
        print("回测异常:", e)
        return -1e6

if __name__ == '__main__':
    start_time = time.time()
    study = optuna.create_study(direction='maximize')
    study.optimize(objective, n_trials=50, n_jobs=1)  # n_jobs>1可能出问题

    end_time = time.time()
    print(f"优化耗时: {(end_time - start_time)/60:.2f} 分钟")
    print("最优参数:", study.best_params)
    print("最优 Sharpe:", study.best_value)
