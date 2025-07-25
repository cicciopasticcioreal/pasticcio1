from flask import Flask, render_template_string
import base64
from io import BytesIO
import csv
import os

from . import config

app = Flask(__name__)

HTML = """
<!doctype html>
<html>
<head>
<title>Trading Bot Dashboard</title>
<style>
body { font-family: Arial, sans-serif; margin: 20px; }
table { border-collapse: collapse; width: 100%; }
th, td { border: 1px solid #ccc; padding: 4px; text-align: center; }
th { background: #eee; }
</style>
</head>
<body>
<h1>Trading Bot Dashboard</h1>
<p>Pairs: {{ pairs }} | Timeframe: {{ timeframe }} | Exchange: {{ exchange }} | Simulate: {{ simulate }}</p>
<p>Refresh: {{ refresh }}s | Total Closed P/L: {{ total_pnl }}</p>
<h2>Open Positions</h2>
<table>
    <tr><th>Pair</th><th>Strategy</th><th>Entry Price</th><th>Amount</th><th>P/L</th><th>P/L %</th></tr>
    {% for p in positions %}
    <tr><td>{{ p.pair }}</td><td>{{ p.strategy }}</td><td>{{ p.entry_price }}</td><td>{{ p.amount }}</td><td>{{ p.pnl }}</td><td>{{ p.pnl_pct }}</td></tr>
    {% endfor %}
</table>
<p><a href="/trades">Trade history</a></p>
<img src="data:image/png;base64,{{ chart }}" alt="P/L chart" />
</body>
</html>
"""

def create_app(bot):
    @app.route("/")
    def index():
        positions = []
        for p in bot.positions:
            current = bot.exchange.fetch_ticker(p.pair)["last"]
            pnl = (current - p.entry_price) * p.amount
            pct = pnl / (p.entry_price * p.amount) * 100 if p.amount else 0
            positions.append({
                "pair": p.pair,
                "strategy": p.strategy,
                "entry_price": p.entry_price,
                "amount": p.amount,
                "pnl": round(pnl, 2),
                "pnl_pct": round(pct, 2),
            })
        chart = generate_pnl_chart(bot.data_path)
        return render_template_string(
            HTML,
            positions=positions,
            pairs=", ".join(config.TRADING_PAIRS),
            timeframe=config.TIMEFRAME,
            exchange=config.EXCHANGE_ID,
            simulate=config.SIMULATE,
            refresh=config.REFRESH_INTERVAL,
            total_pnl=round(bot.closed_profit, 2),
            chart=chart,
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
            <tr><th>Timestamp</th><th>Pair</th><th>Action</th><th>Price</th><th>Amount</th><th>Strategy</th></tr>
            {% for r in rows %}
            <tr>{% for c in r %}<td>{{ c }}</td>{% endfor %}</tr>
            {% endfor %}
        </table>
        <p><a href='/'>Back</a></p>
        """
        return render_template_string(history_html, rows=rows)

    def generate_pnl_chart(csv_path):
        if not csv_path or not os.path.exists(csv_path):
            return ""
        with open(csv_path) as f:
            rows = list(csv.reader(f))[1:]
        pnl = 0
        entries = {}
        curve = []
        for ts, pair, action, price, amount, _ in rows:
            price = float(price)
            amount = float(amount)
            if action == "enter":
                entries.setdefault(pair, []).append((price, amount))
            else:
                entry_price, amt = entries.get(pair, [(price, amount)]).pop(0)
                pnl += (price - entry_price) * amt
            curve.append(pnl)
        if not curve:
            return ""
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots()
        ax.plot(curve)
        ax.set_title("Cumulative P/L")
        buf = BytesIO()
        fig.savefig(buf, format="png")
        plt.close(fig)
        return base64.b64encode(buf.getvalue()).decode()

    return app
