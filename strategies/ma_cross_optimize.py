import datetime
import backtrader as bt
from strategies.ma_cross_over import SmaCross
from utils.fetch_data import get_yfinance_data

def runstrat():
	#Instantiate Cerebro engine
	cerebro = bt.Cerebro(optreturn=False)

	#Set data parameters and add to Cerebro
	data = get_yfinance_data('TLSA', datetime.datetime(2019, 1, 1), datetime.datetime(2024, 12, 31))

	cerebro.adddata(data)
	cerebro.broker.setcash(10000)
	#Default position size
	cerebro.addsizer(bt.sizers.SizerFix, stake=3)
	#Add strategy to Cerebro
	cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe_ratio')

	cerebro.optstrategy(SmaCross, pfast=(5, 10, 15, 20, 30), pslow=range(50, 100))  # Add the trading strategy
	return cerebro.run()


if __name__ == '__main__':
	
	optimized_runs = runstrat()
	final_results_list = []
	#Iterate through list of lists
	for run in optimized_runs:
		for strategy in run:
			PnL = round(strategy.broker.get_value() - 10000,2)
			sharpe = strategy.analyzers.sharpe_ratio.get_analysis()
			final_results_list.append([strategy.params.pfast, strategy.params.pslow, PnL, sharpe['sharperatio']])

	sort_by_sharpe = sorted(final_results_list, key=lambda x: x[3], reverse=True)
	#Print top 5 results sorted by Sharpe Ratio
	for line in sort_by_sharpe[:5]:
		print(line)