import importlib
import logging
from dataclasses import dataclass, field
from typing import List, Any

import ccxt

from . import config
from .strategy import Strategy

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class Position:
    """Simple representation of an open position."""
    entry_price: float
    amount: float
    strategy: str

@dataclass
class TradingBot:
    exchange_id: str = "binance"
    strategies: List[Strategy] = field(default_factory=list)
    positions: List[Position] = field(default_factory=list)

    def __post_init__(self):
        self.exchange = getattr(ccxt, self.exchange_id)({
            "apiKey": config.EXCHANGE_API_KEY,
            "secret": config.EXCHANGE_SECRET,
        })
        self.load_strategies()

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
            if strat.should_enter():
                price = strat.data["close"].iloc[-1]
                amount = 1  # fixed size for example
                self.positions.append(Position(price, amount, strat.__class__.__name__))
                logger.info("Entered position at %s by %s", price, strat.__class__.__name__)
            for pos in list(self.positions):
                if pos.strategy == strat.__class__.__name__ and strat.should_exit(pos):
                    logger.info("Exiting position from %s at %s", pos.strategy, pos.entry_price)
                    self.positions.remove(pos)

