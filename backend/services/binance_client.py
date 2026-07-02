import hmac
import hashlib
import time
import requests
from urllib.parse import urlencode


def _normalize_spot_symbol(symbol: str) -> str:
    normalized = str(symbol or "").strip().upper().replace("_", "").replace("-", "").replace("/", "")
    if not normalized:
        return ""
    if normalized in {"BTC", "ETH", "XRP", "SOL", "BNB", "ADA", "DOGE"}:
        return f"{normalized}USDT"
    return normalized


def _normalize_side(side: str) -> str:
    side_upper = str(side or "").strip().upper()
    if side_upper not in {"BUY", "SELL"}:
        raise ValueError("바이낸스 주문 방향은 BUY 또는 SELL이어야 합니다.")
    return side_upper


def _normalize_order_type(order_type: str) -> str:
    order_type_upper = str(order_type or "").strip().upper()
    if order_type_upper not in {"LIMIT", "MARKET"}:
        raise ValueError("바이낸스 주문 유형은 LIMIT 또는 MARKET이어야 합니다.")
    return order_type_upper


def _to_float(value, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


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


class BinanceFuturesClient:
    """
    바이낸스 USD-M 선물 API 클라이언트입니다. 기본적으로 TESTNET/MOCK 사용을 우선합니다.
    """
    BASE_URLS = {
        "REAL": "https://fapi.binance.com",
        "MOCK": "https://testnet.binancefuture.com",
        "TESTNET": "https://testnet.binancefuture.com",
        "DEMO": "https://testnet.binancefuture.com",
    }

    def __init__(self, api_key: str, secret_key: str, env: str = "TESTNET"):
        self.api_key = api_key
        self.secret_key = secret_key.encode("utf-8")
        self.env = str(env or "TESTNET").upper()
        self.base_url = self.BASE_URLS.get(self.env, self.BASE_URLS["TESTNET"])

    def _sign(self, query_params: dict) -> str:
        query_string = urlencode(query_params)
        return hmac.new(self.secret_key, query_string.encode("utf-8"), hashlib.sha256).hexdigest()

    def _signed_request(self, method: str, path: str, params: dict | None = None):
        request_params = {
            **(params or {}),
            "timestamp": int(time.time() * 1000),
            "recvWindow": 60000,
        }
        request_params["signature"] = self._sign(request_params)
        headers = {"X-MBX-APIKEY": self.api_key}
        res = requests.request(
            method.upper(),
            f"{self.base_url}{path}",
            headers=headers,
            params=request_params,
            timeout=5,
        )
        if res.status_code not in (200, 201):
            raise Exception(f"바이낸스 선물 API 호출 실패 (상태 코드 {res.status_code}): {res.text}")
        return res.json() if res.text else {}

    def get_balance(self) -> dict:
        """
        USD-M 선물 계좌/포지션 정보를 대시보드 공통 잔고 포맷으로 반환합니다.
        """
        account = self._signed_request("GET", "/fapi/v3/account")
        position_risk_by_symbol = {}
        try:
            for risk in self.get_position_risk():
                risk_amount = _to_float(risk.get("positionAmt"))
                if abs(risk_amount) <= 0:
                    continue
                risk_symbol = str(risk.get("symbol") or "").upper()
                risk_side = str(risk.get("positionSide") or "BOTH").upper()
                position_risk_by_symbol[(risk_symbol, risk_side)] = risk
                position_risk_by_symbol.setdefault((risk_symbol, "BOTH"), risk)
        except Exception:
            position_risk_by_symbol = {}

        total_wallet = float(account.get("totalWalletBalance") or 0)
        available_balance = float(account.get("availableBalance") or 0)
        holdings = []
        for position in account.get("positions", []) or []:
            amount = _to_float(position.get("positionAmt"))
            if abs(amount) <= 0:
                continue
            symbol = position.get("symbol")
            position_side = str(position.get("positionSide") or "BOTH").upper()
            risk = position_risk_by_symbol.get((str(symbol or "").upper(), position_side)) or {}
            entry_price = _to_float(
                risk.get("entryPrice")
                or risk.get("breakEvenPrice")
                or position.get("entryPrice")
                or position.get("breakEvenPrice")
            )
            mark_price = _to_float(risk.get("markPrice") or position.get("markPrice"))
            notional = _to_float(risk.get("notional") or position.get("notional"))
            if mark_price <= 0 and amount:
                mark_price = abs(notional / amount) if notional else 0.0
            if mark_price <= 0 and symbol:
                try:
                    mark_price = _to_float(self.get_price(symbol).get("current_price"))
                except Exception:
                    mark_price = 0.0
            if entry_price <= 0 and amount and mark_price:
                # Testnet 계정이 entryPrice를 0으로 늦게 반영하는 경우 화면 붕괴 방지용 임시 추정값입니다.
                entry_price = mark_price
            unrealized = _to_float(risk.get("unRealizedProfit") or position.get("unrealizedProfit"))
            evaluation_amount = abs(notional) if notional else abs(amount * mark_price)
            invested_notional = abs(amount * entry_price)
            holdings.append({
                "symbol": symbol,
                "name": symbol,
                "qty": amount,
                "avg_price": entry_price,
                "current_price": mark_price,
                "eval_amount": evaluation_amount,
                "profit": unrealized,
                "profit_rate": (unrealized / invested_notional) * 100.0 if invested_notional else 0.0,
                "currency": "USDT",
                "position_side": position_side,
                "position_direction": "LONG" if amount > 0 else "SHORT",
                "leverage": position.get("leverage") or risk.get("leverage"),
                "liquidation_price": risk.get("liquidationPrice") or position.get("liquidationPrice"),
                "avg_price_source": "POSITION_RISK" if risk else "ACCOUNT_FALLBACK",
            })
        return {
            "total_evaluation": total_wallet,
            "available_cash": available_balance,
            "currency": "USD",
            "available_cash_currency": "USDT",
            "available_cash_supported": True,
            "available_cash_source": "BINANCE_UM_FUTURES_ACCOUNT",
            "holdings": holdings,
            "raw": account,
        }

    def get_position_risk(self, symbol: str | None = None) -> list[dict]:
        params = {}
        if symbol:
            params["symbol"] = _normalize_spot_symbol(symbol)
        data = self._signed_request("GET", "/fapi/v3/positionRisk", params)
        return data if isinstance(data, list) else [data]

    def get_price(self, symbol: str) -> dict:
        normalized_symbol = _normalize_spot_symbol(symbol)
        if not normalized_symbol:
            raise ValueError("바이낸스 선물 현재가 조회를 위한 심볼이 비어 있습니다.")
        res = requests.get(
            f"{self.base_url}/fapi/v1/ticker/24hr",
            params={"symbol": normalized_symbol},
            timeout=5,
        )
        if res.status_code != 200:
            raise Exception(f"바이낸스 선물 현재가 조회 실패 (상태 코드 {res.status_code}): {res.text}")
        data = res.json()
        return {
            "symbol": normalized_symbol,
            "current_price": float(data.get("lastPrice") or 0),
            "change_rate": float(data.get("priceChangePercent") or 0),
            "currency": "USDT",
            "raw": data,
        }

    def place_order(
        self,
        symbol: str,
        qty: float,
        side: str,
        ord_type: str,
        price: float = None,
        position_side: str | None = None,
        reduce_only: bool = False,
        leverage: int | None = None,
        margin_type: str | None = None,
    ) -> dict:
        normalized_symbol = _normalize_spot_symbol(symbol)
        side_upper = _normalize_side(side)
        order_type = _normalize_order_type(ord_type)
        quantity = float(qty)
        if not normalized_symbol:
            raise ValueError("바이낸스 선물 주문 심볼이 비어 있습니다.")
        if quantity <= 0:
            raise ValueError("바이낸스 선물 주문 수량은 0보다 커야 합니다.")

        settings_result = {}
        if margin_type:
            settings_result["margin_type"] = self.change_margin_type(normalized_symbol, margin_type)
        if leverage is not None:
            settings_result["leverage"] = self.change_leverage(normalized_symbol, leverage)

        params = {
            "symbol": normalized_symbol,
            "side": side_upper,
            "type": order_type,
            "quantity": f"{quantity:.12g}",
            "newOrderRespType": "RESULT",
        }
        if position_side:
            params["positionSide"] = str(position_side).upper()
        if reduce_only:
            params["reduceOnly"] = "true"
        if order_type == "LIMIT":
            if price is None or float(price) <= 0:
                raise ValueError("바이낸스 선물 지정가 주문에는 0보다 큰 가격이 필요합니다.")
            params.update({
                "price": f"{float(price):.12g}",
                "timeInForce": "GTC",
            })

        data = self._signed_request("POST", "/fapi/v1/order", params)
        return {
            "order_id": str(data.get("orderId") or ""),
            "client_order_id": data.get("clientOrderId"),
            "status": data.get("status") or "ORDERED",
            "symbol": normalized_symbol,
            "side": side_upper,
            "type": order_type,
            "futures_settings": settings_result,
            "raw": data,
        }

    def change_leverage(self, symbol: str, leverage: int) -> dict:
        normalized_symbol = _normalize_spot_symbol(symbol)
        try:
            leverage_int = int(leverage)
        except (TypeError, ValueError):
            raise ValueError("바이낸스 선물 레버리지는 1~125 사이 정수여야 합니다.")
        if leverage_int < 1 or leverage_int > 125:
            raise ValueError("바이낸스 선물 레버리지는 1~125 사이로 입력해 주세요.")
        return self._signed_request(
            "POST",
            "/fapi/v1/leverage",
            {"symbol": normalized_symbol, "leverage": leverage_int},
        )

    def get_max_leverage(self, symbol: str) -> int | None:
        normalized_symbol = _normalize_spot_symbol(symbol)
        data = self._signed_request("GET", "/fapi/v1/leverageBracket", {"symbol": normalized_symbol})
        bracket_rows = data if isinstance(data, list) else [data]
        max_leverage = None
        for row in bracket_rows:
            if str(row.get("symbol") or "").upper() != normalized_symbol:
                continue
            for bracket in row.get("brackets", []) or []:
                try:
                    initial_leverage = int(bracket.get("initialLeverage"))
                except (TypeError, ValueError):
                    continue
                max_leverage = max(max_leverage or 0, initial_leverage)
        return max_leverage

    def change_margin_type(self, symbol: str, margin_type: str) -> dict:
        normalized_symbol = _normalize_spot_symbol(symbol)
        normalized_margin_type = str(margin_type or "").upper()
        if normalized_margin_type == "CROSS":
            normalized_margin_type = "CROSSED"
        if normalized_margin_type not in ("CROSSED", "ISOLATED"):
            raise ValueError("바이낸스 선물 마진 모드는 CROSSED 또는 ISOLATED만 지원합니다.")
        try:
            return self._signed_request(
                "POST",
                "/fapi/v1/marginType",
                {"symbol": normalized_symbol, "marginType": normalized_margin_type},
            )
        except Exception as error:
            # Binance는 이미 같은 마진 모드인 경우 -4046을 반환합니다. 이 경우는 실패가 아니라 멱등 성공으로 취급합니다.
            if "-4046" in str(error) or "No need to change margin type" in str(error):
                return {
                    "code": 200,
                    "msg": "margin type already set",
                    "symbol": normalized_symbol,
                    "marginType": normalized_margin_type,
                }
            raise

    def get_position_mode(self) -> dict:
        data = self._signed_request("GET", "/fapi/v1/positionSide/dual")
        is_hedge_mode = str(data.get("dualSidePosition")).lower() == "true"
        return {
            "is_hedge_mode": is_hedge_mode,
            "mode": "HEDGE" if is_hedge_mode else "ONE_WAY",
            "raw": data,
        }

    def test_order(self, symbol: str, qty: float, side: str, ord_type: str, price: float = None) -> dict:
        normalized_symbol = _normalize_spot_symbol(symbol)
        side_upper = _normalize_side(side)
        order_type = _normalize_order_type(ord_type)
        quantity = float(qty)
        params = {
            "symbol": normalized_symbol,
            "side": side_upper,
            "type": order_type,
            "quantity": f"{quantity:.12g}",
        }
        if order_type == "LIMIT":
            if price is None or float(price) <= 0:
                raise ValueError("바이낸스 선물 지정가 테스트 주문에는 0보다 큰 가격이 필요합니다.")
            params.update({"price": f"{float(price):.12g}", "timeInForce": "GTC"})
        data = self._signed_request("POST", "/fapi/v1/order/test", params)
        return {"success": True, "raw": data}

    def get_order_status(self, order_id: str, symbol: str = None) -> dict:
        normalized_symbol = _normalize_spot_symbol(symbol)
        if not normalized_symbol:
            raise ValueError("바이낸스 선물 주문 조회에는 symbol이 필요합니다.")
        data = self._signed_request("GET", "/fapi/v1/order", {"symbol": normalized_symbol, "orderId": order_id})
        executed_qty = float(data.get("executedQty") or 0)
        orig_qty = float(data.get("origQty") or 0)
        return {
            "order_id": str(data.get("orderId") or order_id),
            "status": data.get("status"),
            "executed_qty": executed_qty,
            "remaining_qty": max(orig_qty - executed_qty, 0),
            "raw": data,
        }

    def cancel_order(self, order_id: str, symbol: str = None) -> dict:
        normalized_symbol = _normalize_spot_symbol(symbol)
        if not normalized_symbol:
            raise ValueError("바이낸스 선물 주문 취소에는 symbol이 필요합니다.")
        data = self._signed_request("DELETE", "/fapi/v1/order", {"symbol": normalized_symbol, "orderId": order_id})
        return {
            "order_id": str(data.get("orderId") or order_id),
            "status": data.get("status") or "CANCELED",
            "raw": data,
        }
