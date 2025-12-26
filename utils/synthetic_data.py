import pandas as pd
import numpy as np

def get_aligned_synthetic_data(qqq_df, tqqq_df, annual_expense=0.02):
    """
    输入 QQQ 和 TQQQ 的原始数据，返回 1999 年至今的合成+真实数据
    :param qqq_df: QQQ 历史数据 (需包含 1999 年至今)
    :param tqqq_df: TQQQ 历史数据 (2010年至今)
    :param annual_expense: 来源要求的 2% 年度杠杆损耗
    
    关键细节说明（基于来源逻辑）：
    1. 严谨的损耗扣除：函数严格执行了来源中提到的每年 2% 的损耗扣除。这在回测中至关重要，因为这 2% 的管理费和调仓损耗在长达 26 年的复利下对最终资产总额有显著影响。
    2. 数据无缝衔接：为了避免在 2010 年 2 月出现价格断层，该函数采用了逆向锚定法。它以真实 TQQQ 上市当天的价格作为锚点向 1999 年回溯，确保回测曲线的连续性。
    3. 地狱级副本回测基础：通过此函数生成的 1999-2010 年拟合数据，将包含 2000 年互联网泡沫期间 TQQQ 暴跌 99% 以上的极端行情,。这正是验证该策略“200日均线防火墙”是否能防止账户归零的关键。
    4. 实战意义：来源指出，这种合成数据的方法让普通人能够验证该策略在经历 2000 年和 2008 年两次“毁灭性打击”后的表现，从而证明其 36.1% 最大回撤 的防御能力,。

    """
    # 确保日期格式正确并排序
    qqq_df.index = pd.to_datetime(qqq_df.index)
    tqqq_df.index = pd.to_datetime(tqqq_df.index)
    qqq_df.sort_index(inplace=True)
    tqqq_df.sort_index(inplace=True)

    # 1. 确定真实 TQQQ 的起始日期
    real_start_date = tqqq_df.index[0]
    
    # 2. 提取 TQQQ 上市之前的 QQQ 数据进行拟合
    synthetic_period = qqq_df[qqq_df.index < real_start_date].copy()
    
    # 计算 QQQ 每日收益率
    qqq_returns = synthetic_period['Close'].pct_change()
    
    # 计算每日分摊的 2% 损耗 (依据来源 [2] 的严谨性要求)
    daily_loss = (1 + annual_expense) ** (1/252) - 1
    
    # 合成 TQQQ 每日收益率 = QQQ收益率 * 3 - 每日损耗
    synthetic_returns = (qqq_returns * 3) - daily_loss
    
    # 3. 为了让曲线无缝衔接，以真实 TQQQ 上市首日的价格为基准，逆向推算早期价格
    # 初始价格设为真实 TQQQ 第一天的开盘价
    base_price = tqqq_df.iloc[0]['Open']
    
    # 逆向累乘计算价格序列
    # 我们先正向计算累计收益，然后根据 real_start_date 的价格进行缩放
    cum_ret = (1 + synthetic_returns.fillna(0)).cumprod()
    scaling_factor = base_price / cum_ret.iloc[-1]
    
    synthetic_prices = cum_ret * scaling_factor
    
    # 4. 构建拟合阶段的 DataFrame
    synthetic_df = pd.DataFrame(index=synthetic_period.index)
    synthetic_df['Close'] = synthetic_prices
    # 简化模拟 OHLC (保持比例一致)
    ratio = synthetic_df['Close'] / synthetic_period['Close']
    synthetic_df['Open'] = synthetic_period['Open'] * ratio
    synthetic_df['High'] = synthetic_period['High'] * ratio
    synthetic_df['Low'] = synthetic_period['Low'] * ratio
    synthetic_df['Volume'] = synthetic_period['Volume'] # 成交量沿用 QQQ 仅作参考

    # 5. 合并拟合数据与真实数据 [1]
    # 拼接 2010 年以前的合成数据和 2010 年以后的真实 TQQQ 数据
    full_tqqq = pd.concat([synthetic_df, tqqq_df])
    
    # 6. 与 QQQ 时间轴完全对齐
    final_df = pd.merge(qqq_df[[]], full_tqqq, left_index=True, right_index=True, how='left')
    
    return final_df
