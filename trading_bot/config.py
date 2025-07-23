import os

# Basic configuration for the trading bot.
# In a real setup, you would load these from environment variables
# or a configuration file.

# Exchange identifier and credentials.  These can be overridden
# via environment variables or command-line arguments.
EXCHANGE_ID = os.getenv("EXCHANGE_ID", "binance")
EXCHANGE_API_KEY = os.getenv("EXCHANGE_API_KEY", "your-key")
EXCHANGE_SECRET = os.getenv("EXCHANGE_SECRET", "your-secret")

# Default trading pair and timeframe used when none are supplied by the user.
TRADING_PAIR = os.getenv("TRADING_PAIR", "BTC/USDT")
TIMEFRAME = os.getenv("TIMEFRAME", "1h")

# List of strategy class names to load dynamically. The environment
# variable STRATEGIES can override this with a comma separated list.
_strategies_env = os.getenv("STRATEGIES")
if _strategies_env:
    STRATEGIES = [s.strip() for s in _strategies_env.split(",") if s.strip()]
else:
    STRATEGIES = [
        "MovingAverageStrategy",
        "RSIStrategy",
    ]

# Path used to persist executed trades.  The bot will append to this
# CSV file whenever a new position is opened or closed.
DATA_PATH = os.getenv("DATA_PATH", "trades.csv")

# Log verbosity and dashboard port.
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
DASHBOARD_PORT = int(os.getenv("DASHBOARD_PORT", "5000"))

# Evaluation interval in seconds for running the strategies.
REFRESH_INTERVAL = int(os.getenv("REFRESH_INTERVAL", "60"))

# Trade amount per order when entering or exiting positions.
ORDER_SIZE = float(os.getenv("ORDER_SIZE", "1"))

# Simulation mode skips actual order placement.
SIMULATE = os.getenv("SIMULATE", "true").lower() in ("1", "true", "yes")

# Threshold for how many strategies must agree before entering or exiting.
ENTRY_THRESHOLD = int(os.getenv("ENTRY_THRESHOLD", "1"))
EXIT_THRESHOLD = int(os.getenv("EXIT_THRESHOLD", "1"))

# Risk management settings. Percentages are expressed as positive numbers.
# Set to 0 to disable.
STOP_LOSS_PCT = float(os.getenv("STOP_LOSS_PCT", "0"))
TAKE_PROFIT_PCT = float(os.getenv("TAKE_PROFIT_PCT", "0"))

