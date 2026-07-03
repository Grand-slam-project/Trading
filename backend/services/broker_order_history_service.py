import os
from datetime import datetime, timedelta, timezone

import requests
from flask import current_app

from backend.services.auth_service import get_user_id_from_header
from backend.services.supabase_client import query_supabase, query_supabase_as_service_role
from backend.services.toss_client import TossClient


UTC = timezone.utc


def _is_broker_order_history_missing_error(error) -> bool:
    """
    broker_order_history 테이블이 아직 배포되지 않은 경우를 식별합니다.
    """
    message = str(error or "").lower()
    return "broker_order_history" in message and ("404" in message or "not found" in message or "could not find" in message)


def _is_broker_order_history_schema_error(error) -> bool:
    """
    원격 DB 스키마가 최신 마이그레이션과 다를 때 조회 폴백이 필요한지 판단합니다.
    """
    message = str(error or "").lower()
    return "broker_order_history" in message and (
        "400" in message
        or "pgrst204" in message
        or "schema cache" in message
        or "could not find" in message
        or "ordered_at" in message
    )


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
        if _is_broker_order_history_schema_error(error):
            fallback_params = dict(params)
            fallback_params["order"] = "created_at.desc"
            return query_supabase_as_service_role("broker_order_history", "GET", params=fallback_params) or []
        raise
