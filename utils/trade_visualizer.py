import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import numpy as np

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei']  # 用来正常显示中文标签
plt.rcParams['axes.unicode_minus'] = False  # 用来正常显示负号

def visualize_trade_analyzer(trade_data):
    """
    可视化交易分析器数据
    
    Args:
        trade_data: TradeAnalyzer的get_analysis()结果，可以是AutoOrderedDict或字典
    """
    trade_dict = {}
    if isinstance(trade_data, dict):
        trade_dict = trade_data
    else:
        trade_dict = trade_data.to_dict()
    
    # 创建图形布局
    fig = plt.figure(figsize=(16, 12))
    gs = gridspec.GridSpec(3, 2, figure=fig)
    
    # 1. 总体交易统计
    ax1 = fig.add_subplot(gs[0, 0])
    total_trades = trade_dict['total']['total']
    won_trades = trade_dict['won']['total']
    lost_trades = trade_dict['lost']['total']
    open_trades = trade_dict['total']['open']
    
    labels = ['盈利交易', '亏损交易', '未平仓交易']
    sizes = [won_trades, lost_trades, open_trades]
    colors = ['#2ecc71', '#e74c3c', '#f39c12']
    
    ax1.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90)
    ax1.set_title(f'交易分布 (总计: {total_trades} 笔)')
    
    # 2. 盈亏金额统计
    ax2 = fig.add_subplot(gs[0, 1])
    gross_pnl = trade_dict['pnl']['gross']['total']
    net_pnl = trade_dict['pnl']['net']['total']
    
    categories = ['毛利', '净利']
    values = [gross_pnl, net_pnl]
    colors_bar = ['#3498db', '#9b59b6']
    
    bars = ax2.bar(categories, values, color=colors_bar)
    ax2.set_title('盈亏金额统计')
    ax2.set_ylabel('金额')
    
    # 在柱状图上添加数值标签
    for bar, value in zip(bars, values):
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2., height,
                f'{value:,.2f}', ha='center', va='bottom')
    
    # 3. 多空交易统计
    ax3 = fig.add_subplot(gs[1, 0])
    long_trades = trade_dict['long']['total']
    short_trades = trade_dict['short']['total']
    long_won = trade_dict['long']['won']
    long_lost = trade_dict['long']['lost']
    
    long_data = [long_won, long_lost]
    short_data = [trade_dict['short']['won'], trade_dict['short']['lost']]
    
    x = np.arange(2)
    width = 0.35
    
    bars1 = ax3.bar(x - width/2, long_data, width, label='多头', color='#3498db')
    bars2 = ax3.bar(x + width/2, short_data, width, label='空头', color='#e74c3c')
    
    ax3.set_xlabel('交易结果')
    ax3.set_ylabel('交易数量')
    ax3.set_title('多空交易统计')
    ax3.set_xticks(x)
    ax3.set_xticklabels(['盈利', '亏损'])
    ax3.legend()
    
    # 4. 持仓时间分析
    ax4 = fig.add_subplot(gs[1, 1])
    avg_hold = trade_dict['len']['average']
    max_hold = trade_dict['len']['max']
    min_hold = trade_dict['len']['min']
    
    hold_stats = ['平均持仓', '最长持仓', '最短持仓']
    hold_values = [avg_hold, max_hold, min_hold]
    
    bars = ax4.bar(hold_stats, hold_values, color=['#f39c12', '#e67e22', '#d35400'])
    ax4.set_title('持仓时间统计')
    ax4.set_ylabel('周期数')
    
    for bar, value in zip(bars, hold_values):
        height = bar.get_height()
        ax4.text(bar.get_x() + bar.get_width()/2., height,
                f'{value:.1f}', ha='center', va='bottom')
    
    # 5. 盈亏分布
    ax5 = fig.add_subplot(gs[2, 0])
    won_pnl_avg = trade_dict['won']['pnl']['average']
    lost_pnl_avg = trade_dict['lost']['pnl']['average']
    won_pnl_max = trade_dict['won']['pnl']['max']
    lost_pnl_max = trade_dict['lost']['pnl']['max']
    
    pnl_categories = ['平均盈利', '平均亏损', '最大盈利', '最大亏损']
    pnl_values = [won_pnl_avg, abs(lost_pnl_avg), won_pnl_max, abs(lost_pnl_max)]
    pnl_colors = ['#2ecc71', '#e74c3c', '#27ae60', '#c0392b']
    
    bars = ax5.bar(pnl_categories, pnl_values, color=pnl_colors)
    ax5.set_title('盈亏分布')
    ax5.set_ylabel('金额')
    ax5.tick_params(axis='x', rotation=45)
    
    for bar, value in zip(bars, pnl_values):
        height = bar.get_height()
        ax5.text(bar.get_x() + bar.get_width()/2., height,
                f'{value:,.2f}', ha='center', va='bottom', rotation=45)
    
    # 6. 连续盈亏统计
    ax6 = fig.add_subplot(gs[2, 1])
    won_streak = trade_dict['streak']['won']['longest']
    lost_streak = trade_dict['streak']['lost']['longest']
    current_won = trade_dict['streak']['won']['current']
    current_lost = trade_dict['streak']['lost']['current']
    
    streak_labels = ['最长盈利连', '最长亏损连', '当前盈利连', '当前亏损连']
    streak_values = [won_streak, lost_streak, current_won, current_lost]
    streak_colors = ['#27ae60', '#c0392b', '#2ecc71', '#e74c3c']
    
    bars = ax6.bar(streak_labels, streak_values, color=streak_colors)
    ax6.set_title('连续盈亏统计')
    ax6.set_ylabel('连续次数')
    ax6.tick_params(axis='x', rotation=45)
    
    for bar, value in zip(bars, streak_values):
        height = bar.get_height()
        ax6.text(bar.get_x() + bar.get_width()/2., height,
                f'{value}', ha='center', va='bottom')
    
    plt.tight_layout()
    return fig

def create_detailed_report(data):
    """
    创建详细的交易分析报告
    
    Args:
        data: TradeAnalyzer数据
    """
    report = {
        '总体统计': {
            '总交易数': data['total']['total'],
            '已平仓交易': data['total']['closed'],
            '未平仓交易': data['total']['open'],
            '盈利交易数': data['won']['total'],
            '亏损交易数': data['lost']['total'],
            '胜率': f"{(data['won']['total'] / data['total']['closed'] * 100):.1f}%" if data['total']['closed'] > 0 else 'N/A'
        },
        '盈亏统计': {
            '总毛利': f"{data['pnl']['gross']['total']:,.2f}",
            '总净利': f"{data['pnl']['net']['total']:,.2f}",
            '平均毛利': f"{data['pnl']['gross']['average']:,.2f}",
            '平均净利': f"{data['pnl']['net']['average']:,.2f}",
            '总盈利金额': f"{data['won']['pnl']['total']:,.2f}",
            '总亏损金额': f"{data['lost']['pnl']['total']:,.2f}",
            '盈亏比': f"{(abs(data['won']['pnl']['total'] / data['lost']['pnl']['total'])):.2f}:1" if data['lost']['pnl']['total'] != 0 else 'N/A'
        },
        '多空统计': {
            '多头交易数': data['long']['total'],
            '空头交易数': data['short']['total'],
            '多头盈利数': data['long']['won'],
            '多头亏损数': data['long']['lost'],
            '空头盈利数': data['short']['won'],
            '空头亏损数': data['short']['lost']
        },
        '持仓时间': {
            '平均持仓周期': f"{data['len']['average']:.1f}",
            '最长持仓周期': data['len']['max'],
            '最短持仓周期': data['len']['min'],
            '盈利交易平均持仓': f"{data['len']['won']['average']:.1f}",
            '亏损交易平均持仓': f"{data['len']['lost']['average']:.1f}"
        },
        '连续统计': {
            '最长盈利连': data['streak']['won']['longest'],
            '最长亏损连': data['streak']['lost']['longest'],
            '当前盈利连': data['streak']['won']['current'],
            '当前亏损连': data['streak']['lost']['current']
        }
    }
    
    return report

def print_trade_report(report):
    """打印交易报告"""
    print("=" * 60)
    print("交易分析报告")
    print("=" * 60)
    
    for category, stats in report.items():
        print(f"\n{category}:")
        print("-" * 40)
        for key, value in stats.items():
            print(f"  {key}: {value}")

