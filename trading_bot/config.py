import os

# Basic configuration for the trading bot.
# In a real setup, you would load these from environment variables
# or a configuration file.

# API credentials for exchanges can be set via env variables.
EXCHANGE_API_KEY = os.getenv("EXCHANGE_API_KEY", "your-key")
EXCHANGE_SECRET = os.getenv("EXCHANGE_SECRET", "your-secret")

# Default trading pair and timeframe
TRADING_PAIR = os.getenv("TRADING_PAIR", "BTC/USDT")
TIMEFRAME = os.getenv("TIMEFRAME", "1h")

# List of strategy class names to load dynamically
STRATEGIES = [
    "MovingAverageStrategy",
    "RSIStrategy",
]

# Database or file path for persisting trades
DATA_PATH = os.getenv("DATA_PATH", "trades.csv")

