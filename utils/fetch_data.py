import yfinance as yf
import backtrader as bt
import pandas as pd
from pathlib import Path
import os
from datetime import datetime
from typing import Union

def download_akshare_data(instrument:str, start_date:str, end_date:str
                         , return_df=False, force_download=False) -> Union[str, pd.DataFrame]:
    """
    下载指定股票的历史日线数据并重命名列
    支持A股（上证/深证）和美股行情数据

    参数:
        instrument (str): 股票代码 
            A股格式: "000001.XSHG" (上证), "000001.SH" (上证), 
                    "000001.XSHE" (深证), "000001.SZ" (深证)
            美股格式: "AAPL.US", "GOOGL" (全字母代码)
        start_date (str): 开始日期 (格式 "YYYY-MM-DD")
        end_date (str): 结束日期 (格式 "YYYY-MM-DD")
        return_df (bool): 是否直接返回DataFrame
        force_download (bool): 是否强制重新下载，即使文件已存在

    返回:
        pd.DataFrame 或 str: 包含历史数据的DataFrame或文件路径
    """
    import akshare as ak
    # 使用绝对路径确保无论从哪个目录运行都能正确保存文件
    current_dir = Path(os.path.abspath(__file__)).parent.parent
    datas_dir = os.path.join(current_dir, "datas")
    os.makedirs(datas_dir, exist_ok=True)
    
    if isinstance(start_date, datetime):
       start_date = start_date.strftime('%Y-%m-%d') 
    if isinstance(end_date, datetime):
        end_date = end_date.strftime('%Y-%m-%d')
    
    file_name = f"akshare_{instrument.replace('.', '_')}_{start_date[:10]}_to_{end_date[:10]}.csv"
    file_path = os.path.join(datas_dir, file_name)
    
    # 如果文件已存在且不强制下载，直接返回现有文件
    if os.path.exists(file_path) and not force_download:
        print(f"使用现有数据文件: {file_path}")
        if return_df:
            df = pd.read_csv(file_path, index_col=0, parse_dates=True)
            return df
        return file_path
    
    try:
        # 根据股票代码判断市场类型
        if instrument.endswith('.XSHG') or instrument.endswith('.SH'):
            # 上海交易所股票，去掉后缀
            symbol = instrument.replace('.XSHG', '').replace('.SH', '')
            df = ak.stock_zh_a_hist(symbol=symbol, period="daily", 
                                  start_date=start_date.replace('-', ''), 
                                  end_date=end_date.replace('-', ''), 
                                  adjust="qfq")  # 前复权
        elif instrument.endswith('.XSHE') or instrument.endswith('.SZ'):
            # 深圳交易所股票，去掉后缀
            symbol = instrument.replace('.XSHE', '').replace('.SZ', '')
            df = ak.stock_zh_a_hist(symbol=symbol, period="daily", 
                                  start_date=start_date.replace('-', ''), 
                                  end_date=end_date.replace('-', ''), 
                                  adjust="qfq")  # 前复权
        elif instrument.endswith('.US') or not any(char.isdigit() for char in instrument):
            # 美股代码（以.US结尾或全字母）或者非数字代码
            if instrument.endswith('.US'):
                symbol = instrument.replace('.US', '')
            else:
                symbol = instrument
            
            # 使用akshare的美股日线数据接口（该接口不支持日期参数，需要手动过滤）
            df = ak.stock_us_daily(symbol=symbol, adjust="")
            
            # 美股数据可能需要不同的列名映射
            df = df.rename(columns={
                'date': 'datetime',
                'open': 'Open',
                'close': 'Close', 
                'high': 'High',
                'low': 'Low',
                'volume': 'Volume'
            })
            
            # 转换日期格式
            df['datetime'] = pd.to_datetime(df['datetime'])
            
            # 按日期范围过滤数据
            start_dt = pd.to_datetime(start_date)
            end_dt = pd.to_datetime(end_date)
            df = df[(df['datetime'] >= start_dt) & (df['datetime'] <= end_dt)]
            
        else:
            # 其他类型的A股股票代码，尝试通用接口
            df = ak.stock_zh_a_hist(symbol=instrument, period="daily", 
                                  start_date=start_date.replace('-', ''), 
                                  end_date=end_date.replace('-', ''), 
                                  adjust="qfq")
        
        if df.empty:
            raise ValueError(f"无法下载数据，请检查代码 {instrument} 和日期范围 {start_date} 至 {end_date} 是否正确。")
        
        # 重命名列以适配backtrader格式
        df = df.rename(columns={
            '日期': 'datetime',
            '开盘': 'Open',
            '收盘': 'Close', 
            '最高': 'High',
            '最低': 'Low',
            '成交量': 'Volume'
        })
        
        # 转换日期格式和设置索引
        df['datetime'] = pd.to_datetime(df['datetime'])
        df = df.set_index('datetime')
        
        # 选择需要的列并按时间排序
        df = df[['Open', 'Close', 'High', 'Low', 'Volume']].sort_index()
        
        if return_df:
            return df
        
        df.to_csv(file_path)
        print(f"Akshare数据已保存到: {file_path}")
        return file_path
        
    except Exception as e:
        raise Exception(f"akshare数据下载失败: {str(e)}. 请确保akshare库已正确安装。")


def download_tushare_data(instrument:str, start_date:str, end_date:str
                         , return_df=False, force_download=False)->Union[str, pd.DataFrame]:
    """
    下载指定股票的历史日线数据并重命名列

    参数:
        instrument (str): 股票代码 (如 "000001.SZ")
        start_date (str): 开始日期 (格式 "YYYY-MM-DD")
        end_date (str): 结束日期 (格式 "YYYY-MM-DD")
        return_df (bool): 是否直接返回DataFrame
        force_download (bool): 是否强制重新下载，即使文件已存在

    返回:
        pd.DataFrame 或 str: 包含历史数据的DataFrame或文件路径
    """
    import tushare as ts
    # 使用绝对路径确保无论从哪个目录运行都能正确保存文件
    current_dir = Path(os.path.abspath(__file__)).parent.parent
    datas_dir = os.path.join(current_dir, "datas")
    os.makedirs(datas_dir, exist_ok=True)
    
    if isinstance(start_date, datetime):
       start_date = start_date.strftime('%Y-%m-%d') 
    if isinstance(end_date, datetime):
        end_date = end_date.strftime('%Y-%m-%d')
    
    file_name = f"tushare_{instrument}_{start_date[:10]}_to_{end_date[:10]}.csv"
    file_path = os.path.join(datas_dir, file_name)
    
    # 如果文件已存在且不强制下载，直接返回现有文件
    if os.path.exists(file_path) and not force_download:
        print(f"使用现有数据文件: {file_path}")
        if return_df:
            df = pd.read_csv(file_path, index_col=0, parse_dates=True)
            return df
        return file_path
    
    try:
        # 设置tushare token（可能需要先配置）
        ts.set_token(os.getenv('TUSHARE_TOKEN'))  # 用户需要自行配置token
        pro = ts.pro_api()
        
        # 根据股票代码判断市场（A股或美股）
        if instrument.endswith('.SH') or instrument.endswith('.SZ'):
            # 下载A股日线数据
            df = pro.daily(ts_code=instrument, start_date=start_date.replace('-', ''), 
                          end_date=end_date.replace('-', ''))
        else:
            # 美股代码，使用 us_daily 接口
            df = pro.us_daily(ts_code=instrument, start_date=start_date.replace('-', ''), 
                            end_date=end_date.replace('-', ''))
        
        if df.empty:
            raise ValueError(f"无法下载数据，请检查代码 {instrument} 和日期范围 {start_date} 至 {end_date} 是否正确。")
        
        # 重命名列以适配backtrader格式
        df = df.rename(columns={
            'trade_date': 'datetime',
            'open': 'Open',
            'close': 'Close', 
            'high': 'High',
            'low': 'Low',
            'vol': 'Volume'
        })
        
        # 转换日期格式
        df['datetime'] = pd.to_datetime(df['datetime'])
        df = df.set_index('datetime')
        
        # 选择需要的列并按时间排序
        df = df[['Open', 'Close', 'High', 'Low', 'Volume']].sort_index()
        
        if return_df:
            return df
        
        df.to_csv(file_path)
        print(f"数据已保存到: {file_path}")
        return file_path
        
    except Exception as e:
        raise Exception(f"tushare数据下载失败: {str(e)}. 请确保已配置正确的tushare token。")


def download_yfinance_data(instrument:str, start_date:str, end_date:str
                             , proxy:str='http://localhost:7890'
                             , return_df=False, force_download=False)->Union[str, pd.DataFrame]:
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
    current_dir = Path(os.path.abspath(__file__)).parent.parent
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
    # yfinance 的“坑点”：只复权了 Close， 让所有 OHLC 都复权
    if "Adj Close" in df.columns:
        adj_factor = df["Adj Close"] / df["Close"]
        for col in ["Open", "High", "Low", "Close"]:
            df[col] = df[col] * adj_factor
    df = df[["Open","Close","High","Low","Volume"]]
    if len(df) == 0:
        raise ValueError(f"无法下载数据，请检查代码 {instrument} 和日期范围 {start_date} 至 {end_date} 是否正确。")
    df.index = pd.to_datetime(df.index)
    # 清理 MultiIndex 列
    df.columns = df.columns.get_level_values(0)
    if return_df:
        return df
    
    df.to_csv(file_path)
    return file_path


def get_akshare_data(instrument:str, start_date:str, end_date:str, force_download=False) -> bt.feed.CSVDataBase:
    """
    获取akshare数据并转换为backtrader数据feed
    
    参数:
        instrument (str): 股票代码
        start_date (str): 开始日期
        end_date (str): 结束日期
        
    返回:
        bt.feed.CSVDataBase: backtrader数据feed
    """
    try:
        fpath = download_akshare_data(instrument, start_date, end_date, force_download=force_download)
        data = bt.feeds.GenericCSVData(dataname=fpath,
            dtformat=("%Y-%m-%d"),
            datetime=0,      # 第0列为日期时间
            open=1,          # 第1列为开盘价
            close=2,         # 第2列为收盘价
            high=3,          # 第3列为最高价
            low=4,           # 第4列为最低价
            volume=5,        # 第5列为成交量
            openinterest=-1, # 无持仓量数据
        )
        return data
    except Exception as e:
        raise Exception(f"获取akshare数据失败: {str(e)}")


def get_yfinance_data(code, start_date, end_date, force_download=False)->bt.feed.CSVDataBase:
   fpath = download_yfinance_data(code, start_date, end_date, force_download=force_download)
   data = bt.feeds.GenericCSVData(dataname=fpath,
        dtformat=("%Y-%m-%d"),
        datetime=0,      # 第0列为日期时间
        open=1,          # 第4列为开盘价
        close=2,         # 第1列为收盘价
        high=3,          # 第2列为最高价
        low=4,           # 第3列为最低价
        volume=5,        # 第5列为成交量
        openinterest=-1, # 无持仓量数据
    )
   return data


def get_tushare_data(instrument:str, start_date:str, end_date:str)->bt.feed.CSVDataBase:

    try:
        df = download_tushare_data(instrument, start_date, end_date, return_df=True)
    except Exception as e:
        raise Exception(f"获取tushare数据失败: {str(e)}")
    data = bt.feeds.PandasData(dataname=df)
    return data
