# Chatbot Tool Result Synthesis Design

## Goal

OpenAI function calling으로 선택된 챗봇 도구 결과를 LLM이 한 번 더 자연어로 재작성해, 사용자가 고정 템플릿 대신 맥락 있는 분석 답변을 받게 한다.

## Scope

이번 변경은 `ChatbotService.reply()`에서 OpenAI tool call 이후 실행되는 경로만 다룬다.

포함:
- LLM이 function calling으로 고른 도구 실행 결과 재합성
- 재합성 실패 시 기존 도구 응답 폴백
- 기존 `actions`, `tool_result`, `trace_steps`, `source=OPENAI_TOOL_CALL` 메타데이터 보존
- 관련 단위 테스트 추가

제외:
- 키워드 fast-path 도구 결과 재합성
- 매매 제안 생성, 승인 카드, pending action 흐름 변경
- 실거래 주문 실행 흐름 변경
- 프론트 UI 변경

## Architecture

`ChatbotLLMClient`에 도구 결과 최종 답변 생성 메서드를 추가한다. 이 메서드는 원래 사용자 질문, 도구 이름, 도구의 기존 답변, 구조화된 도구 데이터를 입력받아 짧고 실용적인 한국어 답변을 생성한다.

`ChatbotService.reply()`는 기존처럼 OpenAI tool call을 실행한다. 도구 결과가 있으면 `synthesize_tool_result_reply()`를 호출하고, 성공하면 그 답변을 저장 및 반환한다. 실패하면 기존 `tool_result["reply"]`를 그대로 사용한다.

## Data Flow

1. 사용자가 일반 질문을 입력한다.
2. fast-path 도구가 매칭되지 않으면 기존 LLM 호출이 실행된다.
3. LLM이 `tool_calls`를 반환하면 `_run_llm_tool_call()`이 내부 도구를 실행한다.
4. 도구 결과가 있으면 재합성 LLM 호출을 시도한다.
5. 성공 시 재합성 답변을 반환한다.
6. 실패 시 기존 도구 응답을 반환한다.

## Safety Rules

- 주문 생성 도구는 이번 재합성 대상이 아니다. 현재 `FUNCTION_SCHEMAS`에는 주문 생성 도구가 없으며, 이 상태를 유지한다.
- 재합성 프롬프트는 도구 결과에 없는 사실을 추가하지 말라고 명시한다.
- 도구 결과의 raw payload나 민감정보를 확대 노출하지 않는다.
- 재합성 실패는 사용자 요청 실패로 처리하지 않고 기존 도구 응답으로 폴백한다.

## Error Handling

재합성 호출 중 예외가 발생하면 로그만 남기고 기존 도구 응답을 사용한다. 챗봇 전체 응답을 500으로 실패시키지 않는다.

## Testing

추가/수정 테스트:
- OpenAI tool call 이후 `synthesize_tool_result_reply()`가 호출되고 반환 답변이 최종 reply가 되는지 확인한다.
- 재합성 실패 시 기존 도구 응답으로 폴백하는지 확인한다.
- `actions`, `tool_result`, `trace_steps`, `source` 메타데이터가 유지되는지 확인한다.
- 전체 챗봇 테스트가 통과하는지 확인한다.

검증 명령:

```bash
PYTHONPATH=. pytest backend/tests/test_chatbot_*.py tests/backend/test_chatbot_*.py -q
```
