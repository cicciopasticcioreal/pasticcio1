import pytest
from trading_bot.bot import TradingBot
from requests.exceptions import HTTPError, Timeout

class DummyResponse:
    def __init__(self, json_data=None, status_code=200):
        self._json_data = json_data or {}
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise HTTPError(f"{self.status_code} error")

    def json(self):
        return self._json_data

def test_get_price_success(monkeypatch):
    bot = TradingBot("http://example.com")

    def mock_get(url, timeout):
        return DummyResponse({"price": 100.0})

    monkeypatch.setattr("trading_bot.bot.requests.get", mock_get)
    assert bot.get_price("BTC") == 100.0

def test_get_price_http_error(monkeypatch):
    bot = TradingBot("http://example.com")

    def mock_get(url, timeout):
        return DummyResponse(status_code=500)

    monkeypatch.setattr("trading_bot.bot.requests.get", mock_get)
    with pytest.raises(RuntimeError):
        bot.get_price("BTC")

def test_get_price_timeout(monkeypatch):
    bot = TradingBot("http://example.com")

    def mock_get(url, timeout):
        raise Timeout("timeout")

    monkeypatch.setattr("trading_bot.bot.requests.get", mock_get)
    with pytest.raises(RuntimeError):
        bot.get_price("BTC")
