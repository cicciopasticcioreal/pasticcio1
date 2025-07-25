import importlib
import logging
from dataclasses import dataclass, field
from typing import List, Any
import csv
import os
import time
import json

import pandas as pd

import ccxt
import psutil

from . import config
from .strategy import Strategy

# Configure logging with separate files for trading activity and system events
logging.basicConfig(level=getattr(logging, config.LOG_LEVEL))
trade_logger = logging.getLogger("trading")
system_logger = logging.getLogger("system")

trade_handler = logging.FileHandler(config.TRADING_LOG_PATH)
system_handler = logging.FileHandler(config.SYSTEM_LOG_PATH)
formatter = logging.Formatter("%(asctime)s %(levelname)s:%(message)s")
for h in (trade_handler, system_handler):
    h.setFormatter(formatter)

trade_logger.addHandler(trade_handler)
system_logger.addHandler(system_handler)

trade_logger.setLevel(getattr(logging, config.LOG_LEVEL))
system_logger.setLevel(getattr(logging, config.LOG_LEVEL))

@dataclass
class Position:
    """Representation of an open position."""
    pair: str
    entry_price: float
    amount: float
    strategy: str
    timestamp: float = field(default_factory=time.time)
    partial_taken: bool = False
    highest_price: float = 0.0
    strategies: List[str] = field(default_factory=list)

@dataclass
class TradingBot:
    """Core trading bot class."""

    exchange_id: str = config.EXCHANGE_ID
    strategies: List[Strategy] = field(default_factory=list)
    positions: List[Position] = field(default_factory=list)
    closed_profit: float = 0.0
    data_path: str = config.DATA_PATH
    weights: dict = field(default_factory=dict)

    def __post_init__(self):
        self.exchange = getattr(ccxt, self.exchange_id)({
            "apiKey": config.EXCHANGE_API_KEY,
            "secret": config.EXCHANGE_SECRET,
            "enableRateLimit": True,
        })
        self.load_weights()
        self.auto_select_pairs()
        self.auto_select_strategies()
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

    def load_weights(self) -> None:
        """Load strategy weights from disk."""
        if os.path.exists(config.WEIGHTS_PATH):
            with open(config.WEIGHTS_PATH) as f:
                self.weights = json.load(f)
        else:
            self.weights = {name: 1.0 for name in config.STRATEGIES}

    def save_weights(self) -> None:
        """Persist strategy weights to disk."""
        if not self.weights:
            return
        with open(config.WEIGHTS_PATH, "w") as f:
            json.dump(self.weights, f)

    def adjust_weights(self, strategies: List[str], profit: float) -> None:
        """Update weights based on trade outcome."""
        for name in strategies:
            w = self.weights.get(name, 1.0)
            if profit > 0:
                w += 0.1
            else:
                w = max(0.1, w - 0.1)
            self.weights[name] = round(w, 4)
        self.save_weights()
        for strat in self.strategies:
            if strat.__class__.__name__ in strategies:
                strat.weight = self.weights[strat.__class__.__name__]

    def auto_select_pairs(self) -> None:
        """Populate config.TRADING_PAIRS with the most active markets."""
        if not config.AUTO_SELECT_PAIRS:
            return
        try:
            tickers = self.exchange.fetch_tickers()
        except Exception as exc:
            system_logger.warning("Failed to auto select pairs: %s", exc)
            return
        candidates = [
            (sym, info.get("quoteVolume", 0))
            for sym, info in tickers.items()
            if sym.endswith("/USDT")
        ]
        candidates.sort(key=lambda x: x[1], reverse=True)
        config.TRADING_PAIRS = [sym for sym, _ in candidates[: config.AUTO_PAIR_COUNT]] or config.TRADING_PAIRS
        system_logger.info("Auto selected pairs: %s", config.TRADING_PAIRS)

    def auto_select_strategies(self) -> None:
        """Load all available strategies for automatic selection."""
        if not config.AUTO_SELECT_STRATEGIES:
            return
        module = importlib.import_module("jasperboy.strategy")
        names = []
        for name in dir(module):
            obj = getattr(module, name)
            if isinstance(obj, type) and issubclass(obj, Strategy) and obj is not Strategy:
                names.append(name)
        config.STRATEGIES = names or config.STRATEGIES
        system_logger.info("Auto selected strategies: %s", config.STRATEGIES)

    def load_strategies(self):
        """Dynamically load strategies from config."""
        for pair in config.TRADING_PAIRS:
            for name in config.STRATEGIES:
                module = importlib.import_module("jasperboy.strategy")
                cls = getattr(module, name)
                strategy = cls(self.exchange, pair, config.TIMEFRAME)
                strategy.weight = self.weights.get(name, 1.0)
                self.strategies.append(strategy)
        system_logger.info("Loaded strategies: %s", [s.__class__.__name__ for s in self.strategies])

    def place_order(self, side: str, pair: str, amount: float) -> Any:
        """Execute an order on the exchange or simulate it."""
        if config.SIMULATE:
            trade_logger.info("Simulated %s order for %s %s", side, amount, pair)
            return {"simulated": True}
        try:
            if side == "buy":
                return self.exchange.create_market_buy_order(pair, amount)
            return self.exchange.create_market_sell_order(pair, amount)
        except Exception as exc:
            trade_logger.warning("Failed to place %s order: %s", side, exc)
            return None

    def check_system_health(self) -> None:
        """Log basic system health metrics using psutil."""
        cpu = psutil.cpu_percent()
        mem = psutil.virtual_memory().percent
        disk = psutil.disk_usage("/").percent
        system_logger.debug(
            "System health - CPU: %.1f%% MEM: %.1f%% DISK: %.1f%%",
            cpu,
            mem,
            disk,
        )

    def evaluate(self):
        """Evaluate strategies and manage positions for all pairs."""
        self.check_system_health()
        # Entry checks for each pair
        for pair in config.TRADING_PAIRS:
            try:
                current_price = self.exchange.fetch_ticker(pair)["last"]
            except Exception as exc:
                system_logger.warning("Failed to fetch ticker for %s: %s", pair, exc)
                continue

            entry_votes = [s for s in self.strategies if s.pair == pair and s.should_enter()]
            weight_sum = sum(getattr(s, "weight", 1.0) for s in entry_votes)
            if weight_sum >= config.WEIGHT_THRESHOLD and len(self.positions) < config.MAX_POSITIONS:
                if self.place_order("buy", pair, config.ORDER_SIZE):
                    self.positions.append(
                        Position(
                            pair,
                            current_price,
                            config.ORDER_SIZE,
                            "combined",
                            highest_price=current_price,
                            strategies=[s.__class__.__name__ for s in entry_votes],
                        )
                    )
                    self.record_trade(pair, "enter", current_price, config.ORDER_SIZE, "combined")
                    trade_logger.info("Entered %s with weight %.2f", pair, weight_sum)

        # Exit checks for each open position
        for pos in list(self.positions):
            try:
                current_price = self.exchange.fetch_ticker(pos.pair)["last"]
            except Exception as exc:
                system_logger.warning("Failed to fetch ticker for %s: %s", pos.pair, exc)
                current_price = pos.entry_price

            exit_votes = [s for s in self.strategies if s.pair == pos.pair and s.should_exit(pos)]
            exit_weight = sum(getattr(s, "weight", 1.0) for s in exit_votes)
            change_pct = (current_price - pos.entry_price) / pos.entry_price * 100
            pos.highest_price = max(pos.highest_price, current_price)
            risk_exit = False
            if (
                config.PARTIAL_TAKE_PROFIT_PCT
                and not pos.partial_taken
                and change_pct >= config.PARTIAL_TAKE_PROFIT_PCT
            ):
                close_amt = pos.amount * config.PARTIAL_TAKE_PROFIT_RATIO
                if self.place_order("sell", pos.pair, close_amt):
                    pnl = (current_price - pos.entry_price) * close_amt
                    self.closed_profit += pnl
                    pos.amount -= close_amt
                    pos.partial_taken = True
                    self.record_trade(pos.pair, "partial_exit", current_price, close_amt, "combined")
                    trade_logger.info(
                        "Partial take profit on %s for %.2f at %.2f%%",
                        pos.pair,
                        close_amt,
                        change_pct,
                    )

            if config.TAKE_PROFIT_PCT and change_pct >= config.TAKE_PROFIT_PCT:
                trade_logger.info("Take profit reached on %s: %.2f%%", pos.pair, change_pct)
                risk_exit = True
            elif config.STOP_LOSS_PCT and change_pct <= -config.STOP_LOSS_PCT:
                trade_logger.info("Stop loss reached on %s: %.2f%%", pos.pair, change_pct)
                risk_exit = True

            if (
                config.TRAILING_STOP_PCT
                and pos.highest_price > 0
                and current_price <= pos.highest_price * (1 - config.TRAILING_STOP_PCT / 100)
            ):
                trade_logger.info("Trailing stop triggered on %s", pos.pair)
                risk_exit = True

            if exit_weight >= config.WEIGHT_THRESHOLD or risk_exit:
                if self.place_order("sell", pos.pair, pos.amount):
                    pnl = (current_price - pos.entry_price) * pos.amount
                    self.closed_profit += pnl
                    trade_logger.info(
                        "Exiting %s opened at %.2f with P/L %.2f", pos.pair, pos.entry_price, pnl
                    )
                    self.record_trade(pos.pair, "exit", current_price, pos.amount, "combined")
                    self.adjust_weights(pos.strategies, pnl)
                    self.positions.remove(pos)

