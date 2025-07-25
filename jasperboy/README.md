# JasperBoy Trading Bot

This folder contains a small experimental trading bot using `ccxt`.  It can
run in simulation mode or connect directly to an exchange.  Strategies are
loaded dynamically and evaluated periodically.  A small Flask dashboard shows
open positions, recent trades and a cumulative P/L chart.

## Setup

Install dependencies in a virtual environment:

```bash
pip install -r ../requirements.txt
```

## Usage

Run the bot with the default configuration:

```bash
python -m jasperboy.run_bot
```

Key options include:

- `--pairs` to specify a comma separated list of trading pairs
- `--auto-pairs` to let the bot choose the most liquid pairs automatically
- `--strategies` to choose which strategies to load
- `--auto-strategies` to load all built-in strategies automatically
- `--simulate` to disable real order placement
- `--refresh-interval` seconds between evaluations
- `--max-positions` limit concurrent open trades
- `--partial-tp` percentage gain to trigger a partial take profit
- `--trailing-stop` trailing stop percentage
- `--weight-threshold` minimum combined strategy weight before a trade

Strategy weights adjust automatically based on trade outcomes and are stored in
`weights.json`.

The dashboard will start on the configured port (default `5000`).

### Backtesting

Historical strategies can be tested offline with the built in backtester.  It
reports total profit along with common performance metrics:

```bash
python -m jasperboy.backtest --pair BTC/USDT --timeframe 1h --limit 500
```

This downloads OHLCV data using `ccxt` and runs the configured strategies.
At the end of the run it prints profit, Sharpe ratio and maximum drawdown.

Environment variables can also configure the bot.  See `config.py` for the
full list, including `AUTO_SELECT_PAIRS` and `AUTO_SELECT_STRATEGIES` which
enable automatic selection of pairs and strategies.
`WEIGHT_THRESHOLD` adjusts the minimum combined weight of strategies before
trades are executed, while strategy scores are saved in `weights.json`.

Trading activity is logged to `trading.log` while system events are logged to
`system.log`.

## Running in Google Colab

The bot can also be tested in a Colab notebook using simulation mode.  Create a
new notebook and run the following cells:

```python
!git clone https://github.com/your_username/your_repo.git
%cd your_repo
!pip install -r requirements.txt
!python -m jasperboy.run_bot --simulate --refresh-interval 30
```

Replace the repository URL with the location of your fork.  The `--simulate`
flag disables real order placement so the bot can run without credentials.  A
small Flask dashboard will be available on port `5000`.  You can use tools like
`pyngrok` if you need to expose the dashboard outside of Colab.
