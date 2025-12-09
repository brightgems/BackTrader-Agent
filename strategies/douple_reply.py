# 同时回放多个时间框架
cerebro = bt.Cerebro()

# 原始1分钟数据
data_1min = bt.feeds.GenericCSVData(...)

# 回放为5分钟
data_5min = cerebro.replaydata(data_1min, 
                               timeframe=bt.TimeFrame.Minutes,
                               compression=5)

# 回放为15分钟
data_15min = cerebro.replaydata(data_1min,
                                timeframe=bt.TimeFrame.Minutes,
                                compression=15)

# 添加所有数据
cerebro.adddata(data_5min)
cerebro.adddata(data_15min)