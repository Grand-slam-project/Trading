import os
from collections import defaultdict
from datetime import datetime, timedelta, timezone

import requests
from flask import Blueprint, jsonify, request

from backend.services.error_message_service import format_error_payload


admin_users_bp = Blueprint("admin_users", __name__)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

ALLOWED_SORTS = {
    "today_tokens",
    "tokens_7d",
    "tokens_30d",
    "total_tokens",
    "recent_used_at",
    "created_at",
}
SUPABASE_PAGE_SIZE = 1000
USAGE_LOG_USER_ID_BATCH_SIZE = 200


class InvalidQueryParameter(ValueError):
    pass


def _utc_now():
    return datetime.now(timezone.utc)


def _json_error(error, title, status_code):
    payload = format_error_payload(error, title)
    return jsonify(payload), status_code


def _extract_bearer_token(auth_header):
    if not auth_header or not auth_header.startswith("Bearer "):
        raise ValueError("로그인이 필요합니다.")
    token = auth_header.split(" ", 1)[1].strip()
    if not token:
        raise ValueError("로그인이 필요합니다.")
    return token


def _require_supabase_config():
    if not SUPABASE_URL or not SUPABASE_ANON_KEY or not SUPABASE_SERVICE_ROLE_KEY:
        raise RuntimeError("Supabase 관리자 조회 환경변수가 설정되어 있지 않습니다.")


def _service_headers(extra_headers=None):
    headers = {
        "apikey": SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
        "Content-Type": "application/json",
    }
    if extra_headers:
        headers.update(extra_headers)
    return headers


def _supabase_request(endpoint, method="GET", params=None, json_data=None, extra_headers=None):
    _require_supabase_config()
    response = requests.request(
        method,
        f"{SUPABASE_URL}/rest/v1/{endpoint}",
        headers=_service_headers(extra_headers),
        params=params,
        json=json_data,
        timeout=15,
    )
    if response.status_code not in (200, 201, 204):
        raise RuntimeError(f"Supabase 관리자 조회에 실패했습니다. HTTP {response.status_code}")
    if not response.text:
        return None
    return response.json()


def _verify_admin(auth_header):
    _require_supabase_config()
    token = _extract_bearer_token(auth_header)
    user_response = requests.get(
        f"{SUPABASE_URL}/auth/v1/user",
        headers={"apikey": SUPABASE_ANON_KEY, "Authorization": f"Bearer {token}"},
        timeout=15,
    )
    if user_response.status_code != 200:
        raise PermissionError("유효한 로그인이 필요합니다.")
    user = user_response.json() or {}
    user_id = user.get("id")
    if not user_id:
        raise PermissionError("유효한 로그인이 필요합니다.")
    rows = _supabase_request(
        "profiles",
        params={"select": "id,email,nickname,role", "id": f"eq.{user_id}", "limit": "1"},
    ) or []
    profile = rows[0] if rows else {}
    if profile.get("role") != "ADMIN":
        raise PermissionError("관리자 권한이 필요합니다.")
    return {"id": user_id, "email": user.get("email") or profile.get("email"), "profile": profile}


def _parse_datetime(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def _int_value(value):
    try:
        parsed = int(value or 0)
        return parsed if parsed >= 0 else 0
    except (TypeError, ValueError):
        return 0


def _bounded_query_int(value, default, minimum, maximum, name):
    if value is None or value == "":
        return default
    try:
        return min(max(int(value), minimum), maximum)
    except (TypeError, ValueError) as error:
        raise InvalidQueryParameter(f"{name} 값은 숫자여야 합니다.") from error


def _load_paginated_rows(endpoint, params):
    rows = []
    offset = 0
    while True:
        page_params = {**params, "limit": str(SUPABASE_PAGE_SIZE), "offset": str(offset)}
        page = _supabase_request(endpoint, params=page_params) or []
        rows.extend(page)
        if len(page) < SUPABASE_PAGE_SIZE:
            return rows
        offset += SUPABASE_PAGE_SIZE


def _load_profiles(query):
    params = {
        "select": "id,email,nickname,role,updated_at",
        "order": "updated_at.desc,id.desc",
    }
    if query:
        safe_query = query.replace("%", "").replace(",", " ").strip()
        params["or"] = f"(email.ilike.*{safe_query}*,nickname.ilike.*{safe_query}*)"
    return _load_paginated_rows("profiles", params)


def _load_usage_logs(user_ids, since=None):
    ids = [str(user_id) for user_id in user_ids if user_id]
    if not ids:
        return []
    logs = []
    for index in range(0, len(ids), USAGE_LOG_USER_ID_BATCH_SIZE):
        params = {
            "select": "user_id,request_type,model,prompt_tokens,completion_tokens,total_tokens,created_at",
            "user_id": f"in.({','.join(ids[index:index + USAGE_LOG_USER_ID_BATCH_SIZE])})",
            "order": "created_at.desc,id.desc",
        }
        if since:
            params["created_at"] = f"gte.{since.isoformat()}"
        logs.extend(_load_paginated_rows("chatbot_token_usage_logs", params))
    return logs


def _build_usage_by_user(logs, now):
    today = now.date()
    seven_days_ago = now - timedelta(days=7)
    thirty_days_ago = now - timedelta(days=30)
    usage = defaultdict(lambda: {
        "todayTokens": 0,
        "tokens7d": 0,
        "tokens30d": 0,
        "totalTokens": 0,
        "todayRequests": 0,
        "requests30d": 0,
        "recentUsedAt": None,
    })
    for row in logs:
        user_usage = usage[row.get("user_id")]
        created_at = _parse_datetime(row.get("created_at"))
        total_tokens = _int_value(row.get("total_tokens"))
        user_usage["totalTokens"] += total_tokens
        if created_at:
            iso_value = created_at.isoformat()
            if not user_usage["recentUsedAt"] or iso_value > user_usage["recentUsedAt"]:
                user_usage["recentUsedAt"] = iso_value
            if created_at.date() == today:
                user_usage["todayTokens"] += total_tokens
                user_usage["todayRequests"] += 1
            if created_at >= seven_days_ago:
                user_usage["tokens7d"] += total_tokens
            if created_at >= thirty_days_ago:
                user_usage["tokens30d"] += total_tokens
                user_usage["requests30d"] += 1
    return usage


@admin_users_bp.route("/api/admin/users", methods=["GET"])
def list_admin_users():
    try:
        _verify_admin(request.headers.get("Authorization"))
        query = str(request.args.get("q") or "").strip()
        sort = str(request.args.get("sort") or "tokens_30d")
        order = str(request.args.get("order") or "desc").lower()
        limit = _bounded_query_int(request.args.get("limit"), 50, 1, 200, "limit")
        if sort not in ALLOWED_SORTS:
            sort = "tokens_30d"
        if order not in {"asc", "desc"}:
            order = "desc"

        profiles = _load_profiles(query)
        now = _utc_now()
        usage_by_user = _build_usage_by_user(_load_usage_logs([row.get("id") for row in profiles]), now)
        rows = []
        for profile in profiles:
            row_usage = usage_by_user[profile.get("id")]
            rows.append({
                "id": profile.get("id"),
                "email": profile.get("email") or "",
                "nickname": profile.get("nickname") or "",
                "role": profile.get("role") or "USER",
                "updatedAt": profile.get("updated_at"),
                "usage": row_usage,
            })

        sort_key_map = {
            "today_tokens": lambda item: item["usage"]["todayTokens"],
            "tokens_7d": lambda item: item["usage"]["tokens7d"],
            "tokens_30d": lambda item: item["usage"]["tokens30d"],
            "total_tokens": lambda item: item["usage"]["totalTokens"],
            "recent_used_at": lambda item: item["usage"]["recentUsedAt"] or "",
            "created_at": lambda item: item["updatedAt"] or "",
        }
        rows.sort(key=sort_key_map[sort], reverse=(order == "desc"))

        summary = {
            "totalUsers": len(rows),
            "todayTokens": sum(item["usage"]["todayTokens"] for item in rows),
            "tokens30d": sum(item["usage"]["tokens30d"] for item in rows),
            "activeUsers24h": sum(1 for item in rows if item["usage"]["recentUsedAt"] and _parse_datetime(item["usage"]["recentUsedAt"]) and _parse_datetime(item["usage"]["recentUsedAt"]) >= now - timedelta(hours=24)),
        }
        return jsonify({"success": True, "data": rows[:limit], "summary": summary})
    except InvalidQueryParameter as error:
        return _json_error(error, "유저 관리 조회 실패", 400)
    except ValueError as error:
        return _json_error(error, "유저 관리 조회 실패", 401)
    except PermissionError as error:
        return _json_error(error, "유저 관리 권한 확인 실패", 403)
    except Exception as error:
        return _json_error(error, "유저 관리 조회 실패", 500)


@admin_users_bp.route("/api/admin/users/<user_id>/chatbot-usage", methods=["GET"])
def get_admin_user_chatbot_usage(user_id):
    try:
        _verify_admin(request.headers.get("Authorization"))
        days = _bounded_query_int(request.args.get("days"), 30, 1, 180, "days")
        limit = _bounded_query_int(request.args.get("limit"), 50, 1, 200, "limit")
        since = _utc_now() - timedelta(days=days)
        profiles = _supabase_request(
            "profiles",
            params={"select": "id,email,nickname,role,updated_at", "id": f"eq.{user_id}", "limit": "1"},
        ) or []
        if not profiles:
            return _json_error(ValueError("사용자를 찾을 수 없습니다."), "유저 사용량 조회 실패", 404)

        logs = _load_usage_logs([user_id], since=since)
        daily = defaultdict(lambda: {"promptTokens": 0, "completionTokens": 0, "totalTokens": 0, "requestCount": 0})
        by_type = defaultdict(lambda: {"promptTokens": 0, "completionTokens": 0, "totalTokens": 0, "requestCount": 0})
        recent_logs = []
        for row in logs:
            created_at = _parse_datetime(row.get("created_at"))
            date_key = created_at.date().isoformat() if created_at else "unknown"
            request_type = row.get("request_type") or "unknown"
            prompt_tokens = _int_value(row.get("prompt_tokens"))
            completion_tokens = _int_value(row.get("completion_tokens"))
            total_tokens = _int_value(row.get("total_tokens"))
            for bucket in (daily[date_key], by_type[request_type]):
                bucket["promptTokens"] += prompt_tokens
                bucket["completionTokens"] += completion_tokens
                bucket["totalTokens"] += total_tokens
                bucket["requestCount"] += 1
            if len(recent_logs) < limit:
                recent_logs.append({
                    "createdAt": row.get("created_at"),
                    "requestType": request_type,
                    "model": row.get("model") or "",
                    "promptTokens": prompt_tokens,
                    "completionTokens": completion_tokens,
                    "totalTokens": total_tokens,
                })

        daily_rows = [
            {"date": key, **value}
            for key, value in sorted(daily.items(), key=lambda item: item[0], reverse=True)
        ]
        profile = profiles[0]
        return jsonify({
            "success": True,
            "user": {
                "id": profile.get("id"),
                "email": profile.get("email") or "",
                "nickname": profile.get("nickname") or "",
                "role": profile.get("role") or "USER",
                "updatedAt": profile.get("updated_at"),
            },
            "daily": daily_rows,
            "byRequestType": dict(by_type),
            "recentLogs": recent_logs,
        })
    except InvalidQueryParameter as error:
        return _json_error(error, "유저 사용량 조회 실패", 400)
    except ValueError as error:
        return _json_error(error, "유저 사용량 조회 실패", 401)
    except PermissionError as error:
        return _json_error(error, "유저 사용량 권한 확인 실패", 403)
    except Exception as error:
        return _json_error(error, "유저 사용량 조회 실패", 500)
