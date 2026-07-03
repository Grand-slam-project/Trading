-- user_api_keys 테이블에 api_permissions JSONB 컬럼 추가
ALTER TABLE user_api_keys ADD COLUMN IF NOT EXISTS api_permissions JSONB DEFAULT '{}'::jsonb;
