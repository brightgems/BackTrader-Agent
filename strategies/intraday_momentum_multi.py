import datetime
import backtrader as bt
import akshare as ak
import pandas as pd
import matplotlib.pyplot as plt

# ==========================
# 1. 数据获取函数 (使用 Akshare)
# ==========================
def get_stock_data(symbol, start_date, end_date):
    """
    使用 akshare 获取 A股 分钟级数据
    注意：这里获取的是 1分钟 数据，用于模拟 5分钟 策略
    """
    print(f"正在下载 {symbol} 的数据...")
    
    # Akshare 获取分钟数据的接口
    # 交易市场 A股: 0, 深圳: 30, 上海: 60 (这里用通用接口)
    try:
        # 获取1分钟K线
        # adjust: "qfq" 前复权, "hfq" 后复权, "" 不复权
        df = ak.stock_zh_a_minute(symbol=symbol, period="5", adjust="qfq")
        
        # 数据清洗和列名映射
        df.columns = ['datetime', 'open', 'high', 'low', 'close', 'volume']
        
        # 转换数据类型：确保volume列是数值类型
        df['volume'] = pd.to_numeric(df['volume'], errors='coerce')
        df['datetime'] = pd.to_datetime(df['datetime'])
        
        # 处理可能的NaN值
        df.dropna(inplace=True)
        
        df.set_index('datetime', inplace=True)
        
        # 转换为 5分钟 K线 (因为策略基于5分钟)
        # 这里使用 resample 进行重采样
        df_5min = df.resample('5Min').agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }).dropna()
        
        df_5min.index = df_5min.index.astype('datetime64[ns]')
        print(f"成功获取到 {len(df_5min)} 条5分钟数据.从{df_5min.index.min()} 到 {df_5min.index.max()}")
        
        # 筛选日期范围
        if isinstance(start_date, str):
            start_date = pd.to_datetime(start_date)
        if isinstance(end_date, str):
            end_date = pd.to_datetime(end_date)
        df_5min = df_5min.loc[start_date:end_date]
        
        return df_5min
    
    except Exception as e:
        print(f"数据获取失败: {e}")
        return None

# ==========================
# 2. 策略定义
# ==========================
class First5MinBreakout(bt.Strategy):
    # 定义参数（平衡版本 - 推荐）
    params = (
        ('lookback_periods', 18), # 保持18根K线回看（1.5小时）
        ('vol_ratio_threshold', 1.25), # 适中的成交量阈值125%
        ('stop_loss', 0.025), # 2.5%止损平衡风险和收益
        ('take_profit', 0.025), # 2.5%止盈对称设置
        ('max_trades_per_day', 2), # 每日2次交易限制
    )

    def __init__(self):
        # --- 指标计算 ---
        # 简单移动平均用于辅助判断趋势(可选)
        self.sma = bt.indicators.SimpleMovingAverage(
            self.data.close, period=15)

        # 计算过去一段时间的平均成交量 (用于计算相对量能)
        # self.volume_ma 是过去N根K线的平均成交量
        self.volume_ma = bt.indicators.SimpleMovingAverage(
            self.data.volume, period=self.p.lookback_periods)
        
        # 计算量比: 当前成交量 / 过去平均成交量
        self.vol_ratio = self.data.volume / self.volume_ma

        # 用于标记是否是当天的第一个5分钟
        self.is_first_bar_of_day = True
        
        # 用于存储当天前5分钟的极值
        self.first_5min_high = None
        self.first_5min_low = None
        
        # 记录订单状态
        self.order = None

    def log(self, txt, dt=None):
        """ Logging function for this strategy"""
        dt = dt or self.data.datetime.date(0)
        print(f'{dt.isoformat()}, {txt}')

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return

        # 检查订单是否完成
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(f'【买入执行】价格: {order.executed.price}, 成本: {order.executed.value}, 手续费: {order.executed.comm}')
            elif order.issell():
                self.log(f'【卖出执行】价格: {order.executed.price}, 成本: {order.executed.value}, 手续费: {order.executed.comm}')

        self.order = None
    def next(self):
        # 如果有订单正在挂起，不执行新操作
        if self.order:
            return

        # 正确的数据访问方式：self.data.datetime 而不是 self.datas.datetime
        current_time = self.data.datetime.time(0)
        
        # --- 1. 每天开盘重置逻辑 ---
        # 记录当天第一根K线的极值
        if current_time.hour == 9 and current_time.minute <= 35:
            # 如果是当天前几个5分钟K线，记录极值
            if self.first_5min_high is None or self.is_first_bar_of_day:
                self.first_5min_high = self.data.high[0]
                self.first_5min_low = self.data.low[0]
                self.is_first_bar_of_day = True
            else:
                # 更新极值
                self.first_5min_high = max(self.first_5min_high, self.data.high[0])
                self.first_5min_low = min(self.first_5min_low, self.data.low[0])
        else:
            # 非开盘阶段，标记为False
            if self.is_first_bar_of_day:
                self.is_first_bar_of_day = False
                self.log(f'【开盘阶段结束】记录高点: {self.first_5min_high}, 低点: {self.first_5min_low}')

        # --- 2. 获取当前数据 ---
        price = self.data.close[0]
        high = self.data.high[0]
        low = self.data.low[0]
        
        # 调试信息：显示当前状态
        if len(self.data) % 100 == 0:  # 每100根K线输出一次调试信息
            self.log(f'【调试】当前价格: {price}, 开盘高点: {self.first_5min_high}, 开盘低点: {self.first_5min_low}, 量比: {self.vol_ratio[0]:.2f}')
        
        # --- 3. 过滤条件：相对成交量 ---
        # 只有当量比大于设定阈值时才考虑交易
        if self.vol_ratio[0] < self.p.vol_ratio_threshold:
            return # 量能不足，跳过

        # --- 4. 核心交易逻辑 ---
        # 必须已经过了开盘阶段，且已经记录了前5分钟极值
        if self.first_5min_high is not None and self.first_5min_low is not None and not self.is_first_bar_of_day:
            
            # 【做多逻辑】
            # 条件1: 价格突破前5分钟最高价
            if not self.position: # 如果没有持仓
                if high > self.first_5min_high:
                    self.log(f'【开多信号】当前价格 {price} 突破前5分钟高点 {self.first_5min_high}, 量比: {self.vol_ratio[0]:.2f}')
                    self.order = self.buy() # 买入开仓
            
            # 【做空逻辑】
            # 条件1: 价格跌破前5分钟最低价
            elif not self.position: # 修复逻辑：使用独立的if判断做空
                if low < self.first_5min_low:
                    self.log(f'【开空信号】当前价格 {price} 跌破前5分钟低点 {self.first_5min_low}, 量比: {self.vol_ratio[0]:.2f}')
                    self.order = self.sell() # 卖出开仓 (做空)

        # --- 5. 平仓逻辑 ---
        # 收盘前强制平仓（日内交易）
        if current_time.hour == 14 and current_time.minute >= 55:
            if self.position:
                self.log(f'【强制平仓】收盘前平仓，价格: {price}')
                self.order = self.close()

        # 止损止盈逻辑
        if self.position:
            entry_price = self.position.price
            if self.position.size > 0:  # 多仓
                # 止盈
                if price >= entry_price * (1 + self.p.take_profit):
                    self.log(f'【多仓止盈】价格 {price}, 入场价 {entry_price}, 收益率: {(price/entry_price-1)*100:.2f}%')
                    self.order = self.close()
                # 止损
                elif price <= entry_price * (1 - self.p.stop_loss):
                    self.log(f'【多仓止损】价格 {price}, 入场价 {entry_price}, 收益率: {(price/entry_price-1)*100:.2f}%')
                    self.order = self.close()
            elif self.position.size < 0:  # 空仓
                # 止盈
                if price <= entry_price * (1 - self.p.take_profit):
                    self.log(f'【空仓止盈】价格 {price}, 入场价 {entry_price}, 收益率: {(entry_price/price-1)*100:.2f}%')
                    self.order = self.close()
                # 止损
                elif price >= entry_price * (1 + self.p.stop_loss):
                    self.log(f'【空仓止损】价格 {price}, 入场价 {entry_price}, 收益率: {(entry_price/price-1)*100:.2f}%')
                    self.order = self.close()


# ==========================
# 3. 多股票测试函数
# ==========================
def test_multiple_stocks():
    """测试策略在多个股票上的表现"""
    # 选择几个有代表性的股票，减少到3个提高测试效率
    stocks = [
        ("sz000001", "平安银行"),      # 银行股（已测试成功）
        ("sz000858", "五粮液"),       # 白酒股
        ("sz300750", "宁德时代"),      # 新能源龙头
    ]
    
    results = {}
    
    for stock_code, stock_name in stocks:
        print(f"\n{'='*50}")
        print(f"正在测试: {stock_name}({stock_code})")
        print(f"{'='*50}")
        
        # 初始化 Cerebro 引擎
        cerebro = bt.Cerebro()
        cerebro.addstrategy(First5MinBreakout)

        # 获取数据，减少数据量提高测试速度
        data_df = get_stock_data(stock_code, "2025-12-01", "2025-12-22")
        
        if data_df is None or len(data_df) == 0:
            print(f"{stock_name} 数据获取失败")
            results[stock_name] = None
            continue
            
        # 创建 Data Feed
        data_feed = bt.feeds.PandasData(dataname=data_df)
        cerebro.adddata(data_feed)
        
        # 设置初始资金10万，便于比较
        cerebro.broker.setcash(100000.0)
        cerebro.broker.setcommission(commission=0.0003)
        cerebro.addsizer(bt.sizers.FixedSize, stake=1000) # 每次交易1000股
        
        initial_value = cerebro.broker.getvalue()
        print(f'初始资金: {initial_value:.2f}')
        
        # 运行回测
        try:
            thestrats = cerebro.run()
            final_value = cerebro.broker.getvalue()
            pnl = final_value - initial_value
            pnl_pct = (pnl / initial_value) * 100
            
            results[stock_name] = {
                'initial': initial_value,
                'final': final_value,
                'pnl': pnl,
                'pnl_pct': pnl_pct
            }
            
            print(f'最终资金: {final_value:.2f}')
            print(f'盈亏: {pnl:.2f} ({pnl_pct:.2f}%)')
            
        except Exception as e:
            print(f"回测失败: {e}")
            results[stock_name] = None
    
    # 输出综合结果
    print(f"\n{'='*60}")
    print("多股票测试结果汇总")
    print(f"{'='*60}")
    print(f"{'股票名称':<10} {'初始资金':>10} {'最终资金':>10} {'盈亏金额':>10} {'盈亏比例':>10}")
    print(f"{'-'*60}")
    
    for stock_name, result in results.items():
        if result:
            print(f"{stock_name:<10} {result['initial']:>10.2f} {result['final']:>10.2f} {result['pnl']:>10.2f} {result['pnl_pct']:>10.2f}%")
        else:
            print(f"{stock_name:<10} {'数据获取失败':>48}")
    
    return results

# ==========================
# 4. 主程序
# ==========================
if __name__ == '__main__':
    # 可以选择单股票测试或多股票测试
    test_multiple_stocks()