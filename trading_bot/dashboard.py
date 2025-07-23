from flask import Flask, render_template_string

app = Flask(__name__)

HTML = """
<!doctype html>
<title>Trading Bot Dashboard</title>
<h1>Open Positions</h1>
<table border="1">
    <tr><th>Strategy</th><th>Entry Price</th><th>Amount</th></tr>
    {% for p in positions %}
    <tr><td>{{ p.strategy }}</td><td>{{ p.entry_price }}</td><td>{{ p.amount }}</td></tr>
    {% endfor %}
</table>
"""

def create_app(bot):
    @app.route("/")
    def index():
        return render_template_string(HTML, positions=bot.positions)

    return app

