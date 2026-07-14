from backend.services.chatbot.llm_client import ChatbotLLMClient


class FakeResponse:
    status_code = 200

    @staticmethod
    def json():
        return {
            "choices": [{"message": {"content": "응답"}}],
            "usage": {
                "prompt_tokens": 11,
                "completion_tokens": 7,
                "total_tokens": 18,
            },
        }


def test_normalize_usage_requires_positive_total_tokens():
    client = ChatbotLLMClient()

    assert client._normalize_usage(None) is None
    assert client._normalize_usage({}) is None
    assert client._normalize_usage({"total_tokens": 0}) is None
    assert client._normalize_usage({
        "prompt_tokens": "4",
        "completion_tokens": 3,
        "total_tokens": 7,
    }) == {
        "prompt_tokens": 4,
        "completion_tokens": 3,
        "total_tokens": 7,
    }


def test_generate_reply_records_actual_usage(monkeypatch):
    calls = []
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(
        "backend.services.chatbot.llm_client.requests.post",
        lambda *args, **kwargs: FakeResponse(),
    )

    def fake_query(auth_header, endpoint, method="GET", json_data=None, params=None, extra_headers=None):
        if endpoint == "rpc/consume_chatbot_usage":
            return [{"allowed": True}]
        calls.append({
            "auth_header": auth_header,
            "endpoint": endpoint,
            "method": method,
            "json_data": json_data,
        })
        return []

    monkeypatch.setattr("backend.services.chatbot.llm_client.query_supabase", fake_query)

    client = ChatbotLLMClient()
    result = client.generate_reply(
        system_prompt="시스템",
        user_message="질문",
        user_id="user-1",
        auth_header="Bearer test",
    )

    assert result["usage"]["total_tokens"] == 18
    assert calls == [{
        "auth_header": "Bearer test",
        "endpoint": "chatbot_token_usage_logs",
        "method": "POST",
        "json_data": {
            "user_id": "user-1",
            "request_type": "chat_reply",
            "model": client.model,
            "prompt_tokens": 11,
            "completion_tokens": 7,
            "total_tokens": 18,
        },
    }]


def test_usage_logging_failure_does_not_fail_reply(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(
        "backend.services.chatbot.llm_client.requests.post",
        lambda *args, **kwargs: FakeResponse(),
    )

    def fake_query(auth_header, endpoint, method="GET", json_data=None, params=None, extra_headers=None):
        if endpoint == "rpc/consume_chatbot_usage":
            return [{"allowed": True}]
        raise RuntimeError("Supabase unavailable")

    monkeypatch.setattr("backend.services.chatbot.llm_client.query_supabase", fake_query)

    client = ChatbotLLMClient()
    result = client.generate_reply(
        system_prompt="시스템",
        user_message="질문",
        user_id="user-1",
        auth_header="Bearer test",
    )

    assert result["reply"] == "응답"
    assert result["usage"]["total_tokens"] == 18
