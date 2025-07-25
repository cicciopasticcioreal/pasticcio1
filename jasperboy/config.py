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

# Comma separated list of trading pairs.  When multiple pairs are provided
# the bot will manage independent positions for each of them.
_pairs_env = os.getenv("TRADING_PAIRS")
if _pairs_env:
    TRADING_PAIRS = [p.strip() for p in _pairs_env.split(",") if p.strip()]
else:
    TRADING_PAIRS = [TRADING_PAIR]

# Automatically choose trading pairs if enabled. When AUTO_SELECT_PAIRS
# is true, the bot will query the exchange for the most active markets
# and trade the top AUTO_PAIR_COUNT pairs denominated in USDT.
AUTO_SELECT_PAIRS = os.getenv("AUTO_SELECT_PAIRS", "false").lower() in (
    "1",
    "true",
    "yes",
)
AUTO_PAIR_COUNT = int(os.getenv("AUTO_PAIR_COUNT", "3"))

# List of strategy class names to load dynamically. The environment
# variable STRATEGIES can override this with a comma separated list.
_strategies_env = os.getenv("STRATEGIES")
if _strategies_env:
    STRATEGIES = [s.strip() for s in _strategies_env.split(",") if s.strip()]
else:
    STRATEGIES = [
        "MovingAverageStrategy",
        "RSIStrategy",
        "BollingerBandStrategy",
        "AdaptiveMovingAverageStrategy",
    ]

# When enabled, all available strategies are loaded automatically
# regardless of the STRATEGIES variable. The bot can then decide
# which ones to apply for each pair based on market data.
AUTO_SELECT_STRATEGIES = os.getenv("AUTO_SELECT_STRATEGIES", "false").lower() in (
    "1",
    "true",
    "yes",
)

# Path used to persist executed trades.  The bot will append to this
# CSV file whenever a new position is opened or closed.
DATA_PATH = os.getenv("DATA_PATH", "trades.csv")

# Log verbosity and dashboard port.
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
DASHBOARD_PORT = int(os.getenv("DASHBOARD_PORT", "5000"))

# Log file paths for trading activity and system events
TRADING_LOG_PATH = os.getenv("TRADING_LOG_PATH", "trading.log")
SYSTEM_LOG_PATH = os.getenv("SYSTEM_LOG_PATH", "system.log")

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

# Maximum number of concurrent open positions
MAX_POSITIONS = int(os.getenv("MAX_POSITIONS", "5"))

# Partial take profit settings. When PARTIAL_TAKE_PROFIT_PCT is hit the
# bot will close PARTIAL_TAKE_PROFIT_RATIO of the position.
PARTIAL_TAKE_PROFIT_PCT = float(os.getenv("PARTIAL_TAKE_PROFIT_PCT", "0"))
PARTIAL_TAKE_PROFIT_RATIO = float(os.getenv("PARTIAL_TAKE_PROFIT_RATIO", "0.5"))

# Trailing stop percentage. Set to 0 to disable.
TRAILING_STOP_PCT = float(os.getenv("TRAILING_STOP_PCT", "0"))

# Path to persist strategy weights for the self-learning mechanism.
WEIGHTS_PATH = os.getenv("WEIGHTS_PATH", "weights.json")

# Minimum cumulative weight required to enter or exit a position.
WEIGHT_THRESHOLD = float(os.getenv("WEIGHT_THRESHOLD", "1"))

