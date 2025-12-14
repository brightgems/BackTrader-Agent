
import backtrader as bt
from utils.fetch_data import get_yfinance_data


def run_strategy(strategy, strategy_args={}, 
                 symbol='INTC', start_date='2023-01-01', end_date='2024-06-30',
                 initial_cash = 10000.0, commission=0.001,
                 sizer=None, sizer_params={}):
    """运行advisory信号策略演示"""
    print("=== LLM Advisory 信号交易策略演示 ===")
    
    cerebro = bt.Cerebro()
    
    # 设置初始参数
    
    cerebro.broker.setcash(initial_cash)
    cerebro.broker.setcommission(commission)
    
    # 添加数据
    print(f"获取 {symbol} 数据...")
    data = get_yfinance_data(symbol, start_date, end_date)
    cerebro.adddata(data)
    if sizer is not None:
        if sizer == 'fixed':
            cerebro.addsizer(bt.sizers.FixedSize, **sizer_params)
        elif sizer == 'fixed_reverser':
            cerebro.addsizer(bt.sizers.FixedReverser, **sizer_params)
        elif sizer == 'percent':
            cerebro.addsizer(bt.sizers.PercentSizer, **sizer_params)
        else:
            raise ValueError(f"Invalid sizer value: {sizer}. Must be one of ['fixed', 'fixed_reverser'].")
    # 添加策略 - 传递所有参数
    cerebro.addstrategy(strategy=strategy, 
                       *strategy_args)
    
    # 分析器
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name="sharpe")
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name="drawdown")
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name="trades")
    
    print("运行advisory信号策略回测...")
    results = cerebro.run()
    
    # 输出结果
    strat = results[0]
    final_value = cerebro.broker.getvalue()
    roi = (final_value - initial_cash) / initial_cash * 100
    
    print(f"\n策略结果:")
    print(f"起始资金: {initial_cash:,.2f}")
    print(f"最终资产: {final_value:,.2f}")
    print(f"总收益率: {roi:.2f}%")
    
    # 输出分析器结果
    sharpe = strat.analyzers.sharpe.get_analysis()
    drawdown = strat.analyzers.drawdown.get_analysis()
    
    sharpe_ratio = sharpe.get('sharperatio')
    print(f"夏普比率: {sharpe_ratio:.2f}" if sharpe_ratio is not None else "夏普比率: 无数据")
    
    max_drawdown = drawdown.get('max', {}).get('drawdown')
    print(f"最大回撤: {max_drawdown:.2f}%" if max_drawdown is not None else "最大回撤: 无数据")
    
    return cerebro
