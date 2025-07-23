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
    parser.add_argument("--pair", default=config.TRADING_PAIR, help="Trading pair, e.g. BTC/USDT")
    parser.add_argument("--timeframe", default=config.TIMEFRAME, help="OHLCV timeframe")
    parser.add_argument("--exchange", default=config.EXCHANGE_ID, help="Exchange id from ccxt")
    parser.add_argument("--port", type=int, default=config.DASHBOARD_PORT, help="Dashboard port")
    parser.add_argument("--order-size", type=float, default=config.ORDER_SIZE, help="Amount to trade")
    parser.add_argument("--simulate", action="store_true", default=config.SIMULATE, help="Run without placing real orders")
    parser.add_argument("--entry-threshold", type=int, default=config.ENTRY_THRESHOLD, help="Number of strategies required to enter")
    parser.add_argument("--exit-threshold", type=int, default=config.EXIT_THRESHOLD, help="Number of strategies required to exit")
    args = parser.parse_args(argv)

    # Update configuration based on CLI args
    config.TRADING_PAIR = args.pair
    config.TIMEFRAME = args.timeframe
    config.EXCHANGE_ID = args.exchange
    config.DASHBOARD_PORT = args.port
    config.ORDER_SIZE = args.order_size
    config.SIMULATE = args.simulate
    config.ENTRY_THRESHOLD = args.entry_threshold
    config.EXIT_THRESHOLD = args.exit_threshold

    bot = TradingBot(exchange_id=args.exchange)
    app = create_app(bot)
    threading.Thread(target=run_bot, args=(bot,), daemon=True).start()
    app.run(port=args.port)


if __name__ == "__main__":
    main()
