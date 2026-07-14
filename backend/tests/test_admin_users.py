from datetime import datetime, timedelta, timezone

import pytest
from flask import Flask

from backend.routes import admin_users


@pytest.fixture
def client():
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(admin_users.admin_users_bp)
    return app.test_client()


def test_list_admin_users_requires_admin(monkeypatch, client):
    monkeypatch.setattr(
        admin_users,
        "_verify_admin",
        lambda auth_header: (_ for _ in ()).throw(PermissionError("관리자 권한이 필요합니다.")),
    )

    response = client.get("/api/admin/users", headers={"Authorization": "Bearer user"})

    assert response.status_code == 403
    payload = response.get_json()
    assert payload["success"] is False
    assert "error" in payload


def test_list_admin_users_returns_usage_summary(monkeypatch, client):
    now = datetime.now(timezone.utc)

    monkeypatch.setattr(admin_users, "_verify_admin", lambda auth_header: {"id": "admin-1"})
    monkeypatch.setattr(admin_users, "_utc_now", lambda: now)

    def fake_request(endpoint, method="GET", params=None, json_data=None, extra_headers=None):
        if endpoint == "profiles":
            return [
                {"id": "user-1", "email": "a@example.com", "nickname": "alpha", "role": "USER", "updated_at": "2026-07-14T00:00:00Z"},
                {"id": "user-2", "email": "b@example.com", "nickname": "beta", "role": "ADMIN", "updated_at": "2026-07-13T00:00:00Z"},
            ]
        if endpoint == "chatbot_token_usage_logs":
            return [
                {"user_id": "user-1", "prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15, "created_at": now.isoformat()},
                {"user_id": "user-1", "prompt_tokens": 20, "completion_tokens": 10, "total_tokens": 30, "created_at": (now - timedelta(days=8)).isoformat()},
                {"user_id": "user-2", "prompt_tokens": 7, "completion_tokens": 3, "total_tokens": 10, "created_at": now.isoformat()},
            ]
        return []

    monkeypatch.setattr(admin_users, "_supabase_request", fake_request)

    response = client.get("/api/admin/users", headers={"Authorization": "Bearer admin"})

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["summary"]["totalUsers"] == 2
    assert payload["summary"]["todayTokens"] == 25
    assert payload["summary"]["tokens30d"] == 55
    assert payload["data"][0]["usage"]["totalTokens"] == 45
    assert payload["data"][0]["usage"]["tokens7d"] == 15


def test_list_admin_users_paginates_all_matches_for_system_wide_summary(monkeypatch, client):
    now = datetime(2026, 7, 14, 5, 0, tzinfo=timezone.utc)
    profiles = [
        {"id": "user-1", "email": "alpha-1@example.com", "nickname": "alpha-1", "role": "USER", "updated_at": "2026-07-14T00:00:00Z"},
        {"id": "user-2", "email": "alpha-2@example.com", "nickname": "alpha-2", "role": "USER", "updated_at": "2026-07-13T00:00:00Z"},
        {"id": "user-3", "email": "alpha-3@example.com", "nickname": "alpha-3", "role": "USER", "updated_at": "2026-07-12T00:00:00Z"},
    ]
    logs = [
        {"user_id": "user-1", "total_tokens": 10, "created_at": now.isoformat()},
        {"user_id": "user-2", "total_tokens": 20, "created_at": now.isoformat()},
        {"user_id": "user-3", "total_tokens": 30, "created_at": now.isoformat()},
    ]

    monkeypatch.setattr(admin_users, "_verify_admin", lambda auth_header: {"id": "admin-1"})
    monkeypatch.setattr(admin_users, "_utc_now", lambda: now)
    monkeypatch.setattr(admin_users, "SUPABASE_PAGE_SIZE", 2)

    def fake_request(endpoint, method="GET", params=None, json_data=None, extra_headers=None):
        offset = int(params.get("offset", 0))
        page_size = int(params["limit"])
        if endpoint == "profiles":
            assert "alpha" in params["or"]
            return profiles[offset:offset + page_size]
        if endpoint == "chatbot_token_usage_logs":
            return logs[offset:offset + page_size]
        return []

    monkeypatch.setattr(admin_users, "_supabase_request", fake_request)

    response = client.get("/api/admin/users?q=alpha&limit=2", headers={"Authorization": "Bearer admin"})

    assert response.status_code == 200
    payload = response.get_json()
    assert len(payload["data"]) == 2
    assert payload["summary"] == {
        "totalUsers": 3,
        "todayTokens": 60,
        "tokens30d": 60,
        "activeUsers24h": 3,
    }


def test_list_admin_users_rejects_invalid_limit(monkeypatch, client):
    monkeypatch.setattr(admin_users, "_verify_admin", lambda auth_header: {"id": "admin-1"})

    response = client.get("/api/admin/users?limit=x", headers={"Authorization": "Bearer admin"})

    assert response.status_code == 400
    assert response.get_json()["success"] is False


def test_get_admin_user_chatbot_usage_returns_daily_rows(monkeypatch, client):
    now = datetime(2026, 7, 14, 5, 0, tzinfo=timezone.utc)

    monkeypatch.setattr(admin_users, "_verify_admin", lambda auth_header: {"id": "admin-1"})
    monkeypatch.setattr(admin_users, "_utc_now", lambda: now)

    def fake_request(endpoint, method="GET", params=None, json_data=None, extra_headers=None):
        if endpoint == "profiles":
            return [{"id": "user-1", "email": "a@example.com", "nickname": "alpha", "role": "USER", "updated_at": "2026-07-14T00:00:00Z"}]
        if endpoint == "chatbot_token_usage_logs":
            return [
                {"user_id": "user-1", "request_type": "chat_reply", "model": "gpt-test", "prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15, "created_at": "2026-07-14T01:00:00+00:00"},
                {"user_id": "user-1", "request_type": "tool_synthesis", "model": "gpt-test", "prompt_tokens": 20, "completion_tokens": 10, "total_tokens": 30, "created_at": "2026-07-13T01:00:00+00:00"},
            ]
        return []

    monkeypatch.setattr(admin_users, "_supabase_request", fake_request)

    response = client.get("/api/admin/users/user-1/chatbot-usage", headers={"Authorization": "Bearer admin"})

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["user"]["email"] == "a@example.com"
    assert payload["daily"][0] == {
        "date": "2026-07-14",
        "promptTokens": 10,
        "completionTokens": 5,
        "totalTokens": 15,
        "requestCount": 1,
    }
    assert payload["byRequestType"]["tool_synthesis"]["totalTokens"] == 30
    assert payload["recentLogs"][0]["requestType"] == "chat_reply"
