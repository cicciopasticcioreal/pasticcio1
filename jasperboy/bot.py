import importlib
import logging
from dataclasses import dataclass, field
from typing import List, Any
import csv
import os
import time

import ccxt
import psutil

from . import config
from .strategy import Strategy

logging.basicConfig(level=getattr(logging, config.LOG_LEVEL))
logger = logging.getLogger(__name__)

@dataclass
class Position:
    """Representation of an open position."""
    pair: str
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
                writer.writerow(["timestamp", "pair", "action", "price", "amount", "strategy"])

    def record_trade(self, pair: str, action: str, price: float, amount: float, strategy: str) -> None:
        """Persist trade information to CSV."""
        if not self.data_path:
            return
        with open(self.data_path, "a", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([int(time.time()), pair, action, price, amount, strategy])

    def load_strategies(self):
        """Dynamically load strategies from config."""
        for pair in config.TRADING_PAIRS:
            for name in config.STRATEGIES:
                module = importlib.import_module("jasperboy.strategy")
                cls = getattr(module, name)
                strategy = cls(self.exchange, pair, config.TIMEFRAME)
                self.strategies.append(strategy)
        logger.info("Loaded strategies: %s", [s.__class__.__name__ for s in self.strategies])

    def place_order(self, side: str, pair: str, amount: float) -> Any:
        """Execute an order on the exchange or simulate it."""
        if config.SIMULATE:
            logger.info("Simulated %s order for %s %s", side, amount, pair)
            return {"simulated": True}
        try:
            if side == "buy":
                return self.exchange.create_market_buy_order(pair, amount)
            return self.exchange.create_market_sell_order(pair, amount)
        except Exception as exc:
            logger.warning("Failed to place %s order: %s", side, exc)
            return None

    def check_system_health(self) -> None:
        """Log basic system health metrics using psutil."""
        cpu = psutil.cpu_percent()
        mem = psutil.virtual_memory().percent
        disk = psutil.disk_usage("/").percent
        logger.debug("System health - CPU: %.1f%% MEM: %.1f%% DISK: %.1f%%", cpu, mem, disk)

    def evaluate(self):
        """Evaluate strategies and manage positions for all pairs."""
        self.check_system_health()
        # Entry checks for each pair
        for pair in config.TRADING_PAIRS:
            try:
                current_price = self.exchange.fetch_ticker(pair)["last"]
            except Exception as exc:
                logger.warning("Failed to fetch ticker for %s: %s", pair, exc)
                continue

            entry_votes = [s for s in self.strategies if s.pair == pair and s.should_enter()]
            if len(entry_votes) >= config.ENTRY_THRESHOLD:
                if self.place_order("buy", pair, config.ORDER_SIZE):
                    self.positions.append(Position(pair, current_price, config.ORDER_SIZE, "combined"))
                    self.record_trade(pair, "enter", current_price, config.ORDER_SIZE, "combined")
                    logger.info("Entered %s based on %d strategies", pair, len(entry_votes))

        # Exit checks for each open position
        for pos in list(self.positions):
            try:
                current_price = self.exchange.fetch_ticker(pos.pair)["last"]
            except Exception as exc:
                logger.warning("Failed to fetch ticker for %s: %s", pos.pair, exc)
                current_price = pos.entry_price

            exit_votes = [s for s in self.strategies if s.pair == pos.pair and s.should_exit(pos)]
            change_pct = (current_price - pos.entry_price) / pos.entry_price * 100
            risk_exit = False
            if config.TAKE_PROFIT_PCT and change_pct >= config.TAKE_PROFIT_PCT:
                logger.info("Take profit reached on %s: %.2f%%", pos.pair, change_pct)
                risk_exit = True
            elif config.STOP_LOSS_PCT and change_pct <= -config.STOP_LOSS_PCT:
                logger.info("Stop loss reached on %s: %.2f%%", pos.pair, change_pct)
                risk_exit = True

            if len(exit_votes) >= config.EXIT_THRESHOLD or risk_exit:
                if self.place_order("sell", pos.pair, pos.amount):
                    pnl = (current_price - pos.entry_price) * pos.amount
                    self.closed_profit += pnl
                    logger.info("Exiting %s opened at %.2f with P/L %.2f", pos.pair, pos.entry_price, pnl)
                    self.record_trade(pos.pair, "exit", current_price, pos.amount, "combined")
                    self.positions.remove(pos)

