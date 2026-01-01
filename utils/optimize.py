import backtrader as bt
import numpy as np
from scipy.optimize import differential_evolution


class NormalizedMultiObjectiveOptimizer:
    """多目标优化器 - 使用Min-Max归一化"""
    
    def __init__(self, data, initial_cash=100000):
        self.data = data
        self.initial_cash = initial_cash
        
        # 定义各指标的合理范围（根据实际情况调整）
        self.sharpe_range = (-1, 3)
        self.return_range = (-30, 100)
        self.dd_range = (0, 60)
        
        # 权重配置
        self.weights = {
            'sharpe': 0.4,
            'return': 0.3,
            'drawdown': 0.3
        }
    
    def normalize_value(self, value, min_val, max_val):
        """Min-Max归一化到[0, 1]"""
        normalized = (value - min_val) / (max_val - min_val)
        return np.clip(normalized, 0, 1)
    
    def objective_function(self, params):
        """归一化的目标函数"""
        fast_period, slow_period, rsi_period = [int(x) for x in params]
        
        # 参数有效性检查
        if fast_period >= slow_period or fast_period < 5 or rsi_period < 5:
            return 1e6
        
        try:
            cerebro = bt.Cerebro()
            cerebro.addstrategy(
                MultiObjectiveStrategy,
                fast_period=fast_period,
                slow_period=slow_period,
                rsi_period=rsi_period
            )
            cerebro.adddata(self.data)
            cerebro.broker.setcash(self.initial_cash)
            cerebro.broker.setcommission(commission=0.001)
            
            # 添加分析器
            cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe', 
                              timeframe=bt.TimeFrame.Days, annualize=True, riskfreerate=0.02)
            cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
            cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
            
            result = cerebro.run()
            
            # 提取指标
            sharpe = result[0].analyzers.sharpe.get_analysis().get('sharperatio')
            sharpe = 0 if sharpe is None else float(sharpe)
            
            returns_analysis = result[0].analyzers.returns.get_analysis()
            annual_return = returns_analysis.get('rnorm100', 0)
            annual_return = 0 if annual_return is None else float(annual_return)
            
            drawdown_analysis = result[0].analyzers.drawdown.get_analysis()
            max_dd = abs(drawdown_analysis.get('max', {}).get('drawdown', 100))
            
            # 归一化各指标
            sharpe_norm = self.normalize_value(sharpe, *self.sharpe_range)
            return_norm = self.normalize_value(annual_return, *self.return_range)
            dd_norm = self.normalize_value(
                self.dd_range[1] - max_dd,  # 回撤越小越好
                0, 
                self.dd_range[1]
            )
            
            # 计算综合得分
            score = (
                self.weights['sharpe'] * sharpe_norm +
                self.weights['return'] * return_norm +
                self.weights['drawdown'] * dd_norm
            )
            
            # 打印调试信息
            print(f"参数: fast={fast_period}, slow={slow_period}, rsi={rsi_period}")
            print(f"  原始值: Sharpe={sharpe:.3f}, Return={annual_return:.2f}%, DD={max_dd:.2f}%")
            print(f"  归一化: Sharpe={sharpe_norm:.3f}, Return={return_norm:.3f}, DD={dd_norm:.3f}")
            print(f"  综合得分: {score:.4f}\n")
            
            return -score  # 最大化score = 最小化-score
            
        except Exception as e:
            print(f"策略运行出错: {e}")
            return 1e6
    
    def optimize(self, bounds=None):
        """执行优化"""
        if bounds is None:
            raise ValueError("必须提供参数边界(bounds)进行优化。")
        
        print("开始多目标优化（归一化版本）...")
        print(f"权重配置: {self.weights}")
        print(f"指标范围: Sharpe{self.sharpe_range}, Return{self.return_range}, DD{self.dd_range}\n")
        
        result = differential_evolution(
            self.objective_function,
            bounds,
            maxiter=30,
            popsize=10,
            seed=42,
            polish=False
        )
        
        return result