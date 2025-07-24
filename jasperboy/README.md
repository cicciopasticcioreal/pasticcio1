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
- `--strategies` to choose which strategies to load
- `--simulate` to disable real order placement
- `--refresh-interval` seconds between evaluations

The dashboard will start on the configured port (default `5000`).

Environment variables can also configure the bot.  See `config.py` for the
full list.
