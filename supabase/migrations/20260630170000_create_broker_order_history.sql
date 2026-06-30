-- 브로커 실제 주문 원장 테이블
CREATE TABLE IF NOT EXISTS public.broker_order_history (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE NOT NULL,
    exchange TEXT NOT NULL CHECK (exchange IN ('TOSS', 'KIS', 'COINONE', 'BINANCE')),
    broker_env TEXT NOT NULL DEFAULT 'REAL' CHECK (broker_env IN ('MOCK', 'REAL')),
    account_ref TEXT,
    external_order_id TEXT NOT NULL,
    client_order_id TEXT,
    symbol TEXT,
    market_country TEXT CHECK (market_country IN ('KR', 'US')),
    side TEXT CHECK (side IN ('BUY', 'SELL')),
    order_type TEXT,
    time_in_force TEXT,
    status TEXT NOT NULL,
    raw_status TEXT,
    currency TEXT CHECK (currency IN ('KRW', 'USD')),
    price NUMERIC,
    quantity NUMERIC,
    order_amount NUMERIC,
    filled_quantity NUMERIC,
    average_filled_price NUMERIC,
    filled_amount NUMERIC,
    commission NUMERIC,
    tax NUMERIC,
    ordered_at TIMESTAMP WITH TIME ZONE,
    filled_at TIMESTAMP WITH TIME ZONE,
    canceled_at TIMESTAMP WITH TIME ZONE,
    settlement_date DATE,
    source_api TEXT,
    raw_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    last_synced_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS broker_order_history_user_exchange_env_order_idx
    ON public.broker_order_history (user_id, exchange, broker_env, external_order_id);

CREATE INDEX IF NOT EXISTS broker_order_history_user_ordered_at_idx
    ON public.broker_order_history (user_id, ordered_at DESC);

ALTER TABLE public.broker_order_history ENABLE ROW LEVEL SECURITY;

GRANT USAGE ON SCHEMA public TO authenticated;
GRANT USAGE ON SCHEMA public TO service_role;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.broker_order_history TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.broker_order_history TO service_role;

DROP POLICY IF EXISTS "사용자는 자신의 브로커 주문 원장만 조회 및 관리 가능" ON public.broker_order_history;
CREATE POLICY "사용자는 자신의 브로커 주문 원장만 조회 및 관리 가능" ON public.broker_order_history
    FOR ALL USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

ALTER publication supabase_realtime ADD TABLE public.broker_order_history;
