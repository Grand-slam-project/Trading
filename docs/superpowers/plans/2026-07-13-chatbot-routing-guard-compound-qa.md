# Chatbot Routing Guard And Compound QA Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 자산군/범주만 있는 질문은 확인 응답으로 처리하고, 가격+뉴스/공시/전망 복합 질문은 여러 도구 결과를 조합해 답변한다.

**Architecture:** `backend/services/chatbot/tool_registry.py`의 fast-path 라우팅 앞단에 가드와 복합 정보 라우터를 추가한다. 주문 흐름은 기존 `parse_order_intent()` 우선순위를 유지한다.

**Tech Stack:** Python, pytest, Flask service layer chatbot tool registry.

## Global Constraints

- Follow TDD: write failing tests before production code.
- Do not modify unrelated files or the existing dirty `package-lock.json`.
- Do not change trade proposal creation, approval cards, pending action, or real-order execution behavior.
- Do not use LLM planning for compound routing in this task; use deterministic helpers.
- User-facing replies must include a concrete next action or example.
- Comments added to code must be Korean unless quoting external API terms.

---

### Task 1: Category-Only Routing Guard

**Files:**
- Modify: `backend/services/chatbot/tool_registry.py`
- Test: `backend/tests/test_chatbot_trade_history.py` or a new focused backend chatbot test file

**Interfaces:**
- Add helper: `_build_category_clarification_result(message: str) -> dict | None`
- Consume existing: `run_chatbot_tool(auth_header: str | None, message: str) -> dict | None`

- [ ] **Step 1: Add failing tests**

Add tests for:

```python
def test_run_chatbot_tool_asks_coin_symbol_for_category_only_price_query():
    result = tool_registry.run_chatbot_tool("Bearer test", "코인 시세 알려줘")
    assert result["data"]["source"] == "CATEGORY_CLARIFICATION"
    assert result["data"]["reason"] == "missing_crypto_symbol"
    assert "어떤 코인" in result["reply"]
    assert "BTC" in result["reply"]

def test_run_chatbot_tool_asks_symbol_for_bare_disclosure_query():
    result = tool_registry.run_chatbot_tool("Bearer test", "공시 보여줘")
    assert result["data"]["source"] == "CATEGORY_CLARIFICATION"
    assert result["data"]["reason"] == "missing_disclosure_symbol"
    assert "어떤 종목" in result["reply"]

def test_run_chatbot_tool_asks_news_target_for_bare_news_query():
    result = tool_registry.run_chatbot_tool("Bearer test", "뉴스 알려줘")
    assert result["data"]["source"] == "CATEGORY_CLARIFICATION"
    assert result["data"]["reason"] == "missing_news_target"
    assert "어떤 종목" in result["reply"]
```

Run:

```bash
PYTHONPATH=. pytest backend/tests/test_chatbot_trade_history.py -q
```

Expected before implementation: FAIL because current routing attempts lookup/search instead of clarification.

- [ ] **Step 2: Implement guard**

In `backend/services/chatbot/tool_registry.py`:
- Add a deterministic helper that detects category-only queries.
- Return clarification before exchange-rate/price/outlook/web routing, but after order intent handling.
- Do not trigger clarification when a real symbol or known alias is present, e.g. `비트코인 뉴스`, `삼성전자 공시`, `AAPL 주가`.

- [ ] **Step 3: Verify**

Run:

```bash
PYTHONPATH=. pytest backend/tests/test_chatbot_trade_history.py tests/backend/test_chatbot_tool_registry_price.py backend/tests/test_chatbot_safety_and_proposals.py -q
```

Expected: PASS.

---

### Task 2: Price Plus News/Disclosure/Outlook Compound Routing

**Files:**
- Modify: `backend/services/chatbot/tool_registry.py`
- Test: `backend/tests/test_chatbot_trade_history.py` or a new focused backend chatbot test file

**Interfaces:**
- Add helper: `_run_compound_info_tool(auth_header: str, message: str) -> dict | None`
- Consume existing: `get_asset_price(auth_header, message) -> dict`
- Consume existing: `search_web(auth_header, message) -> dict`
- Consume existing: `get_asset_outlook(auth_header, message) -> dict`

- [ ] **Step 1: Add failing tests**

Stub `get_asset_price`, `search_web`, and `get_asset_outlook` to record calls.

Add tests for:

```python
def test_run_chatbot_tool_combines_price_and_news(monkeypatch):
    calls = []
    monkeypatch.setattr(tool_registry, "get_asset_price", lambda auth, msg: calls.append(("price", msg)) or {"reply": "가격 응답", "data": {"source": "ASSET_PRICE"}})
    monkeypatch.setattr(tool_registry, "search_web", lambda auth, msg: calls.append(("web", msg)) or {"reply": "뉴스 응답", "data": {"source": "NEWS_DB"}})

    result = tool_registry.run_chatbot_tool("Bearer test", "삼성전자 현재가랑 최신 뉴스 알려줘")

    assert calls == [("price", "삼성전자 현재가랑 최신 뉴스 알려줘"), ("web", "삼성전자 현재가랑 최신 뉴스 알려줘")]
    assert result["data"]["source"] == "COMPOUND_INFO"
    assert "가격 응답" in result["reply"]
    assert "뉴스 응답" in result["reply"]

def test_run_chatbot_tool_combines_price_and_disclosure(monkeypatch):
    # same shape, message: "삼성전자 가격이랑 공시 요약해줘"
    # assert secondary source came from search_web

def test_run_chatbot_tool_combines_price_and_outlook(monkeypatch):
    # same shape, message: "테슬라 가격 어때 전망도 알려줘"
    # assert secondary source came from get_asset_outlook
```

Run:

```bash
PYTHONPATH=. pytest backend/tests/test_chatbot_trade_history.py -q
```

Expected before implementation: FAIL because only `get_asset_price` is called.

- [ ] **Step 2: Implement compound helper**

In `run_chatbot_tool()`:
- After category clarification and before standalone price routing, call `_run_compound_info_tool()`.
- Only handle non-order information requests.
- Detect:
  - price + web/news/disclosure
  - price + outlook
- Compose:

```text
현재가
{price_reply}

추가 확인
{secondary_reply}
```

Return data:

```python
{
    "source": "COMPOUND_INFO",
    "components": ["ASSET_PRICE", "..."],
    "price": price_result.get("data"),
    "secondary": secondary_result.get("data"),
}
```

- [ ] **Step 3: Preserve order safety**

Add/keep a test proving:

```python
def test_compound_info_does_not_intercept_order_with_news(monkeypatch):
    # "삼성전자 1주 사줘 그리고 뉴스 알려줘" still follows order flow
```

- [ ] **Step 4: Verify**

Run:

```bash
PYTHONPATH=. pytest backend/tests/test_chatbot_trade_history.py backend/tests/test_chatbot_safety_and_proposals.py tests/backend/test_chatbot_tool_registry_price.py -q
```

Expected: PASS.

---

### Task 3: Full Verification

**Files:**
- No code changes unless verification finds a regression.

- [ ] **Step 1: Run full chatbot tests**

Run:

```bash
PYTHONPATH=. pytest backend/tests/test_chatbot_*.py tests/backend/test_chatbot_*.py -q
```

Expected: PASS.

- [ ] **Step 2: Report**

Report:
- files changed
- tests run and results
- remaining warnings
