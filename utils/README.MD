# ftnn_to_influxdb

## 核心功能

1. **Socket通信协议**：
   - 使用FTNN插件的JSON协议格式
   - Protocol: '1001' 用于报价请求
   - 支持港股(Market='1')和美股(Market='2')

2. **实时数据采集**：
   - 持续获取tick数据
   - 按分钟聚合成OHLC蜡烛图数据
   - 自动写入InfluxDB

3. **数据聚合**：
   - 支持1分钟、5分钟、15分钟等多种时间间隔
   - 使用pandas的resample功能

## 使用示例

```bash
# 采集美股ASHR实时数据，1分钟K线，持续60分钟
python ftnn_influx.py --stock-code ASHR --market 2 \
  --interval 60 --duration 60 --info

# 采集港股腾讯(00700)，5分钟K线
python ftnn_influx.py --stock-code 00700 --market 1 \
  --interval 300 --duration 120 --info

# 从CSV文件导入历史数据
python ftnn_influx.py --stock-code ASHR --market 2 \
  --import-csv c:\\9\\ftnn_souji_ASHR_6_fengzhong.csv

# 指定InfluxDB配置
python ftnn_influx.py --stock-code ASHR --market 2 \
  --dbhost localhost --dbport 8086 \
  --database market_data --duration 30 --info
```

## 主要改进

1. ✅ 使用实际的FTNN Socket协议（JSON格式）
2. ✅ 正确处理时间戳（秒数转换为时:分:秒）
3. ✅ Tick数据聚合为OHLC
4. ✅ 自动重连机制
5. ✅ 完整的错误处理和日志
6. ✅ 支持CSV历史数据导入
7. ✅ 修复了原代码的所有bug

这个版本直接对接您的FTNN插件，可以实时采集数据并存储到InfluxDB！