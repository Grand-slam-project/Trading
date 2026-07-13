# Chatbot Test Recovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restore chatbot backend test reliability, starting with broken order/proposal safety behavior.

**Architecture:** Fix narrowly around existing Flask chatbot service modules. Preserve the Human-in-the-Loop order flow: chatbot may create `PENDING` proposals only after precheck data is attached, and real execution remains behind explicit user approval.

**Tech Stack:** Python, Flask service layer, pytest, Supabase REST helper abstractions.

## Global Constraints

- Do not modify unrelated files or the existing dirty `package-lock.json`.
- User-facing backend errors must not expose raw exceptions.
- Real trade execution must not be enabled by chatbot changes.
- Toss is the main stock broker; KIS is legacy/hold.
- Comments added to code must be Korean unless quoting external API terms.
- Run focused tests before reporting completion.

---

### Task 1: Chatbot Order And Proposal Safety Tests

**Files:**
- Modify: `backend/services/chatbot/tool_registry.py`
- Test: `backend/tests/test_chatbot_safety_and_proposals.py`

**Interfaces:**
- Consumes: `parse_order_intent(message) -> ParsedOrderIntent`
- Consumes: `_run_chatbot_precheck(...) -> dict`
- Produces: `run_chatbot_tool(auth_header, message) -> dict | None`
- Produces: `create_trade_proposal(auth_header, arguments) -> dict`

- [ ] **Step 1: Reproduce the focused failures**

Run:

```bash
PYTHONPATH=. pytest backend/tests/test_chatbot_safety_and_proposals.py -q
```

Expected before fix: failures around `missing_exchange`, `unsupported_order_type`, `precheck_failed`, and proposal `data.status`.

- [ ] **Step 2: Fix order/proposal behavior only**

Keep edits in `backend/services/chatbot/tool_registry.py`.

Required outcomes:

- `create_trade_proposal()` must validate missing/failed precheck before inserting a pending proposal.
- Existing tests expecting precheck-related errors should not be shadowed by mock-environment validation.
- `run_chatbot_tool()` must return created proposal fields in `result["data"]`, including `status` and `broker_env` when Supabase returns them.
- Crypto order messages like `XRP 10개 800원에 사줘` should default to a safe proposal flow instead of `missing_exchange`.
- Unsupported Coinone market/amount orders should return `reason: "unsupported_order_type"` without calling precheck or inserting.
- Precheck failures should return `reason: "precheck_failed"` and must not insert a proposal.

- [ ] **Step 3: Verify focused tests**

Run:

```bash
PYTHONPATH=. pytest backend/tests/test_chatbot_safety_and_proposals.py -q
```

Expected after fix: all tests in that file pass.

- [ ] **Step 4: Report**

Report:

- Root cause summary
- Files modified
- Exact test command and result
- Any remaining failures outside this test file
