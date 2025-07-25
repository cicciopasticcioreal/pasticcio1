"""Entry point for running the trading bot with dashboard."""
import argparse
import threading
import time

from .bot import TradingBot
from .dashboard import create_app
from . import config


def run_bot(bot: TradingBot):
    """Continuously evaluate strategies using the configured interval."""
    while True:
        bot.evaluate()
        time.sleep(config.REFRESH_INTERVAL)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Run the trading bot")
    parser.add_argument("--pair", default=config.TRADING_PAIR, help="Primary trading pair, e.g. BTC/USDT")
    parser.add_argument("--pairs", default=','.join(config.TRADING_PAIRS), help="Comma-separated list of trading pairs")
    parser.add_argument("--auto-pairs", action="store_true", default=config.AUTO_SELECT_PAIRS, help="Select trading pairs automatically")
    parser.add_argument("--auto-pair-count", type=int, default=config.AUTO_PAIR_COUNT, help="Number of pairs to auto select")
    parser.add_argument("--timeframe", default=config.TIMEFRAME, help="OHLCV timeframe")
    parser.add_argument("--exchange", default=config.EXCHANGE_ID, help="Exchange id from ccxt")
    parser.add_argument("--port", type=int, default=config.DASHBOARD_PORT, help="Dashboard port")
    parser.add_argument("--order-size", type=float, default=config.ORDER_SIZE, help="Amount to trade")
    parser.add_argument("--simulate", action="store_true", default=config.SIMULATE, help="Run without placing real orders")
    parser.add_argument("--refresh-interval", type=int, default=config.REFRESH_INTERVAL, help="Seconds between evaluations")
    parser.add_argument("--data-path", default=config.DATA_PATH, help="CSV file to persist trades")
    parser.add_argument("--entry-threshold", type=int, default=config.ENTRY_THRESHOLD, help="Number of strategies required to enter")
    parser.add_argument("--exit-threshold", type=int, default=config.EXIT_THRESHOLD, help="Number of strategies required to exit")
    parser.add_argument(
        "--strategies",
        default=','.join(config.STRATEGIES),
        help="Comma-separated list of strategy class names",
    )
    parser.add_argument("--auto-strategies", action="store_true", default=config.AUTO_SELECT_STRATEGIES, help="Load all strategies automatically")
    parser.add_argument(
        "--stop-loss",
        type=float,
        default=config.STOP_LOSS_PCT,
        help="Stop loss percentage",
    )
    parser.add_argument(
        "--take-profit",
        type=float,
        default=config.TAKE_PROFIT_PCT,
        help="Take profit percentage",
    )
    parser.add_argument(
        "--max-positions",
        type=int,
        default=config.MAX_POSITIONS,
        help="Maximum number of open positions",
    )
    parser.add_argument(
        "--partial-tp",
        type=float,
        default=config.PARTIAL_TAKE_PROFIT_PCT,
        help="Partial take profit percentage",
    )
    parser.add_argument(
        "--partial-ratio",
        type=float,
        default=config.PARTIAL_TAKE_PROFIT_RATIO,
        help="Fraction to close when partial take profit triggers",
    )
    parser.add_argument(
        "--trailing-stop",
        type=float,
        default=config.TRAILING_STOP_PCT,
        help="Trailing stop percentage",
    )
    parser.add_argument(
        "--weight-threshold",
        type=float,
        default=config.WEIGHT_THRESHOLD,
        help="Minimum combined strategy weight before a trade",
    )
    args = parser.parse_args(argv)

    # Update configuration based on CLI args
    config.TRADING_PAIR = args.pair
    config.TRADING_PAIRS = [p.strip() for p in args.pairs.split(',') if p.strip()]
    config.AUTO_SELECT_PAIRS = args.auto_pairs
    config.AUTO_PAIR_COUNT = args.auto_pair_count
    config.TIMEFRAME = args.timeframe
    config.EXCHANGE_ID = args.exchange
    config.DASHBOARD_PORT = args.port
    config.ORDER_SIZE = args.order_size
    config.SIMULATE = args.simulate
    config.REFRESH_INTERVAL = args.refresh_interval
    config.DATA_PATH = args.data_path
    config.ENTRY_THRESHOLD = args.entry_threshold
    config.EXIT_THRESHOLD = args.exit_threshold
    config.STRATEGIES = [s.strip() for s in args.strategies.split(',') if s.strip()]
    config.AUTO_SELECT_STRATEGIES = args.auto_strategies
    config.STOP_LOSS_PCT = args.stop_loss
    config.TAKE_PROFIT_PCT = args.take_profit
    config.MAX_POSITIONS = args.max_positions
    config.PARTIAL_TAKE_PROFIT_PCT = args.partial_tp
    config.PARTIAL_TAKE_PROFIT_RATIO = args.partial_ratio
    config.TRAILING_STOP_PCT = args.trailing_stop
    config.WEIGHT_THRESHOLD = args.weight_threshold

    bot = TradingBot(exchange_id=args.exchange)
    app = create_app(bot)
    threading.Thread(target=run_bot, args=(bot,), daemon=True).start()
    app.run(port=args.port)


if __name__ == "__main__":
    main()
