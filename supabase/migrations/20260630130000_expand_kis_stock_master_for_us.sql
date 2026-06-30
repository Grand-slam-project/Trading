-- 1. market_country 제약조건 변경 (KR만 허용하던 것에서 US 추가 허용)
ALTER TABLE public.kis_stock_master DROP CONSTRAINT IF EXISTS kis_stock_master_market_country_check;
ALTER TABLE public.kis_stock_master ADD CONSTRAINT kis_stock_master_market_country_check 
    CHECK (market_country IN ('KR', 'US'));

-- 2. market_segment 제약조건 변경 (미국 주식 시장 추가)
ALTER TABLE public.kis_stock_master DROP CONSTRAINT IF EXISTS kis_stock_master_market_segment_check;
ALTER TABLE public.kis_stock_master ADD CONSTRAINT kis_stock_master_market_segment_check 
    CHECK (market_segment IN ('KOSPI', 'KOSDAQ', 'KONEX', 'ETF', 'ETN', 'NASDAQ', 'NYSE', 'AMEX', 'OTHER'));

-- 3. 정제 표시명 및 테마 섹터 컬럼 추가
ALTER TABLE public.kis_stock_master ADD COLUMN IF NOT EXISTS display_name TEXT;
ALTER TABLE public.kis_stock_master ADD COLUMN IF NOT EXISTS sector TEXT;

-- 4. 효율적인 필터링 조회를 위한 인덱스 신설
CREATE INDEX IF NOT EXISTS idx_kis_stock_master_country_symbol 
    ON public.kis_stock_master (market_country, symbol);
