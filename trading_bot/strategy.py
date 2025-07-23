import abc
import logging
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)

class Strategy(abc.ABC):
    """Abstract base class for trading strategies."""

    def __init__(self, exchange, pair: str, timeframe: str):
        self.exchange = exchange
        self.pair = pair
        self.timeframe = timeframe
        self.data = pd.DataFrame()

    def update_data(self):
        """Fetch recent OHLCV data from the exchange."""
        try:
            ohlcv = self.exchange.fetch_ohlcv(self.pair, timeframe=self.timeframe)
        except Exception as exc:
            logger.warning("Failed to fetch OHLCV data: %s", exc)
            return
        self.data = pd.DataFrame(
            ohlcv,
            columns=["timestamp", "open", "high", "low", "close", "volume"],
        )

    @abc.abstractmethod
    def should_enter(self) -> bool:
        """Return True if a position should be opened."""

    @abc.abstractmethod
    def should_exit(self, position: Any) -> bool:
        """Return True if a position should be closed."""

class MovingAverageStrategy(Strategy):
    """Simple moving average crossover strategy."""

    short_window = 7
    long_window = 25

    def should_enter(self) -> bool:
        self.update_data()
        if len(self.data) < self.long_window:
            return False
        short_ma = self.data["close"].rolling(self.short_window).mean().iloc[-1]
        long_ma = self.data["close"].rolling(self.long_window).mean().iloc[-1]
        return short_ma > long_ma

    def should_exit(self, position: Any) -> bool:
        self.update_data()
        short_ma = self.data["close"].rolling(self.short_window).mean().iloc[-1]
        long_ma = self.data["close"].rolling(self.long_window).mean().iloc[-1]
        return short_ma < long_ma

class RSIStrategy(Strategy):
    """Relative Strength Index strategy."""

    rsi_period = 14
    overbought = 70
    oversold = 30

    def _rsi(self) -> float:
        delta = self.data["close"].diff()
        up = delta.clip(lower=0).ewm(alpha=1 / self.rsi_period).mean()
        down = -delta.clip(upper=0).ewm(alpha=1 / self.rsi_period).mean()
        rs = up / down
        return 100 - (100 / (1 + rs)).iloc[-1]

    def should_enter(self) -> bool:
        self.update_data()
        if len(self.data) < self.rsi_period:
            return False
        return self._rsi() < self.oversold

    def should_exit(self, position: Any) -> bool:
        self.update_data()
        if len(self.data) < self.rsi_period:
            return False
        return self._rsi() > self.overbought

