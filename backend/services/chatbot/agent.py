"""LangGraph chatbot agent with tool-calling loop."""
import json
import logging
from typing import Annotated, Callable, TypedDict

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages

from backend.services.chatbot.langchain_tools import (
    build_tool_schemas,
    execute_tool_call,
)

logger = logging.getLogger(__name__)
MAX_TOOL_ROUNDS = 5


class AgentState(TypedDict):
    """State for the chatbot LangGraph agent."""
    messages: Annotated[list[BaseMessage], add_messages]
    trace_steps: list[dict]
    user_id: str
    auth_header: str
    request_id: str
    tool_round: int


def _should_continue(state: AgentState) -> str:
    """Determine whether to call tools or end."""
    messages = state.get("messages") or []
    if not messages:
        return END

    last_message = messages[-1]
    if not isinstance(last_message, AIMessage):
        return END

    tool_calls = getattr(last_message, "tool_calls", None) or []
    if not tool_calls:
        return END

    tool_round = state.get("tool_round") or 0
    if tool_round >= MAX_TOOL_ROUNDS:
        logger.warning(
            "Max tool rounds reached (%d). Stopping. request_id=%s",
            MAX_TOOL_ROUNDS,
            state.get("request_id"),
        )
        return END

    return "tools"


def _call_model_node(state: AgentState, llm: BaseChatModel) -> dict:
    """Invoke the LLM with current messages."""
    messages = state.get("messages") or []
    tool_schemas = build_tool_schemas()
    llm_with_tools = llm.bind_tools(tool_schemas)
    response = llm_with_tools.invoke(messages)
    return {"messages": [response]}


def _tools_node(state: AgentState) -> dict:
    """Execute tool calls from the last AI message."""
    messages = state.get("messages") or []
    last_message = messages[-1]
    auth_header = state.get("auth_header") or ""
    trace_steps = list(state.get("trace_steps") or [])
    tool_round = (state.get("tool_round") or 0) + 1

    tool_messages: list[ToolMessage] = []
    for tool_call in getattr(last_message, "tool_calls", []) or []:
        tool_name = tool_call.get("name") or ""
        arguments = tool_call.get("args") or {}
        tool_call_id = tool_call.get("id") or ""

        trace_steps.append({"kind": "tool", "label": f"도구 실행: {tool_name}"})

        try:
            result_str = execute_tool_call(tool_name, arguments, auth_header)
        except Exception as error:
            result_str = json.dumps(
                {"reply": f"도구 실행 실패: {str(error)[:200]}", "data": {"error": "tool_error"}},
                ensure_ascii=False,
            )

        tool_messages.append(
            ToolMessage(content=result_str, tool_call_id=tool_call_id)
        )

    return {
        "messages": tool_messages,
        "trace_steps": trace_steps,
        "tool_round": tool_round,
    }


def create_chatbot_agent(llm: BaseChatModel):
    """Create a compiled LangGraph agent with the given LLM.

    The agent follows a call_model -> tools loop pattern.
    """
    graph = StateGraph(AgentState)

    graph.add_node("call_model", lambda state: _call_model_node(state, llm))
    graph.add_node("tools", _tools_node)

    graph.set_entry_point("call_model")
    graph.add_conditional_edges("call_model", _should_continue, {"tools": "tools", END: END})
    graph.add_edge("tools", "call_model")

    return graph.compile()


def run_agent(
    agent,
    *,
    system_prompt: str,
    user_message: str,
    history: list[dict] | None = None,
    user_id: str = "",
    auth_header: str = "",
    request_id: str = "",
) -> dict:
    """Run the agent synchronously and return the final result."""
    messages: list[BaseMessage] = [SystemMessage(content=system_prompt)]

    for item in history or []:
        role = item.get("role")
        content = str(item.get("content") or "").strip()
        if not content:
            continue
        if role == "user":
            messages.append(HumanMessage(content=content))
        elif role == "assistant":
            messages.append(AIMessage(content=content))

    messages.append(HumanMessage(content=user_message))

    initial_state = {
        "messages": messages,
        "trace_steps": [{"kind": "request", "label": "요청 분석"}],
        "user_id": user_id,
        "auth_header": auth_header,
        "request_id": request_id,
        "tool_round": 0,
    }

    final_state = agent.invoke(initial_state)

    final_messages = final_state.get("messages") or []
    reply = ""
    for msg in reversed(final_messages):
        if isinstance(msg, AIMessage) and msg.content:
            reply = str(msg.content).strip()
            break

    if not reply:
        reply = "응답을 만들지 못했습니다. 잠시 후 다시 시도해 주세요."

    tool_results = []
    for msg in final_messages:
        if isinstance(msg, ToolMessage):
            try:
                tool_results.append(json.loads(msg.content))
            except (TypeError, ValueError):
                tool_results.append({"reply": msg.content})

    return {
        "reply": reply,
        "actions": [],
        "meta": {
            "user_id": user_id,
            "request_id": request_id,
            "trace_steps": final_state.get("trace_steps") or [],
            "tool_results": tool_results,
            "tool_rounds": final_state.get("tool_round") or 0,
            "source": "LANGGRAPH_AGENT",
        },
    }


def stream_agent(
    agent,
    *,
    system_prompt: str,
    user_message: str,
    history: list[dict] | None = None,
    user_id: str = "",
    auth_header: str = "",
    request_id: str = "",
    on_delta: Callable[[str], None] | None = None,
    on_trace: Callable[[dict], None] | None = None,
) -> dict:
    """Run the agent with streaming, calling on_delta for each token."""
    messages: list[BaseMessage] = [SystemMessage(content=system_prompt)]

    for item in history or []:
        role = item.get("role")
        content = str(item.get("content") or "").strip()
        if not content:
            continue
        if role == "user":
            messages.append(HumanMessage(content=content))
        elif role == "assistant":
            messages.append(AIMessage(content=content))

    messages.append(HumanMessage(content=user_message))

    initial_state = {
        "messages": messages,
        "trace_steps": [{"kind": "request", "label": "요청 분석"}],
        "user_id": user_id,
        "auth_header": auth_header,
        "request_id": request_id,
        "tool_round": 0,
    }

    trace_steps: list[dict] = [{"kind": "request", "label": "요청 분석"}]
    reply_parts: list[str] = []
    tool_results: list[dict] = []
    tool_rounds = 0

    for event in agent.stream(initial_state, stream_mode="updates"):
        for node_name, node_output in event.items():
            node_messages = node_output.get("messages") or []
            for msg in node_messages:
                if isinstance(msg, AIMessage):
                    content = str(msg.content or "").strip()
                    tool_calls = getattr(msg, "tool_calls", None) or []
                    if content and not tool_calls:
                        reply_parts.append(content)
                        if on_delta:
                            on_delta(content)
                    elif tool_calls and on_trace:
                        for tc in tool_calls:
                            on_trace({"kind": "openai_tool_call", "label": f"도구 호출: {tc.get('name')}"})

                elif isinstance(msg, ToolMessage):
                    if on_trace:
                        on_trace({"kind": "tool_done", "label": "도구 결과 수신"})
                    try:
                        tool_results.append(json.loads(msg.content))
                    except (TypeError, ValueError):
                        tool_results.append({"reply": msg.content})

            if "trace_steps" in node_output:
                new_steps = node_output["trace_steps"]
                for step in new_steps:
                    if step not in trace_steps:
                        trace_steps.append(step)
                        if on_trace:
                            on_trace(step)
            if "tool_round" in node_output:
                tool_rounds = node_output["tool_round"]

    reply = "".join(reply_parts).strip()
    if not reply:
        reply = "응답을 만들지 못했습니다. 잠시 후 다시 시도해 주세요."

    return {
        "reply": reply,
        "actions": [],
        "meta": {
            "user_id": user_id,
            "request_id": request_id,
            "trace_steps": trace_steps,
            "tool_results": tool_results,
            "tool_rounds": tool_rounds,
            "source": "LANGGRAPH_AGENT",
        },
    }
