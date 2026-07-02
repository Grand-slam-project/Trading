import os
import threading
from datetime import datetime, timedelta, timezone

import requests
from flask import current_app

from backend.services.auth_service import get_user_id_from_header
from backend.services.supabase_client import query_supabase, query_supabase_as_service_role
from backend.services.binance_client import BinanceClient
from backend.services.toss_client import TossClient


UTC = timezone.utc
_binance_sync_lock = threading.Lock()
_last_binance_sync_time = {}


def _is_broker_order_history_missing_error(error) -> bool:
    """
    broker_order_history 테이블이 아직 배포되지 않은 경우를 식별합니다.
    """
    message = str(error or "").lower()
    return "broker_order_history" in message and ("404" in message or "not found" in message or "could not find" in message)


def _normalize_timestamp(value):
    """
    다양한 시각 표현을 UTC ISO 문자열로 정규화합니다.
    """
    if not value:
        return None
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(float(value), tz=UTC).isoformat()
        except Exception:
            return None

    text = str(value).strip()
    if not text:
        return None

    candidates = [
        text.replace("Z", "+00:00"),
        text,
    ]
    for candidate in candidates:
        try:
            parsed = datetime.fromisoformat(candidate)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=UTC)
            return parsed.astimezone(UTC).isoformat()
        except ValueError:
            continue

    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            parsed = datetime.strptime(text, fmt).replace(tzinfo=UTC)
            return parsed.isoformat()
        except ValueError:
            continue
    return None


def _normalize_date(value):
    """
    날짜를 YYYY-MM-DD로 정규화합니다.
    """
    normalized = _normalize_timestamp(value)
    if normalized:
        return normalized[:10]
    text = str(value or "").strip()
    return text[:10] if text else None


def _to_float(value):
    try:
        if value in (None, ""):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _binance_symbol_assets(symbol: str) -> tuple[str, str]:
    text = str(symbol or "").upper()
    for quote in ("USDT", "BUSD", "USDC", "BTC", "ETH", "BNB", "USD"):
        if text.endswith(quote) and len(text) > len(quote):
            return text[:-len(quote)], quote
    return text, ""


def _normalize_binance_trade_symbol(symbol: str) -> str:
    """
    잔고 API가 BTC와 BTCUSDT를 모두 줄 수 있어 거래내역 조회용 심볼을 안전하게 정규화합니다.
    """
    text = str(symbol or "").strip().upper().replace("_", "").replace("-", "").replace("/", "")
    if not text:
        return ""
    _, quote_asset = _binance_symbol_assets(text)
    return text if quote_asset else f"{text}USDT"


def _normalize_binance_order_type(trade: dict) -> str:
    """
    바이낸스 체결 내역은 주문 유형을 주지 않는 경우가 있어 시장 구분값과 섞지 않고 별도 기본값으로 보존합니다.
    """
    raw_type = trade.get("type") or trade.get("orderType") or trade.get("origType")
    return str(raw_type or "UNKNOWN").upper()


def _map_binance_trade_to_history_row(user_id, broker_env, symbol, trade, exchange="BINANCE"):
    base_asset, quote_asset = _binance_symbol_assets(symbol)
    price = _to_float(trade.get("price")) or 0.0
    qty = _to_float(trade.get("qty")) or 0.0
    quote_qty = _to_float(trade.get("quoteQty"))
    commission = _to_float(trade.get("commission"))
    trade_id = str(trade.get("id") or "")
    order_id = str(trade.get("orderId") or "")
    order_trade_id = f"{order_id}:{trade_id}" if order_id and trade_id else (trade_id or order_id)

    return {
        "user_id": user_id,
        "exchange": exchange,
        "broker_env": str(broker_env or "REAL").upper(),
        "external_order_id": order_trade_id,
        "external_trade_id": trade_id or None,
        "symbol": str(symbol or "").upper(),
        "base_asset": base_asset or None,
        "quote_asset": quote_asset or None,
        "market_country": "US",
        "side": "BUY" if trade.get("isBuyer") or trade.get("buyer") else "SELL",
        "order_type": _normalize_binance_order_type(trade),
        "status": "EXECUTED",
        "raw_status": "FILLED",
        "currency": "USDT" if quote_asset == "USDT" else "USD",
        "price": price,
        "quantity": qty,
        "order_amount": quote_qty if quote_qty is not None else price * qty,
        "filled_quantity": qty,
        "average_filled_price": price,
        "filled_amount": quote_qty if quote_qty is not None else price * qty,
        "commission": commission,
        "commission_asset": trade.get("commissionAsset") or None,
        "ordered_at": _normalize_timestamp((trade.get("time") or 0) / 1000 if trade.get("time") else None),
        "filled_at": _normalize_timestamp((trade.get("time") or 0) / 1000 if trade.get("time") else None),
        "source_api": "binance_futures_user_trades" if exchange == "BINANCE_UM_FUTURES" else "binance_my_trades",
        "raw_payload": trade,
        "last_synced_at": datetime.now(UTC).isoformat(),
    }


def _normalize_toss_order_status(order):
    """
    토스 주문 상태를 내부 상태값으로 정규화합니다.
    """
    raw_status = str(order.get("status") or "").upper()
    execution = order.get("execution") or {}
    filled_quantity = _to_float(
        order.get("executedQuantity")
        or order.get("filledQuantity")
        or execution.get("filledQuantity")
    ) or 0.0
    quantity = _to_float(order.get("quantity")) or 0.0

    if raw_status in {"FILLED", "EXECUTED", "DONE", "COMPLETED"}:
        return "EXECUTED"
    if raw_status in {"CANCELED", "CANCELLED"}:
        return "CANCELED"
    if raw_status in {"REJECTED", "FAILED", "EXPIRED"}:
        return "FAILED"
    if quantity > 0 and 0 < filled_quantity < quantity:
        return "PARTIALLY_FILLED"
    if raw_status in {"PENDING", "APPROVED", "ORDERED", "OPEN", "ACCEPTED", "PARTIAL"}:
        return "OPEN"
    return raw_status or "UNKNOWN"


def _map_toss_order_to_history_row(user_id, broker_env, account_ref, order):
    """
    토스 주문 응답을 broker_order_history용 레코드로 변환합니다.
    """
    execution = order.get("execution") or {}
    quantity = _to_float(order.get("quantity"))
    price = _to_float(order.get("price"))
    filled_quantity = _to_float(
        order.get("executedQuantity")
        or order.get("filledQuantity")
        or execution.get("filledQuantity")
    )
    average_filled_price = _to_float(
        order.get("averageFilledPrice")
        or execution.get("averageFilledPrice")
    )
    filled_amount = _to_float(
        order.get("filledAmount")
        or execution.get("filledAmount")
    )
    commission = _to_float(order.get("commission") or execution.get("commission"))
    tax = _to_float(order.get("tax") or execution.get("tax"))
    order_amount = _to_float(order.get("orderAmount"))
    if order_amount is None and price is not None and quantity is not None:
        order_amount = price * quantity

    symbol = str(order.get("symbol") or "").upper() or None
    market_country = str(order.get("marketCountry") or ("US" if symbol and symbol.isalpha() else "KR")).upper()
    currency = str(order.get("currency") or ("USD" if market_country == "US" else "KRW")).upper()

    return {
        "user_id": user_id,
        "exchange": "TOSS",
        "broker_env": str(broker_env or "REAL").upper(),
        "account_ref": account_ref,
        "external_order_id": str(order.get("orderId") or ""),
        "client_order_id": order.get("clientOrderId"),
        "symbol": symbol,
        "market_country": market_country,
        "side": str(order.get("side") or "").upper() or None,
        "order_type": str(order.get("orderType") or "").upper() or None,
        "time_in_force": str(order.get("timeInForce") or "").upper() or None,
        "status": _normalize_toss_order_status(order),
        "raw_status": str(order.get("status") or "").upper() or None,
        "currency": currency,
        "price": price,
        "quantity": quantity,
        "order_amount": order_amount,
        "filled_quantity": filled_quantity,
        "average_filled_price": average_filled_price,
        "filled_amount": filled_amount,
        "commission": commission,
        "tax": tax,
        "ordered_at": _normalize_timestamp(order.get("orderedAt") or order.get("createdAt")),
        "filled_at": _normalize_timestamp(order.get("filledAt") or execution.get("filledAt")),
        "canceled_at": _normalize_timestamp(order.get("canceledAt")),
        "settlement_date": _normalize_date(order.get("settlementDate")),
        "source_api": "toss_orders",
        "raw_payload": order,
        "last_synced_at": datetime.now(UTC).isoformat(),
    }


def _upsert_broker_order_history(rows):
    """
    브로커 주문 원장을 upsert합니다.
    """
    if not rows:
        return

    supabase_url = os.getenv("SUPABASE_URL")
    service_role_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not supabase_url or not service_role_key:
        raise ValueError("SUPABASE_URL 또는 SUPABASE_SERVICE_ROLE_KEY 환경 변수가 없습니다.")

    response = requests.post(
        f"{supabase_url}/rest/v1/broker_order_history?on_conflict=user_id,exchange,broker_env,external_order_id",
        headers={
            "apikey": service_role_key,
            "Authorization": f"Bearer {service_role_key}",
            "Content-Type": "application/json",
            "Prefer": "resolution=merge-duplicates,return=minimal",
        },
        json=rows,
        timeout=30,
    )
    try:
        response.raise_for_status()
    except requests.HTTPError as error:
        if _is_broker_order_history_missing_error(error) or _is_broker_order_history_missing_error(response.text):
            raise RuntimeError("broker_order_history 테이블이 아직 Supabase에 적용되지 않았습니다. 마이그레이션을 먼저 반영해 주세요.") from error
        raise


def sync_toss_broker_orders(
    auth_header,
    broker_env="REAL",
    status_scope="ALL",
    from_date=None,
    to_date=None,
    symbol=None,
    limit=100,
):
    """
    토스 실제 주문내역을 조회해 broker_order_history 테이블에 적재합니다.
    """
    user_id, _ = get_user_id_from_header(auth_header)
    normalized_env = str(broker_env or "REAL").upper()
    normalized_scope = str(status_scope or "ALL").upper()
    if normalized_scope not in {"ALL", "OPEN", "CLOSED"}:
        raise ValueError("status_scope는 ALL, OPEN, CLOSED 중 하나여야 합니다.")

    records = query_supabase(
        auth_header,
        "user_api_keys",
        "GET",
        params={
            "user_id": f"eq.{user_id}",
            "exchange": "eq.TOSS",
            "broker_env": f"eq.{normalized_env}",
            "limit": "1",
        },
    )
    if not records:
        raise ValueError(f"등록된 TOSS ({normalized_env}) API 크리덴셜 정보가 없습니다.")

    record = records[0]
    crypto_helper = current_app.crypto
    client = TossClient(
        client_id=crypto_helper.decrypt(record.get("encrypted_access_key")),
        client_secret=crypto_helper.decrypt(record.get("encrypted_secret_key")),
        account_seq=record.get("toss_account_seq"),
        env=normalized_env,
        user_id=user_id,
    )
    account_ref = record.get("toss_account_seq") or record.get("toss_account_no")

    statuses = ["OPEN", "CLOSED"] if normalized_scope == "ALL" else [normalized_scope]
    effective_from = from_date
    effective_to = to_date
    if "CLOSED" in statuses and not effective_from:
        effective_from = (datetime.now(UTC) - timedelta(days=90)).date().isoformat()
    if "CLOSED" in statuses and not effective_to:
        effective_to = datetime.now(UTC).date().isoformat()

    synced_count = 0
    results = []
    for status in statuses:
        cursor = None
        fetched_count = 0
        pages = 0
        status_error = None
        while True:
            pages += 1
            try:
                payload = client.list_orders(
                    status=status,
                    from_date=effective_from if status == "CLOSED" else None,
                    to_date=effective_to if status == "CLOSED" else None,
                    cursor=cursor if status == "CLOSED" else None,
                    limit=limit if status == "CLOSED" else None,
                    symbol=symbol,
                )
            except Exception as error:
                if _is_broker_order_history_missing_error(error):
                    raise RuntimeError("broker_order_history 테이블이 아직 Supabase에 적용되지 않았습니다. 마이그레이션을 먼저 반영해 주세요.") from error
                status_error = str(error)
                break

            orders = payload.get("orders") or []
            mapped_rows = []
            for order in orders:
                row = _map_toss_order_to_history_row(user_id, normalized_env, account_ref, order)
                if row.get("external_order_id"):
                    mapped_rows.append(row)

            if mapped_rows:
                _upsert_broker_order_history(mapped_rows)
                fetched_count += len(mapped_rows)
                synced_count += len(mapped_rows)

            if status != "CLOSED" or not payload.get("has_next") or not payload.get("next_cursor"):
                break
            cursor = payload.get("next_cursor")

        results.append(
            {
                "status": status,
                "fetched_count": fetched_count,
                "pages": pages,
                "error": status_error,
            }
        )

    return {
        "exchange": "TOSS",
        "broker_env": normalized_env,
        "status_scope": normalized_scope,
        "from_date": effective_from,
        "to_date": effective_to,
        "symbol": symbol,
        "synced_count": synced_count,
        "results": results,
    }


def sync_binance_broker_trades(auth_header, exchange="BINANCE", broker_env="REAL", symbols=None, limit=1000):
    """
    Fetch Binance personal spot or futures trades and store them in broker_order_history.
    """
    user_id, _ = get_user_id_from_header(auth_header)
    normalized_env = str(broker_env or "REAL").upper()
    target_exchange = "BINANCE" if exchange in ("BINANCE", "BINANCE_UM_FUTURES") else exchange

    # Throttling 방어막: 동일 유저의 동일 환경/거래소 동기화 요청은 최소 5분 간격으로 제한
    cache_key = (user_id, exchange, normalized_env)
    now = datetime.now(UTC)
    with _binance_sync_lock:
        last_time = _last_binance_sync_time.get(cache_key)
        if last_time and (now - last_time) < timedelta(minutes=5):
            return {
                "exchange": exchange,
                "broker_env": normalized_env,
                "symbols": symbols or [],
                "synced_count": 0,
                "results": [],
                "message": "최근 5분 이내에 동기화가 수행되어 추가 조회를 스킵했습니다. (Throttled)"
            }

    records = query_supabase(
        auth_header,
        "user_api_keys",
        "GET",
        params={
            "user_id": f"eq.{user_id}",
            "exchange": f"eq.{target_exchange}",
            "broker_env": f"eq.{normalized_env}",
            "limit": "1",
        },
    )
    if not records:
        raise ValueError(f"등록된 {target_exchange} ({normalized_env}) API 키 정보가 없습니다.")

    record = records[0]
    crypto_helper = current_app.crypto
    
    if exchange == "BINANCE_UM_FUTURES":
        from backend.services.binance_client import BinanceFuturesClient
        client = BinanceFuturesClient(
            api_key=crypto_helper.decrypt(record.get("encrypted_access_key")),
            secret_key=crypto_helper.decrypt(record.get("encrypted_secret_key")),
            env=normalized_env,
        )
    else:
        client = BinanceClient(
            api_key=crypto_helper.decrypt(record.get("encrypted_access_key")),
            secret_key=crypto_helper.decrypt(record.get("encrypted_secret_key")),
            env=normalized_env,
        )

    DEFAULT_MAJOR_SYMBOLS = {"BTCUSDT", "ETHUSDT", "XRPUSDT", "SOLUSDT", "BNBUSDT", "ADAUSDT", "DOGEUSDT"}
    if symbols:
        sync_symbols = sorted({_normalize_binance_trade_symbol(symbol) for symbol in symbols if symbol})
    else:
        balance = client.get_balance()
        holding_symbols = {
            _normalize_binance_trade_symbol(holding.get("symbol"))
            for holding in balance.get("holdings", []) or []
            if holding.get("symbol")
        }
        sync_symbols = sorted({symbol for symbol in holding_symbols if symbol}.union(DEFAULT_MAJOR_SYMBOLS))

    synced_count = 0
    results = []
    for symbol in sync_symbols:
        if not symbol:
            continue
        try:
            trades = client.list_my_trades(symbol, limit=limit)
            rows = [
                _map_binance_trade_to_history_row(user_id, normalized_env, symbol, trade, exchange=exchange)
                for trade in trades
                if trade.get("id") is not None
            ]
            if rows:
                _upsert_broker_order_history(rows)
                synced_count += len(rows)
            results.append({"symbol": symbol, "fetched_count": len(rows), "error": None})
        except Exception as error:
            results.append({"symbol": symbol, "fetched_count": 0, "error": str(error)[:300]})

    result = {
        "exchange": exchange,
        "broker_env": normalized_env,
        "symbols": sync_symbols,
        "synced_count": synced_count,
        "results": results,
    }
    if any(result.get("error") is None for result in results):
        with _binance_sync_lock:
            _last_binance_sync_time[cache_key] = datetime.now(UTC)
    return result


def get_binance_cost_basis_from_history(auth_header, broker_env="REAL"):
    """
    Calculate remaining Binance spot cost basis from stored personal trades.
    """
    user_id, _ = get_user_id_from_header(auth_header)
    normalized_env = str(broker_env or "REAL").upper()
    rows = query_supabase_as_service_role(
        "broker_order_history",
        "GET",
        params={
            "user_id": f"eq.{user_id}",
            "exchange": "eq.BINANCE",
            "broker_env": f"eq.{normalized_env}",
            "status": "eq.EXECUTED",
            "order": "filled_at.asc.nullslast,ordered_at.asc.nullslast,created_at.asc",
            "limit": "5000",
        },
    ) or []

    positions = {}
    for row in rows:
        symbol = str(row.get("symbol") or "").upper()
        base_asset = str(row.get("base_asset") or "").upper()
        if not base_asset:
            base_asset, _ = _binance_symbol_assets(symbol)
        if not base_asset:
            continue

        side = str(row.get("side") or "").upper()
        qty = _to_float(row.get("filled_quantity") or row.get("quantity")) or 0.0
        amount = _to_float(row.get("filled_amount") or row.get("order_amount"))
        price = _to_float(row.get("average_filled_price") or row.get("price")) or 0.0
        if amount is None:
            amount = price * qty
        if qty <= 0 or amount < 0:
            continue

        state = positions.setdefault(base_asset, {"qty": 0.0, "cost": 0.0, "trades": 0})
        commission = _to_float(row.get("commission")) or 0.0
        commission_asset = str(row.get("commission_asset") or "").upper()
        quote_asset = str(row.get("quote_asset") or row.get("currency") or "").upper()
        quote_fee = commission if commission_asset and commission_asset == quote_asset else 0.0

        if side == "SELL":
            if state["qty"] > 0:
                sell_qty = min(qty, state["qty"])
                avg_cost = state["cost"] / state["qty"] if state["qty"] > 0 else 0.0
                state["qty"] -= sell_qty
                state["cost"] -= avg_cost * sell_qty
        else:
            state["qty"] += qty
            state["cost"] += amount + quote_fee
        state["trades"] += 1

    result = {}
    for asset, state in positions.items():
        qty = state["qty"]
        cost = state["cost"]
        if qty <= 0.000001 or cost <= 0:
            continue
        result[asset] = {
            "qty": qty,
            "cost_amount": cost,
            "avg_price": cost / qty,
            "currency": "USDT",
            "source": "BINANCE_SYNCED",
            "trade_count": state["trades"],
        }
    return result


def list_broker_order_history(auth_header, limit=300, exchange=None, broker_env=None):
    """
    사용자의 브로커 주문 원장을 조회합니다.
    """
    user_id, _ = get_user_id_from_header(auth_header)
    params = {
        "user_id": f"eq.{user_id}",
        "order": "ordered_at.desc.nullslast,created_at.desc",
        "limit": str(max(1, min(int(limit), 1000))),
    }
    if exchange:
        params["exchange"] = f"eq.{str(exchange).upper()}"
    if broker_env:
        params["broker_env"] = f"eq.{str(broker_env).upper()}"
    try:
        return query_supabase_as_service_role("broker_order_history", "GET", params=params) or []
    except Exception as error:
        if _is_broker_order_history_missing_error(error):
            return []
        raise
