from unittest.mock import MagicMock

import backend.services.admin_ai_fund_trading_scheduler as scheduler


def test_build_coinone_client_uses_user_api_key_credentials(monkeypatch):
    captured = {}

    class FakeCryptoHelper:
        def decrypt(self, value):
            return f"plain-{value}"

    class FakeCoinoneClient:
        def __init__(self, access_token, secret_key):
            captured["access_token"] = access_token
            captured["secret_key"] = secret_key

    monkeypatch.setattr(scheduler, "CryptoHelper", lambda *_args, **_kwargs: FakeCryptoHelper())
    monkeypatch.setattr(
        scheduler,
        "safe_query_supabase_as_service_role",
        lambda *_args, **_kwargs: [{
            "encrypted_access_key": "access",
            "encrypted_secret_key": "secret",
        }],
    )
    monkeypatch.setattr("backend.services.coinone_client.CoinoneClient", FakeCoinoneClient)

    client = scheduler._build_exchange_client("coinone", {"user_id": "admin-123"})

    assert isinstance(client, FakeCoinoneClient)
    assert captured == {
        "access_token": "plain-access",
        "secret_key": "plain-secret",
    }


def test_build_binance_client_uses_user_api_key_credentials(monkeypatch):
    captured = {}

    class FakeCryptoHelper:
        def decrypt(self, value):
            return f"plain-{value}"

    class FakeBinanceClient:
        def __init__(self, api_key, secret_key, env):
            captured.update(api_key=api_key, secret_key=secret_key, env=env)

    monkeypatch.setattr(scheduler, "CryptoHelper", lambda *_args, **_kwargs: FakeCryptoHelper())
    monkeypatch.setattr(
        scheduler,
        "safe_query_supabase_as_service_role",
        lambda *_args, **_kwargs: [{"encrypted_access_key": "access", "encrypted_secret_key": "secret"}],
    )
    monkeypatch.setattr("backend.services.binance_client.BinanceClient", FakeBinanceClient)

    client = scheduler._build_exchange_client("binance", {"user_id": "admin-123", "broker_env": "MOCK"})

    assert isinstance(client, FakeBinanceClient)
    assert captured == {"api_key": "plain-access", "secret_key": "plain-secret", "env": "MOCK"}


def test_build_toss_client_uses_user_credentials_and_account_sequence(monkeypatch):
    captured = {}

    class FakeCryptoHelper:
        def decrypt(self, value):
            return f"plain-{value}"

    class FakeTossClient:
        def __init__(self, client_id, client_secret, account_seq, env, user_id):
            captured.update(
                client_id=client_id,
                client_secret=client_secret,
                account_seq=account_seq,
                env=env,
                user_id=user_id,
            )

    monkeypatch.setattr(scheduler, "CryptoHelper", lambda *_args, **_kwargs: FakeCryptoHelper())
    monkeypatch.setattr(
        scheduler,
        "safe_query_supabase_as_service_role",
        lambda *_args, **_kwargs: [{
            "encrypted_access_key": "access",
            "encrypted_secret_key": "secret",
            "toss_account_seq": "account-1",
        }],
    )
    monkeypatch.setattr("backend.services.toss_client.TossClient", FakeTossClient)

    client = scheduler._build_exchange_client("toss", {"user_id": "admin-123", "broker_env": "MOCK"})

    assert isinstance(client, FakeTossClient)
    assert captured == {
        "client_id": "plain-access",
        "client_secret": "plain-secret",
        "account_seq": "account-1",
        "env": "MOCK",
        "user_id": "admin-123",
    }


def test_run_ai_fund_cycle_reuses_signal_reads_per_threshold(monkeypatch):
    signal_reads = []
    executions = []

    class FakeTrader:
        def __init__(self, user_id, exchange_type):
            self.user_id = user_id
            self.exchange_type = exchange_type

        def evaluate_exit_signal(self, *_args, **_kwargs):
            return None

        def evaluate_and_execute_signal(self, **kwargs):
            executions.append((self.user_id, self.exchange_type, kwargs["symbol"]))
            return {"order_id": f"ord-{self.user_id}"}

    monkeypatch.setattr(
        scheduler,
        "_load_active_configs",
        lambda: [
            {"user_id": "admin-1", "exchange_type": "coinone", "min_signal_confidence": 0.75, "max_position_size": 100000},
            {"user_id": "admin-2", "exchange_type": "coinone", "min_signal_confidence": 0.75, "max_position_size": 100000},
        ],
    )
    monkeypatch.setattr(
        scheduler,
        "_read_crypto_signals",
        lambda min_confidence: signal_reads.append(min_confidence) or [{"symbol": "BTC", "confidence_score": 0.90}],
    )
    monkeypatch.setattr(scheduler, "_build_exchange_client", lambda *_args, **_kwargs: MagicMock())
    monkeypatch.setattr(scheduler, "_get_current_price_coinone", lambda _symbol: 50000000.0)
    monkeypatch.setattr("backend.services.admin_ai_managed_trader.AdminAiManagedTrader", FakeTrader)

    scheduler._run_ai_fund_cycle()

    assert signal_reads == [0.75]
    assert executions == [
        ("admin-1", "coinone", "BTC"),
        ("admin-2", "coinone", "BTC"),
    ]


def test_run_ai_fund_cycle_does_not_dry_run_when_supported_exchange_has_no_credentials(monkeypatch):
    writes = []

    monkeypatch.setattr(
        scheduler,
        "_load_active_configs",
        lambda: [
            {"user_id": "admin-1", "exchange_type": "coinone", "min_signal_confidence": 0.75, "max_position_size": 100000},
        ],
    )
    monkeypatch.setattr(
        scheduler,
        "_read_crypto_signals",
        lambda _min_confidence: [{"symbol": "BTC", "confidence_score": 0.90}],
    )
    monkeypatch.setattr(scheduler, "_build_exchange_client", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        "backend.services.supabase_client.safe_query_supabase_as_service_role",
        lambda *args, **kwargs: writes.append((args, kwargs)),
    )

    scheduler._run_ai_fund_cycle()

    assert writes == []


def test_run_ai_fund_cycle_checks_exit_positions_before_buy_signals(monkeypatch):
    executions = []

    class FakeTrader:
        def __init__(self, user_id, exchange_type):
            self.user_id = user_id
            self.exchange_type = exchange_type

        def list_open_positions(self):
            return [{"symbol": "ETH"}]

        def evaluate_exit_signal(self, symbol, current_price):
            if symbol == "ETH" and current_price == 3200000.0:
                return {"symbol": "ETH", "signal_type": "SELL", "reason": "TAKE_PROFIT", "quantity": 0.5}
            return None

        def evaluate_and_execute_signal(self, **kwargs):
            executions.append((kwargs["signal_type"], kwargs["symbol"]))
            return {"order_id": "sell-eth"}

    monkeypatch.setattr(
        scheduler,
        "_load_active_configs",
        lambda: [
            {"user_id": "admin-1", "exchange_type": "coinone", "min_signal_confidence": 0.75, "max_position_size": 100000},
        ],
    )
    monkeypatch.setattr(
        scheduler,
        "_read_crypto_signals",
        lambda _min_confidence: [{"symbol": "BTC", "confidence_score": 0.90}],
    )
    monkeypatch.setattr(scheduler, "_build_exchange_client", lambda *_args, **_kwargs: MagicMock())
    monkeypatch.setattr(
        scheduler,
        "_get_current_price_coinone",
        lambda symbol: 3200000.0 if symbol == "ETH" else 50000000.0,
    )
    monkeypatch.setattr("backend.services.admin_ai_managed_trader.AdminAiManagedTrader", FakeTrader)

    scheduler._run_ai_fund_cycle()

    assert executions[0] == ("SELL", "ETH")


def test_run_ai_fund_cycle_reconciles_orders_before_reading_buy_signals(monkeypatch):
    events = []

    class FakeTrader:
        def __init__(self, *_args, **_kwargs):
            pass

        def list_open_positions(self):
            return []

        def evaluate_and_execute_signal(self, **_kwargs):
            events.append("buy")
            return None

    class FakeReconciliationService:
        def __init__(self, _ledger):
            pass

        def reconcile_config(self, _config, _client):
            events.append("reconcile")

    monkeypatch.setattr(
        scheduler,
        "_load_active_configs",
        lambda: [{"user_id": "admin-1", "exchange_type": "coinone", "min_signal_confidence": 0.75, "max_position_size": 100000}],
    )
    monkeypatch.setattr(scheduler, "_read_crypto_signals", lambda _score: [{"symbol": "BTC", "confidence_score": 0.9}])
    monkeypatch.setattr(scheduler, "_build_exchange_client", lambda *_args: MagicMock())
    monkeypatch.setattr(scheduler, "_get_current_price_coinone", lambda _symbol: 50000000.0)
    monkeypatch.setattr("backend.services.admin_ai_managed_trader.AdminAiManagedTrader", FakeTrader)
    monkeypatch.setattr("backend.services.ai_fund_reconciliation.AiFundReconciliationService", FakeReconciliationService)
    monkeypatch.setattr("backend.services.ai_fund_ledger.AiFundLedger", MagicMock())

    scheduler._run_ai_fund_cycle()

    assert events[:2] == ["reconcile", "buy"]
