import datetime
import time
import backtrader as bt
import optuna

from strategies.ma_cross_over import SmaCross
from utils.fetch_data import get_yfinance_data


def objective(trial):
    # ✅ 整数参数（Optuna 原生支持）
    pfast = trial.suggest_int('pfast', 5, 30)
    pslow = trial.suggest_int('pslow', 40, 100)

    # 参数约束
    if pfast >= pslow:
        return -1e6

    cerebro = bt.Cerebro()
    cerebro.addstrategy(SmaCross, pfast=pfast, pslow=pslow)

    data = get_yfinance_data(
        'TSLA',
        datetime.datetime(2019, 1, 1),
        datetime.datetime(2024, 12, 31)
    )
    cerebro.adddata(data)

    cerebro.broker.setcash(10000)

    # 👉 用 SharpeRatio
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe', timeframe=bt.TimeFrame.Days,
    annualize=True)

    result = cerebro.run()
    sharpe = result[0].analyzers.sharpe.get_analysis().get('sharperatio')

    # Optuna 必须返回 float
    if sharpe is None:
        return -1e6

    return float(sharpe)


if __name__ == '__main__':
    start_time = time.time()

    study = optuna.create_study(direction='maximize')
    study.optimize(objective, n_trials=100, n_jobs=8)

    end_time = time.time()
    print(f"优化耗时: {(end_time - start_time)/60:.2f} 分钟")

    print("最优参数:", study.best_params)
    print("最优 Sharpe:", study.best_value)
