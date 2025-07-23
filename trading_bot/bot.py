import requests
from requests.exceptions import HTTPError, Timeout, RequestException

class TradingBot:
    def __init__(self, base_url: str, timeout: int = 5):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout

    def get_price(self, symbol: str) -> float:
        """Fetch the latest price for a symbol.

        Raises:
            RuntimeError: If the request fails or times out.
        """
        url = f"{self.base_url}/price/{symbol}"
        try:
            resp = requests.get(url, timeout=self.timeout)
            resp.raise_for_status()
        except Timeout:
            raise RuntimeError(f"Request timed out when fetching {symbol}")
        except HTTPError as exc:
            raise RuntimeError(f"HTTP error when fetching {symbol}: {exc}")
        except RequestException as exc:
            raise RuntimeError(f"Request error when fetching {symbol}: {exc}")

        data = resp.json()
        return float(data.get("price"))
