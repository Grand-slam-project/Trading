import hmac
import hashlib
import time
import requests
from urllib.parse import urlencode


class BinanceClient:
    """
    Binance API client for account balances and personal trade history.
    """
    def __init__(self, api_key: str, secret_key: str):
        self.api_key = api_key
        self.secret_key = secret_key.encode("utf-8")
        self.base_url = "https://api.binance.com"

    def _sign(self, query_params: dict) -> str:
        query_string = urlencode(query_params)
        return hmac.new(
            self.secret_key,
            query_string.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()

    def _signed_get(self, path: str, params: dict | None = None, timeout: int = 5) -> dict | list:
        request_params = {
            **(params or {}),
            "timestamp": int(time.time() * 1000),
            "recvWindow": 60000
        }
        request_params["signature"] = self._sign(request_params)
        headers = {
            "X-MBX-APIKEY": self.api_key
        }
        res = requests.get(f"{self.base_url}{path}", headers=headers, params=request_params, timeout=timeout)
        if res.status_code != 200:
            raise Exception(f"Binance API call failed (status {res.status_code}): {res.text}")
        return res.json()

    def _get_tickers(self) -> dict:
        url = f"{self.base_url}/api/v3/ticker/price"
        try:
            res = requests.get(url, timeout=5)
            if res.status_code == 200:
                data = res.json()
                tickers = {}
                for item in data:
                    symbol = item.get("symbol", "").upper()
                    tickers[symbol] = float(item.get("price", 0.0))
                return tickers
        except Exception:
            pass
        return {}

    def get_balance(self) -> dict:
        data = self._signed_get("/api/v3/account")
        tickers = self._get_tickers()

        balances = data.get("balances", [])
        holdings = []
        total_eval = 0.0
        available_cash = 0.0

        for item in balances:
            asset = item.get("asset", "").upper()
            try:
                free_val = float(item.get("free", 0.0))
                locked_val = float(item.get("locked", 0.0))
            except (ValueError, TypeError):
                free_val = 0.0
                locked_val = 0.0

            total_qty = free_val + locked_val
            if total_qty <= 0.000001:
                continue

            if asset in ("USDT", "BUSD", "USDC"):
                if asset == "USDT":
                    available_cash = free_val
                total_eval += total_qty
                continue

            pair = f"{asset}USDT"
            curr_price = tickers.get(pair, 0.0)
            eval_price = curr_price * total_qty
            total_eval += eval_price

            holdings.append({
                "symbol": asset,
                "name": asset,
                "qty": total_qty,
                "avg_price": 0.0,
                "current_price": curr_price,
                "cost_amount": 0.0,
                "eval_amount": eval_price,
                "profit": 0.0,
                "profit_rate": 0.0,
                "currency": "USDT",
                "cost_amount_krw": 0.0,
                "eval_amount_krw": 0.0,
                "profit_krw": 0.0,
                "source": "LIVE_BALANCE",
                "asset_type": "CRYPTO",
            })

        return {
            "total_evaluation": total_eval,
            "available_cash": available_cash,
            "available_cash_currency": "USDT",
            "currency": "USDT",
            "holdings": holdings,
            "raw": data
        }

    def list_my_trades(self, symbol: str, limit: int = 1000, from_id: int | None = None) -> list[dict]:
        params = {
            "symbol": str(symbol or "").upper(),
            "limit": max(1, min(int(limit or 1000), 1000)),
        }
        if from_id is not None:
            params["fromId"] = int(from_id)
        data = self._signed_get("/api/v3/myTrades", params=params, timeout=10)
        return data if isinstance(data, list) else []
