import yfinance as yf
import backtrader as bt
import pandas as pd
import os
from datetime import datetime

def download_yfinance_data(instrument:str, start_date:str, end_date:str
                             , proxy:str='http://localhost:7890'
                             , return_df=False, force_download=False):
    """
    下载指定金融工具的历史数据并重命名列

    参数:
        instrument (str): 金融工具代码 (如 "AAPL")
        start_date (str): 开始日期 (格式 "YYYY-MM-DD")
        end_date (str): 结束日期 (格式 "YYYY-MM-DD")
        proxy (dict, optional): 代理设置
        return_df (bool): 是否直接返回DataFrame
        force_download (bool): 是否强制重新下载，即使文件已存在

    返回:
        pd.DataFrame 或 str: 包含历史数据的DataFrame或文件路径
    """
    # 使用绝对路径确保无论从哪个目录运行都能正确保存文件
    current_dir = os.path.dirname(os.path.abspath(__file__))
    datas_dir = os.path.join(current_dir, "datas")
    os.makedirs(datas_dir, exist_ok=True)
    
    if isinstance(start_date, datetime):
       start_date = start_date.strftime('%Y-%m-%d') 
    if isinstance(end_date, datetime):
        end_date = end_date.strftime('%Y-%m-%d')
    
    file_name = f"{instrument}_{start_date[:10]}_to_{end_date[:10]}.csv"
    file_path = os.path.join(datas_dir, file_name)
    
    # 如果文件已存在且不强制下载，直接返回现有文件
    if os.path.exists(file_path) and not force_download:
        print(f"使用现有数据文件: {file_path}")
        if return_df:
            df = pd.read_csv(file_path, index_col=0, parse_dates=True)
            return df
        return file_path
    
    df = yf.download(
        instrument,
        start=start_date,
        end=end_date,
        auto_adjust=True,
        proxy=proxy
    )
    if len(df) == 0:
        raise ValueError(f"无法下载数据，请检查代码 {instrument} 和日期范围 {start_date} 至 {end_date} 是否正确。")
    df.index = pd.to_datetime(df.index)
    # 清理 MultiIndex 列
    df.columns = df.columns.get_level_values(0)
    if return_df:
        return df
    
    df.to_csv(file_path)
    return file_path


def get_yfinance_data(code, start_date, end_date):
   fpath = download_yfinance_data(code, start_date, end_date)
   data = bt.feeds.GenericCSVData(dataname=fpath,
        dtformat=("%Y-%m-%d"),
        datetime=0,      # 第0列为日期时间
        close=1,         # 第1列为收盘价
        high=2,          # 第2列为最高价
        low=3,           # 第3列为最低价
        open=4,          # 第4列为开盘价
        volume=5,        # 第5列为成交量
        openinterest=-1, # 无持仓量数据
    )
   return data