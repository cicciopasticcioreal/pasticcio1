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
    """Representation of an open position."""
    entry_price: float
    amount: float
    strategy: str
    timestamp: float = field(default_factory=time.time)

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

    def place_order(self, side: str, amount: float) -> Any:
        """Execute an order on the exchange or simulate it."""
        if config.SIMULATE:
            logger.info("Simulated %s order for %s %s", side, amount, config.TRADING_PAIR)
            return {"simulated": True}
        try:
            if side == "buy":
                return self.exchange.create_market_buy_order(config.TRADING_PAIR, amount)
            return self.exchange.create_market_sell_order(config.TRADING_PAIR, amount)
        except Exception as exc:
            logger.warning("Failed to place %s order: %s", side, exc)
            return None

    def evaluate(self):
        """Evaluate strategies and manage positions."""
        entry_votes = []
        exit_votes = []
        for strat in self.strategies:
            try:
                if strat.should_enter():
                    entry_votes.append(strat)
                if self.positions and strat.should_exit(self.positions[0]):
                    exit_votes.append(strat)
            except Exception:
                logger.exception("Error in strategy %s", strat.__class__.__name__)

        if not self.positions and len(entry_votes) >= config.ENTRY_THRESHOLD:
            price = entry_votes[0].data["close"].iloc[-1]
            if self.place_order("buy", config.ORDER_SIZE):
                self.positions.append(Position(price, config.ORDER_SIZE, "combined"))
                self.record_trade("enter", price, config.ORDER_SIZE, "combined")
                logger.info("Entered position at %s based on %d strategies", price, len(entry_votes))

        elif self.positions and len(exit_votes) >= config.EXIT_THRESHOLD:
            pos = self.positions[0]
            if self.place_order("sell", pos.amount):
                logger.info("Exiting position opened at %s", pos.entry_price)
                self.record_trade("exit", pos.entry_price, pos.amount, "combined")
                self.positions.clear()

