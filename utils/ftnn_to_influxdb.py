#!/usr/bin/env python3
"""
FTNN Socket API to InfluxDB Data Converter
Fetches real-time market data from FTNN plugin and stores it in InfluxDB
"""

import sys
import os
import json
import socket
import logging
import numpy as np
import pandas as pd
import datetime as dt
import argparse
import time
from influxdb import DataFrameClient as dfclient
from influxdb.exceptions import InfluxDBClientError
from typing import List, Optional, Dict


class FTNNTool(object):
    """Tool for importing FTNN socket API data into InfluxDB"""
    
    def __init__(self, args, logger):
        """
        Initialize FTNN socket client and InfluxDB connection
        
        Args:
            args: Parsed command line arguments
            logger: Logger instance
        """
        self.log = logger
        self.timeout = 10.0
        
        # InfluxDB configuration
        self._dbhost = args.dbhost if args.dbhost else 'localhost'
        self._dbport = args.dbport if args.dbport else 8086
        self._username = args.username if args.username else None
        self._password = args.password if args.password else None
        self._database = args.database if args.database else 'market_data'
        
        # FTNN Socket configuration
        self._ftnn_host = args.ftnn_host if args.ftnn_host else 'localhost'
        self._ftnn_port = args.ftnn_port if args.ftnn_port else 11111
        self._market = args.market  # 1=HK, 2=US
        self._stock_code = args.stock_code
        
        # Data aggregation settings
        self._interval = args.interval  # in seconds (60 for 1min, 300 for 5min)
        self._tick_data = []
        self._current_minute_data = pd.DataFrame()
        
        # Initialize socket connection
        self._sock = None
        self._connect_socket()
        
        # Initialize InfluxDB client
        try:
            self.dfdb = dfclient(
                self._dbhost, 
                self._dbport,
                self._username, 
                self._password,
                self._database
            )
            self.log.info("Connected to InfluxDB at %s:%s", self._dbhost, self._dbport)
        except Exception as err:
            self.log.error("Failed to connect to InfluxDB: %s", err)
            sys.exit(-1)
    
    def _connect_socket(self):
        """Establish socket connection to FTNN plugin"""
        try:
            self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._sock.connect((self._ftnn_host, self._ftnn_port))
            self._sock.settimeout(self.timeout)
            self.log.info("Connected to FTNN plugin at %s:%s", 
                         self._ftnn_host, self._ftnn_port)
        except socket.error as err:
            self.log.error("Failed to connect to FTNN plugin: %s", err)
            sys.exit(-1)
    
    def _send_quote_request(self, stock_code: str, market: str) -> Dict:
        """
        Send quote request to FTNN plugin
        
        Args:
            stock_code: Stock symbol (e.g., 'ASHR', '00700')
            market: Market code ('1' for HK, '2' for US)
            
        Returns:
            Dictionary containing quote data
        """
        # Build request according to FTNN protocol
        req = {
            'Protocol': '1001',
            'ReqParam': {
                'Market': market,
                'StockCode': stock_code
            },
            'Version': '1'
        }
        
        str_req = json.dumps(req) + "\n"
        self.log.debug("Sending request: %s", str_req.strip())
        
        try:
            self._sock.send(str_req.encode('utf-8'))
        except socket.error as err:
            self.log.error("Failed to send request: %s", err)
            self._connect_socket()  # Reconnect
            return None
        
        # Receive response
        rsp = ""
        while True:
            try:
                buf = self._sock.recv(1024).decode('utf-8')
                rsp += buf
                
                # Response ends with '\n'
                if '\n' in rsp:
                    break
            except socket.timeout:
                self.log.warning("Socket receive timeout")
                return None
            except socket.error as err:
                self.log.error("Socket receive error: %s", err)
                return None
        
        self.log.debug("Received response: %s", rsp.strip())
        
        # Parse response
        try:
            rsp_data = json.loads(rsp.strip())
            return rsp_data
        except json.JSONDecodeError as err:
            self.log.error("Failed to parse JSON response: %s", err)
            return None
    
    def _parse_quote_data(self, rsp_data: Dict) -> Optional[Dict]:
        """
        Parse quote response data
        
        Args:
            rsp_data: Raw response from FTNN
            
        Returns:
            Dictionary with parsed price and time data
        """
        if not rsp_data or 'RetData' not in rsp_data:
            return None
        
        try:
            ret_data = rsp_data['RetData']
            
            # Extract current price
            current_price = float(ret_data.get('Price', 0))
            
            # Extract timestamp (seconds since midnight)
            current_time = int(ret_data.get('UpdateTime', 0))
            current_hour = current_time // 3600
            current_minute = (current_time - current_hour * 3600) // 60
            current_second = current_time - current_hour * 3600 - current_minute * 60
            
            # Create timestamp
            now = dt.datetime.now()
            timestamp = dt.datetime(
                now.year, now.month, now.day,
                current_hour, current_minute, current_second
            )
            
            return {
                'timestamp': timestamp,
                'price': current_price,
                'volume': ret_data.get('Volume', 0),
                'turnover': ret_data.get('Turnover', 0)
            }
        
        except (KeyError, ValueError) as err:
            self.log.error("Failed to parse quote data: %s", err)
            return None
    
    def _aggregate_to_ohlc(self, tick_data: List[Dict], interval_minutes: int = 1) -> Optional[pd.DataFrame]:
        """
        Aggregate tick data to OHLC candles
        
        Args:
            tick_data: List of tick data dictionaries
            interval_minutes: Candle interval in minutes
            
        Returns:
            DataFrame with OHLC data
        """
        if not tick_data:
            return None
        
        # Convert to DataFrame
        df = pd.DataFrame(tick_data)
        df.set_index('timestamp', inplace=True)
        
        # Resample to OHLC
        ohlc = df['price'].resample(f'{interval_minutes}min').ohlc()
        volume = df['volume'].resample(f'{interval_minutes}min').sum()
        
        # Combine
        result = ohlc.copy()
        result['volume'] = volume
        
        # Rename columns to match our schema
        result.columns = ['open_p', 'high_p', 'low_p', 'close_p', 'volume']
        
        return result
    
    def collect_realtime_data(self, duration_minutes: int = 60):
        """
        Collect real-time data for specified duration
        
        Args:
            duration_minutes: How long to collect data (in minutes)
        """
        start_time = time.time()
        end_time = start_time + (duration_minutes * 60)
        
        last_minute = None
        tick_buffer = []
        
        self.log.info("Starting data collection for %s (Market: %s)", 
                     self._stock_code, self._market)
        self.log.info("Will collect for %d minutes", duration_minutes)
        
        while time.time() < end_time:
            # Request quote
            rsp_data = self._send_quote_request(self._stock_code, self._market)
            
            if rsp_data:
                quote = self._parse_quote_data(rsp_data)
                
                if quote:
                    current_minute = quote['timestamp'].strftime('%Y-%m-%d %H:%M')
                    
                    # Check if we've moved to a new minute
                    if last_minute is not None and current_minute != last_minute:
                        # Aggregate previous minute's data
                        if tick_buffer:
                            self.log.info("Aggregating data for minute: %s (%d ticks)", 
                                        last_minute, len(tick_buffer))
                            
                            ohlc = self._aggregate_to_ohlc(tick_buffer, 
                                                          interval_minutes=self._interval // 60)
                            
                            if ohlc is not None and not ohlc.empty:
                                self._write_to_influxdb(ohlc, self._stock_code)
                            
                            # Clear buffer
                            tick_buffer = []
                    
                    # Add to buffer
                    tick_buffer.append(quote)
                    last_minute = current_minute
                    
                    self.log.debug("Tick: %s - Price: %.2f", 
                                 quote['timestamp'], quote['price'])
            
            # Sleep between requests
            time.sleep(0.5)
        
        # Process remaining data
        if tick_buffer:
            self.log.info("Processing final buffer (%d ticks)", len(tick_buffer))
            ohlc = self._aggregate_to_ohlc(tick_buffer, 
                                          interval_minutes=self._interval // 60)
            if ohlc is not None and not ohlc.empty:
                self._write_to_influxdb(ohlc, self._stock_code)
        
        self.log.info("Data collection completed")
    
    def _write_to_influxdb(self, df: pd.DataFrame, measurement: str):
        """
        Write DataFrame to InfluxDB
        
        Args:
            df: DataFrame with OHLC data
            measurement: Measurement name (usually ticker symbol)
        """
        try:
            self.log.info("Writing %d records to InfluxDB (measurement: %s)", 
                         len(df), measurement)
            self.dfdb.write_points(df, measurement)
            self.log.info("Successfully wrote data to InfluxDB")
        except InfluxDBClientError as err:
            self.log.error('Failed to write to InfluxDB: %s', err)
    
    def get_historical_data_from_csv(self, csv_file: str):
        """
        Load historical data from CSV file and write to InfluxDB
        
        Args:
            csv_file: Path to CSV file with historical data
        """
        if not os.path.exists(csv_file):
            self.log.error("CSV file does not exist: %s", csv_file)
            return
        
        try:
            df = pd.read_csv(csv_file, index_col=0)
            
            # Parse index as datetime
            df.index = pd.to_datetime(df.index)
            
            # Rename columns if needed
            column_mapping = {
                'open': 'open_p',
                'high': 'high_p',
                'low': 'low_p',
                'close': 'close_p'
            }
            df = df.rename(columns=column_mapping)
            
            # Write to InfluxDB
            self._write_to_influxdb(df, self._stock_code)
            
            self.log.info("Successfully imported %d records from %s", 
                         len(df), csv_file)
        
        except Exception as err:
            self.log.error("Failed to import CSV: %s", err)
    
    def close(self):
        """Clean up resources"""
        if self._sock:
            self._sock.close()
            self.log.info("Closed FTNN socket connection")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description="Import FTNN Socket API Data to InfluxDB"
    )
    
    # Stock options
    parser.add_argument(
        "--stock-code",
        required=True,
        action='store',
        help="Stock code (e.g., ASHR, 00700, 01585)."
    )
    parser.add_argument(
        '--market',
        required=True,
        action='store',
        choices=['1', '2'],
        help='Market code: 1=Hong Kong, 2=US.'
    )
    
    # InfluxDB options
    parser.add_argument(
        '--dbhost',
        required=False,
        action='store',
        default=None,
        help='InfluxDB hostname.'
    )
    parser.add_argument(
        '--dbport',
        required=False,
        action='store',
        default=None,
        type=int,
        help='InfluxDB port number.'
    )
    parser.add_argument(
        '--username',
        required=False,
        action='store',
        default=None,
        help='InfluxDB username.'
    )
    parser.add_argument(
        '--password',
        required=False,
        action='store',
        default=None,
        help='InfluxDB password.'
    )
    parser.add_argument(
        '--database',
        required=False,
        action='store',
        default=None,
        help='InfluxDB database name.'
    )
    
    # FTNN Socket options
    parser.add_argument(
        '--ftnn-host',
        required=False,
        action='store',
        default=None,
        help='FTNN plugin socket hostname.'
    )
    parser.add_argument(
        '--ftnn-port',
        required=False,
        action='store',
        default=None,
        type=int,
        help='FTNN plugin socket port number.'
    )
    
    # Data collection options
    parser.add_argument(
        '--interval',
        required=False,
        action='store',
        default=60,
        type=int,
        choices=[60, 300, 900, 1800, 3600],
        help='Data interval in seconds (60=1min, 300=5min, 900=15min, 1800=30min, 3600=1hour).'
    )
    parser.add_argument(
        '--duration',
        required=False,
        action='store',
        default=60,
        type=int,
        help='Collection duration in minutes.'
    )
    
    # CSV import option
    parser.add_argument(
        '--import-csv',
        required=False,
        action='store',
        default=None,
        help='Import historical data from CSV file instead of real-time collection.'
    )
    
    # Logging options
    parser.add_argument(
        '--debug',
        required=False,
        action='store_true',
        help='Enable debug logging.'
    )
    parser.add_argument(
        '--info',
        required=False,
        action='store_true',
        help='Enable info logging.'
    )
    
    args = parser.parse_args()
    
    # Setup logging
    log = logging.getLogger('FTNNTool')
    log_console = logging.StreamHandler(sys.stdout)
    log_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    log_console.setFormatter(log_formatter)
    log.addHandler(log_console)
    
    # Set log level
    if args.debug:
        log.setLevel(logging.DEBUG)
    elif args.info:
        log.setLevel(logging.INFO)
    else:
        log.setLevel(logging.WARNING)
    
    # Initialize FTNN tool
    try:
        ftnn = FTNNTool(args, log)
    except Exception as err:
        log.error("Failed to initialize FTNN tool: %s", err)
        sys.exit(-1)
    
    try:
        if args.import_csv:
            # Import from CSV
            ftnn.get_historical_data_from_csv(args.import_csv)
        else:
            # Collect real-time data
            ftnn.collect_realtime_data(duration_minutes=args.duration)
    
    except KeyboardInterrupt:
        log.info("Interrupted by user")
    
    except Exception as err:
        log.error("Error during data collection: %s", err)
    
    finally:
        ftnn.close()


if __name__ == "__main__":
    main()