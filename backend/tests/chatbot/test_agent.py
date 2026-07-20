# backend/tests/chatbot/test_agent.py
import os
import pytest


def test_create_chatbot_agent_returns_compiled_graph(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    from backend.services.chatbot.llm_provider import create_chatbot_llm
    from backend.services.chatbot.agent import create_chatbot_agent

    llm = create_chatbot_llm()
    agent = create_chatbot_agent(llm)
    assert agent is not None
    assert hasattr(agent, "invoke")


def test_agent_state_has_required_keys():
    from backend.services.chatbot.agent import AgentState
    assert "messages" in AgentState.__annotations__
    assert "trace_steps" in AgentState.__annotations__
    assert "auth_header" in AgentState.__annotations__
    assert "user_id" in AgentState.__annotations__


def test_max_tool_rounds_default():
    from backend.services.chatbot.agent import MAX_TOOL_ROUNDS
    assert MAX_TOOL_ROUNDS >= 5
