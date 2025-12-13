# BackTrader-Agent package
import os
import sys
from dotenv import load_dotenv

# Automatically load .env file
load_dotenv()

# Add current directory to path
sys.path.append('.')

# Environment variables
TUSHARE_TOKEN = os.getenv('TUSHARE_TOKEN')