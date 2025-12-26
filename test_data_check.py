import sys
sys.path.append('.')
from strategies.intraday_momentum_multi import get_stock_data
import pandas as pd

# 测试数据获取功能
print('测试数据获取...')
try:
    df = get_stock_data('sz000001', '2025-01-01', '2025-03-01')

    if df is None:
        print('数据获取失败')
    elif len(df) == 0:
        print('获取到空数据')
    else:
        print(f'数据形状: {df.shape}')
        print(f'数据前几行:')
        print(df.head())
        print(f'数据后几行:')
        print(df.tail())
        print(f'数据类型: {df.dtypes}')
        print(f'索引范围: {df.index.min()} 到 {df.index.max()}')
        print(f'索引类型: {type(df.index)}')
except Exception as e:
    print(f'获取数据时出错: {e}')