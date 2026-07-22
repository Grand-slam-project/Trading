"""AI 위탁운용 주문 체결을 포지션 원장으로 반영합니다."""

from __future__ import annotations

from typing import Any

from backend.services.ai_fund_exchange import ExchangeOrder
from backend.services.supabase_client import safe_query_supabase_as_service_role


OPEN_SELL_STATUSES = "PENDING_SUBMIT,SUBMITTED,PARTIALLY_FILLED,CANCEL_REQUESTED"


class AiFundLedger:
    """AI 위탁 귀속 포지션만 관리하는 원장 서비스입니다."""

    def __init__(self, user_id: str, exchange_type: str):
        self.user_id = user_id
        self.exchange_type = exchange_type.lower()

    def get_sellable_quantity(self, symbol: str) -> float:
        position = self._get_position(symbol)
        quantity = _to_float((position or {}).get("quantity"))
        reservations = self._query(
            "ai_fund_orders",
            params={
                "user_id": f"eq.{self.user_id}",
                "exchange_type": f"eq.{self.exchange_type}",
                "symbol": f"eq.{symbol.upper()}",
                "side": "eq.SELL",
                "status": f"in.({OPEN_SELL_STATUSES})",
                "select": "requested_qty",
            },
        )
        reserved = sum(_to_float(row.get("requested_qty")) for row in reservations)
        return max(quantity - reserved, 0.0)

    def apply_new_fill(self, order: ExchangeOrder, order_id: str | None = None) -> float:
        """누적 체결 수량에서 아직 반영하지 않은 체결분만 포지션에 적용합니다."""
        if order.filled_qty <= 0 or order.average_fill_price is None:
            return 0.0

        recorded = self._recorded_fill_quantity(order_id)
        new_quantity = max(order.filled_qty - recorded, 0.0)
        if new_quantity <= 0:
            return 0.0

        fill_rows = self._query(
            "ai_fund_fills",
            method="POST",
            json_data={
                "order_id": order_id,
                "exchange_type": self.exchange_type,
                "exchange_fill_id": self._synthetic_fill_id(order, recorded, new_quantity),
                "symbol": order.symbol,
                "side": order.side,
                "quantity": new_quantity,
                "price": order.average_fill_price,
                "fee_amount": order.fee,
            },
        )
        if not fill_rows:
            return 0.0
        self._apply_position(order, new_quantity)
        return new_quantity

    def _apply_position(self, order: ExchangeOrder, new_quantity: float) -> None:
        position = self._get_position(order.symbol)
        current_qty = _to_float((position or {}).get("quantity"))
        current_average = _to_float((position or {}).get("average_entry_price"))
        realized_pnl = _to_float((position or {}).get("realized_pnl"))

        if order.side == "BUY":
            total_cost = (current_qty * current_average) + (new_quantity * order.average_fill_price)
            next_qty = current_qty + new_quantity
            next_average = total_cost / next_qty if next_qty > 0 else 0.0
        else:
            sell_quantity = min(new_quantity, current_qty)
            next_qty = max(current_qty - sell_quantity, 0.0)
            next_average = current_average if next_qty > 0 else 0.0
            realized_pnl += ((order.average_fill_price - current_average) * sell_quantity) - order.fee

        payload = {
            "user_id": self.user_id,
            "exchange_type": self.exchange_type,
            "symbol": order.symbol,
            "quantity": next_qty,
            "average_entry_price": next_average,
            "realized_pnl": realized_pnl,
        }
        if position and position.get("id"):
            self._query(
                f"ai_fund_positions?id=eq.{position['id']}",
                method="PATCH",
                json_data=payload,
            )
        else:
            self._query("ai_fund_positions", method="POST", json_data=payload)

    def _get_position(self, symbol: str) -> dict[str, Any] | None:
        rows = self._query(
            "ai_fund_positions",
            params={
                "user_id": f"eq.{self.user_id}",
                "exchange_type": f"eq.{self.exchange_type}",
                "symbol": f"eq.{symbol.upper()}",
                "limit": "1",
            },
        )
        return rows[0] if rows else None

    def _recorded_fill_quantity(self, order_id: str | None) -> float:
        if not order_id:
            return 0.0
        rows = self._query(
            "ai_fund_fills",
            params={"order_id": f"eq.{order_id}", "select": "quantity"},
        )
        return sum(_to_float(row.get("quantity")) for row in rows)

    def _query(self, endpoint: str, method: str = "GET", **kwargs: Any) -> list[dict[str, Any]]:
        result = safe_query_supabase_as_service_role(endpoint, method=method, **kwargs) or []
        return result if isinstance(result, list) else []

    @staticmethod
    def _synthetic_fill_id(order: ExchangeOrder, recorded: float, quantity: float) -> str:
        identity = order.exchange_order_id or order.client_order_id
        return f"{identity}:{recorded + quantity:.12f}"


def _to_float(value: Any) -> float:
    try:
        return float(value or 0.0)
    except (TypeError, ValueError):
        return 0.0
