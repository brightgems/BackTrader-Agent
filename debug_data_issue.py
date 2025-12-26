import sys
sys.path.append('.')
import akshare as ak
import pandas as pd

# 直接测试akshare接口
print('直接测试akshare接口...')
try:
    df = ak.stock_zh_a_minute(symbol="sz000001", period="5", adjust="qfq")
    print(f'原始数据形状: {df.shape}')
    print(f'原始数据前几行:')
    print(df.head())
    print(f'原始数据类型: {df.dtypes}')
    
    if df is not None and len(df) > 0:
        # 测试数据清洗逻辑
        df.columns = ['datetime', 'open', 'high', 'low', 'close', 'volume']
        df['datetime'] = pd.to_datetime(df['datetime'])
        df.set_index('datetime', inplace=True)
        print(f'\n清洗后数据形状: {df.shape}')
        print(f'清洗后数据前几行:')
        print(df.head())
        
        # 测试重采样逻辑
        df_5min = df.resample('5Min').agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }).dropna()
        print(f'\n重采样后数据形状: {df_5min.shape}')
        print(f'重采样后数据前几行:')
        print(df_5min.head())
        
        # 检查索引问题
        print(f'\n索引信息:')
        print(f'索引类型: {type(df_5min.index)}')
        print(f'索引值示例: {df_5min.index[:5]}')
        
except Exception as e:
    print(f'错误: {e}')