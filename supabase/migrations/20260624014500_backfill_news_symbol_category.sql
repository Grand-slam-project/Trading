UPDATE public.news_articles
SET raw_payload = COALESCE(raw_payload, '{}'::jsonb)
    || jsonb_build_object(
        'query_category', 'symbol',
        'query_key', concat(lower(source), ':symbol:', symbol),
        'query_text', symbol,
        'collection_reason', 'symbol_backfill'
    )
WHERE COALESCE(symbol, '') <> ''
  AND COALESCE(raw_payload->>'query_category', '') = '';
