import os
import pytest
from backend.services.credentials_gateway import CredentialsGateway

def test_credentials_gateway_shared_system_key_mapping(monkeypatch):
    monkeypatch.setenv("TOSS_API_KEY", "system-toss-key-value")
    
    gateway = CredentialsGateway()
    gateway._key_cache.clear()
    
    query_count = 0
    def mock_query_supabase(auth_header, endpoint, method, params=None):
        nonlocal query_count
        query_count += 1
        return [{
            "encrypted_access_key": "system-toss-key-value",
            "encrypted_secret_key": "sec",
            "toss_account_seq": "123"
        }]
    
    monkeypatch.setattr("backend.services.credentials_gateway.query_supabase", mock_query_supabase)
    monkeypatch.setattr("backend.utils.crypto_helper.CryptoHelper.decrypt", lambda self, x: x)

    # 1. user-1 로 최초 조회 시도 (DB 조회 1회 발생)
    creds = gateway.get_credentials("Bearer test", "user-1", "TOSS", "REAL")
    assert creds["access_key"] == "system-toss-key-value"
    assert query_count == 1

    # 2. 동일 키 매핑이 정상 작동한다면 ("system_toss", "TOSS", "REAL") 키가 생성되어 있어야 함
    assert ("system_toss", "TOSS", "REAL") in gateway._key_cache

    # 3. user-2 로 최초 조회 시도 (DB를 읽어야 비로소 시스템 키와 동일함을 알 수 있으므로 DB 조회 1회 추가되어 누적 2회)
    creds2 = gateway.get_credentials("Bearer test", "user-2", "TOSS", "REAL")
    assert creds2["access_key"] == "system-toss-key-value"
    assert query_count == 2

    # 4. user-2 로 연속 조회 시도 (이미 system_toss 에 매핑되었으므로 DB 조회 미발생, 누적 2회 유지)
    creds2_retry = gateway.get_credentials("Bearer test", "user-2", "TOSS", "REAL")
    assert creds2_retry["access_key"] == "system-toss-key-value"
    assert query_count == 2
