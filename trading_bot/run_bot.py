"""Entry point for running the trading bot with dashboard."""
import threading
import time

from .bot import TradingBot
from .dashboard import create_app


def run_bot(bot: TradingBot):
    while True:
        bot.evaluate()
        time.sleep(60)  # run every minute


def main():
    bot = TradingBot()
    app = create_app(bot)
    threading.Thread(target=run_bot, args=(bot,), daemon=True).start()
    app.run(port=5000)


if __name__ == "__main__":
    main()
