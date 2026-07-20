# backend/tests/chatbot/test_chat_service_agent.py
import pytest


def test_chatbot_service_has_agent_attribute(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    from backend.services.chatbot.chat_service import ChatbotService
    service = ChatbotService()
    assert hasattr(service, "agent")
    assert service.agent is not None


def test_chatbot_service_reply_signature_unchanged(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    import inspect
    from backend.services.chatbot.chat_service import ChatbotService
    sig = inspect.signature(ChatbotService.reply)
    param_names = list(sig.parameters.keys())
    assert "message" in param_names
    assert "user_id" in param_names
    assert "auth_header" in param_names
    assert "trace_callback" in param_names
    assert "delta_callback" in param_names
    assert "request_id" in param_names
    assert "structured_order" in param_names
