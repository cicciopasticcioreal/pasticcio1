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
    closed_profit: float = 0.0
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
        current_price = None
        try:
            current_price = self.exchange.fetch_ticker(config.TRADING_PAIR)["last"]
        except Exception as exc:
            logger.warning("Failed to fetch ticker: %s", exc)

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

        if not self.positions and len(entry_votes) >= config.ENTRY_THRESHOLD and current_price is not None:
            price = current_price
            if self.place_order("buy", config.ORDER_SIZE):
                self.positions.append(Position(price, config.ORDER_SIZE, "combined"))
                self.record_trade("enter", price, config.ORDER_SIZE, "combined")
                logger.info("Entered position at %s based on %d strategies", price, len(entry_votes))

        elif self.positions:
            pos = self.positions[0]
            risk_exit = False
            if current_price is not None:
                change_pct = (current_price - pos.entry_price) / pos.entry_price * 100
                if config.TAKE_PROFIT_PCT and change_pct >= config.TAKE_PROFIT_PCT:
                    logger.info("Take profit reached: %.2f%%", change_pct)
                    risk_exit = True
                elif config.STOP_LOSS_PCT and change_pct <= -config.STOP_LOSS_PCT:
                    logger.info("Stop loss reached: %.2f%%", change_pct)
                    risk_exit = True

            if len(exit_votes) >= config.EXIT_THRESHOLD or risk_exit:
                if current_price is None:
                    current_price = pos.entry_price
                if self.place_order("sell", pos.amount):
                    pnl = (current_price - pos.entry_price) * pos.amount
                    self.closed_profit += pnl
                    logger.info("Exiting position opened at %s with P/L %.2f", pos.entry_price, pnl)
                    self.record_trade("exit", current_price, pos.amount, "combined")
                    self.positions.clear()

