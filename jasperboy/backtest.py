import argparse
import logging
from typing import List

import ccxt
import pandas as pd
import json
import os

from .strategy import Strategy
from .bot import Position
from . import config

logger = logging.getLogger("backtest")

class Backtester:
    """Simple backtesting engine using historical OHLCV data."""

    def __init__(
        self,
        exchange_id: str,
        pair: str,
        timeframe: str,
        strategies: List[Strategy],
        order_size: float = 1,
    ):
        self.exchange = getattr(ccxt, exchange_id)()
        self.pair = pair
        self.timeframe = timeframe
        self.strategies = strategies
        self.order_size = order_size
        self.positions: List[Position] = []
        self.closed_profit = 0.0
        self.profit_curve: List[float] = []
        self.metrics: dict[str, float] = {}

    def run(self, limit: int = 500):
        """Execute backtest and compute performance metrics."""
        ohlcv = self.exchange.fetch_ohlcv(
            self.pair, timeframe=self.timeframe, limit=limit
        )
        df = pd.DataFrame(
            ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"]
        )
        for i in range(len(df)):
            window = df.iloc[: i + 1]
            price = window["close"].iloc[-1]
            for s in self.strategies:
                s.data = window
            if not self.positions:
                entry_votes = [s for s in self.strategies if s.should_enter()]
                weight_sum = sum(getattr(s, "weight", 1.0) for s in entry_votes)
                if weight_sum >= config.WEIGHT_THRESHOLD:
                    self.positions.append(
                        Position(
                            self.pair,
                            price,
                            self.order_size,
                            "backtest",
                            highest_price=price,
                        )
                    )
            else:
                pos = self.positions[0]
                exit_votes = [s for s in self.strategies if s.should_exit(pos)]
                weight_exit = sum(getattr(s, "weight", 1.0) for s in exit_votes)
                if weight_exit >= config.WEIGHT_THRESHOLD:
                    pnl = (price - pos.entry_price) * pos.amount
                    self.closed_profit += pnl
                    self.positions.clear()
            # Track equity curve
            equity = self.closed_profit
            if self.positions:
                equity += (price - self.positions[0].entry_price) * self.positions[0].amount
            self.profit_curve.append(equity)

        if self.positions:
            last_price = df["close"].iloc[-1]
            pnl = (last_price - self.positions[0].entry_price) * self.positions[0].amount
            self.closed_profit += pnl
            self.profit_curve[-1] = self.closed_profit

        self._compute_metrics()
        return self.closed_profit

    def _compute_metrics(self) -> None:
        """Calculate sharpe ratio and max drawdown for the profit curve."""
        if not self.profit_curve:
            self.metrics = {"sharpe": 0.0, "max_drawdown": 0.0}
            return
        curve = pd.Series(self.profit_curve)
        returns = curve.pct_change().fillna(0)
        sharpe = 0.0
        if returns.std() != 0:
            sharpe = (returns.mean() / returns.std()) * (len(returns) ** 0.5)
        roll_max = curve.cummax()
        drawdown = (curve - roll_max) / roll_max
        max_drawdown = drawdown.min() if not drawdown.empty else 0.0
        self.metrics = {
            "sharpe": round(sharpe, 4),
            "max_drawdown": round(float(max_drawdown), 4),
        }


def main(argv=None):
    parser = argparse.ArgumentParser(description="Run backtest")
    parser.add_argument("--pair", default=config.TRADING_PAIR)
    parser.add_argument("--timeframe", default=config.TIMEFRAME)
    parser.add_argument("--exchange", default=config.EXCHANGE_ID)
    parser.add_argument("--limit", type=int, default=500)
    parser.add_argument("--strategies", default=','.join(config.STRATEGIES))
    parser.add_argument("--weight-threshold", type=float, default=config.WEIGHT_THRESHOLD)
    args = parser.parse_args(argv)

    config.TRADING_PAIR = args.pair
    config.TIMEFRAME = args.timeframe
    config.EXCHANGE_ID = args.exchange
    config.STRATEGIES = [s.strip() for s in args.strategies.split(',') if s.strip()]
    config.WEIGHT_THRESHOLD = args.weight_threshold

    strategies = []
    weights = {}
    if os.path.exists(config.WEIGHTS_PATH):
        with open(config.WEIGHTS_PATH) as f:
            weights = json.load(f)
    for name in config.STRATEGIES:
        mod = __import__('jasperboy.strategy', fromlist=[name])
        cls = getattr(mod, name)
        strat = cls(None, args.pair, args.timeframe)
        strat.weight = weights.get(name, 1.0)
        strategies.append(strat)

    tester = Backtester(
        args.exchange, args.pair, args.timeframe, strategies, config.ORDER_SIZE
    )
    profit = tester.run(limit=args.limit)
    metrics = tester.metrics
    print(
        f"Backtest completed. Profit: {profit:.2f} | Sharpe: {metrics['sharpe']:.2f} | Max DD: {metrics['max_drawdown']:.2%}"
    )


if __name__ == "__main__":
    main()
