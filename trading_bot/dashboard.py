from flask import Flask, render_template_string
import csv
import os

from . import config

app = Flask(__name__)

HTML = """
<!doctype html>
<title>Trading Bot Dashboard</title>
<h1>Trading Bot Dashboard</h1>
<p>Pair: {{ pair }} | Timeframe: {{ timeframe }} | Exchange: {{ exchange }} | Simulate: {{ simulate }}</p>
<p>Total Closed P/L: {{ total_pnl }}</p>
<h2>Open Positions</h2>
<table border="1">
    <tr><th>Strategy</th><th>Entry Price</th><th>Amount</th><th>P/L</th></tr>
    {% for p in positions %}
    <tr><td>{{ p.strategy }}</td><td>{{ p.entry_price }}</td><td>{{ p.amount }}</td><td>{{ p.pnl }}</td></tr>
    {% endfor %}
</table>
<p><a href="/trades">Trade history</a></p>
"""

def create_app(bot):
    @app.route("/")
    def index():
        positions = []
        for p in bot.positions:
            current = bot.exchange.fetch_ticker(config.TRADING_PAIR)["last"]
            pnl = (current - p.entry_price) * p.amount
            positions.append({"strategy": p.strategy, "entry_price": p.entry_price, "amount": p.amount, "pnl": round(pnl, 2)})
        return render_template_string(
            HTML,
            positions=positions,
            pair=config.TRADING_PAIR,
            timeframe=config.TIMEFRAME,
            exchange=config.EXCHANGE_ID,
            simulate=config.SIMULATE,
            total_pnl=round(bot.closed_profit, 2),
        )

    @app.route("/trades")
    def trades():
        if not bot.data_path or not os.path.exists(bot.data_path):
            rows = []
        else:
            with open(bot.data_path) as f:
                rows = list(csv.reader(f))[1:][-20:]
        history_html = """
        <h1>Recent Trades</h1>
        <table border='1'>
            <tr><th>Timestamp</th><th>Action</th><th>Price</th><th>Amount</th><th>Strategy</th></tr>
            {% for r in rows %}
            <tr>{% for c in r %}<td>{{ c }}</td>{% endfor %}</tr>
            {% endfor %}
        </table>
        <p><a href='/'>Back</a></p>
        """
        return render_template_string(history_html, rows=rows)

    return app
