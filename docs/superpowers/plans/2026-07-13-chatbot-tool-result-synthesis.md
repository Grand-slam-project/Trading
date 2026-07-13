# Chatbot Tool Result Synthesis Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** OpenAI function calling으로 실행된 챗봇 도구 결과를 LLM이 한 번 더 재합성해 자연스러운 최종 답변으로 반환한다.

**Architecture:** `ChatbotLLMClient`에 재합성 메서드를 추가하고, `ChatbotService.reply()`의 `OPENAI_TOOL_CALL` 분기에서만 호출한다. 실패 시 기존 도구 응답으로 폴백한다.

**Tech Stack:** Python, Flask service layer, pytest, requests 기반 OpenAI Chat Completions client.

## Global Constraints

- Do not modify unrelated files or the existing dirty `package-lock.json`.
- Do not change trade proposal creation, approval cards, pending action, or keyword fast-path behavior.
- Do not expose raw provider payloads, API keys, account numbers, tokens, or stack traces in user-facing replies.
- Recomposition failure must fall back to the original tool reply instead of failing the chatbot response.
- Comments added to code must be Korean unless quoting external API terms.
- Follow TDD: write failing tests before production code.

---

### Task 1: OpenAI Tool Result Recomposition

**Files:**
- Modify: `backend/services/chatbot/llm_client.py`
- Modify: `backend/services/chatbot/chat_service.py`
- Test: `backend/tests/test_chatbot_profile_context.py` or a new focused backend chatbot test file

**Interfaces:**
- Add: `ChatbotLLMClient.synthesize_tool_result_reply(system_prompt: str, user_message: str, tool_name: str | None, tool_reply: str, tool_data: dict | None) -> dict`
- Consume existing: `ChatbotService._run_llm_tool_call(auth_header, tool_call, fallback_text) -> dict | None`
- Preserve response meta: `tool_result`, `trace_steps`, `tool_call`, `source`

- [ ] **Step 1: Add failing test for successful recomposition**

Create or modify a chatbot service test that stubs:

```python
class FakeLLM:
    def generate_reply(self, **kwargs):
        return {
            "reply": "",
            "tool_calls": [{
                "function": {
                    "name": "get_asset_price",
                    "arguments": "{\"query\":\"AAPL\"}",
                }
            }],
            "model": "fake",
            "usage": {},
        }

    def synthesize_tool_result_reply(self, **kwargs):
        return {"reply": "AAPL은 현재가와 등락률을 함께 보면 단기 변동성은 낮지만 확인이 필요합니다."}
```

Stub `_run_llm_tool_call()` to return:

```python
{
    "reply": "AAPL 현재가는 $210.50입니다.",
    "actions": [{"type": "navigate", "label": "AAPL 보기", "to": "/asset/STOCK/AAPL"}],
    "data": {"source": "ASSET_PRICE", "symbol": "AAPL", "current_price": 210.5},
}
```

Assert:
- final `reply` is the synthesized reply
- `actions` are preserved
- `meta.tool_result.symbol == "AAPL"`
- `meta.source == "OPENAI_TOOL_CALL"`

Run:

```bash
PYTHONPATH=. pytest <chosen_test_file>::<test_name> -q
```

Expected: FAIL because `synthesize_tool_result_reply` is not called or not implemented.

- [ ] **Step 2: Add failing test for fallback**

Use a fake LLM where `synthesize_tool_result_reply()` raises `RuntimeError("provider down")`.

Assert:
- final `reply` is original `"AAPL 현재가는 $210.50입니다."`
- `meta.source == "OPENAI_TOOL_CALL"`
- no exception escapes `ChatbotService.reply()`

Run:

```bash
PYTHONPATH=. pytest <chosen_test_file>::<test_name> -q
```

Expected: FAIL until fallback behavior is implemented.

- [ ] **Step 3: Implement client method**

In `backend/services/chatbot/llm_client.py`, add `synthesize_tool_result_reply(...)`.

Behavior:
- Build a Chat Completions payload with no function tools.
- Use the configured model, `temperature=0.2`, and a conservative max token cap no larger than `self.max_output_tokens`.
- Include instructions in Korean:
  - answer in Korean
  - use only the given tool result
  - do not add facts not present in tool result
  - keep the answer concise and actionable
  - preserve safety caveats for investment decisions
- Serialize `tool_data` with `json.dumps(..., ensure_ascii=False, default=str)` and truncate if needed to avoid huge prompts.
- Return `{"reply": content, "usage": usage, "model": self.model}`.

- [ ] **Step 4: Wire service fallback**

In `backend/services/chatbot/chat_service.py`, update only the `for tool_call in result.get("tool_calls")` branch:
- execute the tool as before
- call a small helper or inline guarded block to synthesize
- on exception, log via `_log_repository_failure()` or `logger.exception()` and use original tool reply
- record the final reply, not the raw tool reply
- keep all existing meta fields

- [ ] **Step 5: Verify focused tests**

Run the new/modified tests:

```bash
PYTHONPATH=. pytest <chosen_test_file> -q
```

Expected: PASS.

- [ ] **Step 6: Verify chatbot suite**

Run:

```bash
PYTHONPATH=. pytest backend/tests/test_chatbot_*.py tests/backend/test_chatbot_*.py -q
```

Expected: PASS.

- [ ] **Step 7: Report**

Report:
- root cause addressed
- files modified
- exact tests run and results
- any warnings left
