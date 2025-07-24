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
