"""
AI 위탁 자동매매 스케줄러 (admin_ai_fund_trading_scheduler.py)

- DB의 admin_ai_fund_configs (is_active=true) 설정을 읽어 활성 거래소별로 루프 실행
- ML predictions CSV (crypto_predictions_lgbm_v10.csv) 에서 신호를 읽어 임계값 이상이면 실행
- AdminAiManagedTrader.evaluate_and_execute_signal() 을 통해 주문 + 로그 처리
- 각 거래소별 1건씩 분산 락(lock) 확보 후 실행 → 중복 주문 방지
"""
import logging
import os
import threading
import time
from pathlib import Path

from backend.services.supabase_client import safe_query_supabase_as_service_role
from backend.utils.crypto_helper import CryptoHelper

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[2]

# crypto v10 예측 CSV 경로 (ml/configs/lgbm_crypto_v10.yaml 기준)
CRYPTO_PREDICTIONS_PATH = PROJECT_ROOT / "ml" / "data" / "processed" / "crypto_predictions_lgbm_v10.csv"

_ai_fund_started = False


def _load_active_configs() -> list[dict]:
    """admin_ai_fund_configs 에서 is_active=true 설정 목록을 조회합니다."""
    try:
        configs = safe_query_supabase_as_service_role(
            "admin_ai_fund_configs",
            params={"is_active": "eq.true"},
        ) or []
        return configs
    except Exception as e:
        logger.warning(f"[AiFundScheduler] 설정 조회 실패: {e}")
        return []


def _read_crypto_signals(min_confidence_score: float) -> list[dict]:
    """
    crypto_predictions_lgbm_v10.csv 에서 LONG 신호 중
    signal_score >= min_confidence_score * 100 인 종목을 반환합니다.
    """
    try:
        if not CRYPTO_PREDICTIONS_PATH.exists():
            logger.warning(f"[AiFundScheduler] 예측 파일 없음: {CRYPTO_PREDICTIONS_PATH}")
            return []

        import pandas as pd
        df = pd.read_csv(CRYPTO_PREDICTIONS_PATH, dtype={"symbol": "string"})

        threshold_score = min_confidence_score * 100.0
        mask = (
            (df["position"].str.upper() == "LONG") &
            (df["signal_score"] >= threshold_score)
        )
        candidates = df[mask].sort_values("signal_score", ascending=False)

        signals = []
        for _, row in candidates.iterrows():
            signals.append({
                "symbol": str(row["symbol"]),
                "confidence_score": float(row["signal_score"]) / 100.0,
                "exchange": str(row.get("exchange", "")).upper(),
                "signal_id": str(
                    row.get("signal_id")
                    or row.get("generated_at")
                    or row.get("timestamp")
                    or row.get("created_at")
                    or f"{row['symbol']}:{row['signal_score']}"
                ),
            })
        return signals

    except Exception as e:
        logger.warning(f"[AiFundScheduler] 예측 파일 읽기 실패: {e}")
        return []


def _get_current_price_coinone(symbol: str) -> float | None:
    """코인원 현재가를 조회합니다. 실패 시 None 반환."""
    try:
        from backend.services.coinone_client import CoinoneClient
        client = CoinoneClient.__new__(CoinoneClient)  # 인증 없이 퍼블릭 API만 사용
        client.access_token = ""
        client.secret_key = b""
        client.base_url = "https://api.coinone.co.kr"
        price_data = client.get_price(symbol)
        price = price_data.get("current_price") or price_data.get("last") or price_data.get("close")
        if price:
            return float(price)
    except Exception as e:
        logger.warning(f"[AiFundScheduler] 코인원 현재가 조회 실패 ({symbol}): {e}")
    return None


def _build_exchange_client(exchange_type: str, config: dict):
    """사용자별 암호화 API 키로 거래소 클라이언트를 생성합니다."""
    exchange = exchange_type.lower()
    user_id = str(config.get("user_id") or "")
    broker_env = str(config.get("broker_env") or "REAL").upper()
    if exchange == "coinone":
        from backend.services.coinone_client import CoinoneClient

        credentials = _load_user_exchange_credentials(
            user_id=user_id,
            exchange="COINONE",
            broker_env=broker_env,
        )
        if not credentials:
            logger.warning(
                f"[AiFundScheduler] 코인원 사용자 API 키 없음 "
                f"(user={str(config.get('user_id') or '')[:8]})"
            )
            return None
        access_token = credentials["access_key"]
        secret_key = credentials["secret_key"]
        return CoinoneClient(access_token=access_token, secret_key=secret_key)
    if exchange == "binance":
        from backend.services.binance_client import BinanceClient

        credentials = _load_user_exchange_credentials(user_id, "BINANCE", broker_env)
        if not credentials:
            logger.warning("[AiFundScheduler] 바이낸스 사용자 API 키 없음 (user=%s)", user_id[:8])
            return None
        return BinanceClient(
            api_key=credentials["access_key"],
            secret_key=credentials["secret_key"],
            env=broker_env,
        )
    if exchange == "toss":
        from backend.services.toss_client import TossClient

        credentials = _load_user_exchange_credentials(user_id, "TOSS", broker_env)
        if not credentials or not credentials.get("toss_account_seq"):
            logger.warning("[AiFundScheduler] 토스 사용자 API 키 또는 계좌 식별자 없음 (user=%s)", user_id[:8])
            return None
        return TossClient(
            client_id=credentials["access_key"],
            client_secret=credentials["secret_key"],
            account_seq=credentials["toss_account_seq"],
            env=broker_env,
            user_id=user_id,
        )
    return None


def _load_user_exchange_credentials(user_id: str, exchange: str, broker_env: str = "REAL") -> dict | None:
    if not user_id:
        return None

    rows = safe_query_supabase_as_service_role(
        "user_api_keys",
        params={
            "user_id": f"eq.{user_id}",
            "exchange": f"eq.{exchange}",
            "broker_env": f"eq.{broker_env}",
            "limit": "1",
        },
    ) or []
    if not rows:
        return None

    row = rows[0]
    crypto = CryptoHelper(os.getenv("ENCRYPTION_KEY", "temporary-key-for-test"))
    return {
        "access_key": crypto.decrypt(row.get("encrypted_access_key")),
        "secret_key": crypto.decrypt(row.get("encrypted_secret_key")),
        "toss_account_seq": row.get("toss_account_seq"),
    }


def _run_ai_fund_cycle() -> None:
    """
    1. 활성 AI 펀드 설정 목록 조회
    2. 거래소별로 ML 신호 읽기
    3. 임계값 초과 신호에 대해 evaluate_and_execute_signal() 실행
    """
    configs = _load_active_configs()
    if not configs:
        return

    from backend.services.admin_ai_managed_trader import AdminAiManagedTrader
    from backend.services.ai_fund_ledger import AiFundLedger
    from backend.services.ai_fund_reconciliation import AiFundReconciliationService

    # 거래소별로 configs 그룹화 (여러 user_id가 같은 거래소를 쓸 수 있음)
    signal_cache: dict[float, list[dict]] = {}
    for cfg in configs:
        user_id = cfg.get("user_id", "")
        exchange_type = str(cfg.get("exchange_type", "coinone")).lower()
        min_confidence = float(cfg.get("min_signal_confidence", 0.75))
        max_position_size = float(cfg.get("max_position_size", 0.0))

        if not user_id:
            continue

        # 현재 코인 ML 신호만 지원 (코인원/바이낸스 공통 coinone 예측 CSV 사용)
        if exchange_type not in {"coinone", "binance", "toss"}:
            continue

        trader = AdminAiManagedTrader(user_id=user_id, exchange_type=exchange_type)
        client = _build_exchange_client(exchange_type, cfg)

        if client is None:
            logger.warning(
                f"[AiFundScheduler] {exchange_type} 주문 클라이언트 없음 — "
                f"실제 주문과 체결 로그 생성을 건너뜁니다."
            )
            continue

        try:
            reconciliation = AiFundReconciliationService(
                AiFundLedger(user_id=user_id, exchange_type=exchange_type)
            ).reconcile_config(cfg, client)
            needs_review_count = int(getattr(reconciliation, "needs_review_count", 0) or 0)
            if needs_review_count:
                logger.warning(
                    "[AiFundScheduler] 대사 검토 대기 주문 %d건 발생 (user=%s, exchange=%s)",
                    needs_review_count,
                    user_id[:8],
                    exchange_type,
                )
        except Exception as reconciliation_error:
            logger.exception(
                "[AiFundScheduler] 주문 대사 실패로 신규 진입을 건너뜁니다 (user=%s, exchange=%s): %s",
                user_id[:8],
                exchange_type,
                reconciliation_error,
            )
            continue

        try:
            exit_executed = False
            list_positions = getattr(trader, "list_open_positions", lambda: [])
            for position in list_positions():
                held_symbol = str(position.get("symbol") or "")
                current_price = _get_current_price_coinone(held_symbol) if exchange_type == "coinone" else None
                if not current_price or current_price <= 0:
                    continue
                exit_signal = trader.evaluate_exit_signal(held_symbol, current_price=current_price)
                if not exit_signal:
                    continue
                result = trader.evaluate_and_execute_signal(
                    symbol=held_symbol,
                    signal_type="SELL",
                    confidence_score=1.0,
                    current_price=current_price,
                    exchange_client=client,
                )
                if result:
                    exit_executed = True
                    logger.info(
                        f"[AiFundScheduler] SELL 조건 실행 — {held_symbol} "
                        f"@ {current_price:,.0f} ({exit_signal.get('reason')})"
                    )
            if exit_executed:
                continue
        except Exception as exit_err:
            logger.exception(f"[AiFundScheduler] 보유 포지션 청산 검사 오류: {exit_err}")

        if max_position_size <= 0:
            continue

        if min_confidence not in signal_cache:
            signal_cache[min_confidence] = _read_crypto_signals(min_confidence)
        signals = signal_cache[min_confidence]
        if not signals:
            logger.info(
                f"[AiFundScheduler] 확신도 {min_confidence * 100:.0f}% 초과 신호 없음 "
                f"(user={user_id[:8]}, exchange={exchange_type})"
            )
            continue

        top_signal = signals[0]
        symbol = top_signal["symbol"]
        confidence = top_signal["confidence_score"]

        current_price = _get_current_price_coinone(symbol) if exchange_type == "coinone" else None
        if not current_price or current_price <= 0:
            logger.warning(f"[AiFundScheduler] 현재가 조회 실패 ({symbol}) — 매수 건너뜀")
            continue

        try:
            result = trader.evaluate_and_execute_signal(
                symbol=symbol,
                signal_type="BUY",
                confidence_score=confidence,
                current_price=current_price,
                exchange_client=client,
                signal_id=top_signal.get("signal_id"),
            )
            if result:
                logger.info(
                    f"[AiFundScheduler] BUY 체결 완료 — {symbol} "
                    f"@ {current_price:,.0f} (확신도 {confidence * 100:.1f}%)"
                )
            else:
                logger.info(f"[AiFundScheduler] BUY 조건 미충족 또는 락 점유 — {symbol}")
        except Exception as exec_err:
            logger.exception(f"[AiFundScheduler] 주문 실행 오류 ({symbol}): {exec_err}")


def start_ai_fund_trading_scheduler(
    enabled: bool = True,
    interval_seconds: int = 30,
) -> None:
    """
    AI 위탁 자동매매 스케줄러를 백그라운드 스레드로 구동합니다.

    Args:
        enabled: 환경변수 AI_FUND_TRADING_ENABLED 기반 활성화 여부
        interval_seconds: 실행 주기 (기본 30초)
    """
    global _ai_fund_started
    if _ai_fund_started or not enabled:
        if not enabled:
            logger.info("[AiFundScheduler] AI 위탁 자동매매 스케줄러 비활성화됨 (enabled=false)")
        return

    _ai_fund_started = True
    logger.info(
        f"[AiFundScheduler] AI 위탁 자동매매 스케줄러 시작 "
        f"(주기: {interval_seconds}초, 예측파일: {CRYPTO_PREDICTIONS_PATH.name})"
    )

    def _loop() -> None:
        # 첫 실행 지연 (다른 스케줄러 기동 완료 대기)
        time.sleep(15)
        while True:
            try:
                _run_ai_fund_cycle()
            except Exception as loop_err:
                logger.exception(f"[AiFundScheduler] 루프 오류: {loop_err}")
            time.sleep(interval_seconds)

    thread = threading.Thread(target=_loop, daemon=True, name="ai-fund-trading-scheduler")
    thread.start()
