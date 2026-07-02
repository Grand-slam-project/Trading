ALTER TABLE public.broker_order_history
    ADD COLUMN IF NOT EXISTS external_trade_id TEXT,
    ADD COLUMN IF NOT EXISTS base_asset TEXT,
    ADD COLUMN IF NOT EXISTS quote_asset TEXT,
    ADD COLUMN IF NOT EXISTS commission_asset TEXT;

ALTER TABLE public.trade_proposals DROP CONSTRAINT IF EXISTS trade_proposals_exchange_check;
ALTER TABLE public.trade_proposals
    ADD CONSTRAINT trade_proposals_exchange_check
    CHECK (exchange IN ('COINONE', 'BINANCE', 'BINANCE_UM_FUTURES', 'KIS', 'TOSS'));

ALTER TABLE public.broker_order_history DROP CONSTRAINT IF EXISTS broker_order_history_exchange_check;
ALTER TABLE public.broker_order_history
    ADD CONSTRAINT broker_order_history_exchange_check
    CHECK (exchange IN ('TOSS', 'KIS', 'COINONE', 'BINANCE', 'BINANCE_UM_FUTURES'));

ALTER TABLE public.broker_order_history DROP CONSTRAINT IF EXISTS broker_order_history_currency_check;
ALTER TABLE public.broker_order_history
    ADD CONSTRAINT broker_order_history_currency_check
    CHECK (currency IN ('KRW', 'USD', 'USDT'));

CREATE INDEX IF NOT EXISTS broker_order_history_user_exchange_symbol_idx
    ON public.broker_order_history (user_id, exchange, broker_env, symbol);

CREATE INDEX IF NOT EXISTS broker_order_history_binance_trade_idx
    ON public.broker_order_history (user_id, exchange, broker_env, external_trade_id)
    WHERE exchange IN ('BINANCE', 'BINANCE_UM_FUTURES') AND external_trade_id IS NOT NULL;
