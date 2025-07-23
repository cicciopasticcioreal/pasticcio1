import importlib
import logging
from dataclasses import dataclass, field
from typing import List, Any
import csv
import os
import time

import ccxt

from . import config
from .strategy import Strategy

logging.basicConfig(level=getattr(logging, config.LOG_LEVEL))
logger = logging.getLogger(__name__)

@dataclass
class Position:
    """Simple representation of an open position."""
    entry_price: float
    amount: float
    strategy: str

@dataclass
class TradingBot:
    """Core trading bot class."""

    exchange_id: str = config.EXCHANGE_ID
    strategies: List[Strategy] = field(default_factory=list)
    positions: List[Position] = field(default_factory=list)
    data_path: str = config.DATA_PATH

    def __post_init__(self):
        self.exchange = getattr(ccxt, self.exchange_id)({
            "apiKey": config.EXCHANGE_API_KEY,
            "secret": config.EXCHANGE_SECRET,
            "enableRateLimit": True,
        })
        self.load_strategies()
        # Ensure trade file exists
        if self.data_path and not os.path.exists(self.data_path):
            with open(self.data_path, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["timestamp", "action", "price", "amount", "strategy"])

    def record_trade(self, action: str, price: float, amount: float, strategy: str) -> None:
        """Persist trade information to CSV."""
        if not self.data_path:
            return
        with open(self.data_path, "a", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([int(time.time()), action, price, amount, strategy])

    def load_strategies(self):
        """Dynamically load strategies from config."""
        for name in config.STRATEGIES:
            module = importlib.import_module("trading_bot.strategy")
            cls = getattr(module, name)
            strategy = cls(self.exchange, config.TRADING_PAIR, config.TIMEFRAME)
            self.strategies.append(strategy)
        logger.info("Loaded strategies: %s", [s.__class__.__name__ for s in self.strategies])

    def evaluate(self):
        """Evaluate strategies and manage positions."""
        for strat in self.strategies:
            try:
                if strat.should_enter():
                    price = strat.data["close"].iloc[-1]
                    amount = 1  # fixed size for example
                    self.positions.append(Position(price, amount, strat.__class__.__name__))
                    self.record_trade("enter", price, amount, strat.__class__.__name__)
                    logger.info("Entered position at %s by %s", price, strat.__class__.__name__)
            except Exception as exc:
                logger.exception("Error in strategy %s", strat.__class__.__name__)

        for pos in list(self.positions):
            strat = next((s for s in self.strategies if s.__class__.__name__ == pos.strategy), None)
            if strat and strat.should_exit(pos):
                logger.info("Exiting position from %s at %s", pos.strategy, pos.entry_price)
                self.record_trade("exit", pos.entry_price, pos.amount, pos.strategy)
                self.positions.remove(pos)

