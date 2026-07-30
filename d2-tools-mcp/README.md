# D2 — Tool Design & MCP Integration (18%)

## 실습 목표
- 좋은 툴 설명(description) vs 나쁜 예를 비교한다.
- 구조화된 에러 응답(`isError`/`errorCategory`/`isRetryable`/`message`)을 구현한다.
- `tool_choice`의 auto/any/특정툴 강제를 각각 실행해 차이를 본다.
- 미니 MCP 서버를 만들고 `.mcp.json`으로 연결한다.

## 시드 (세션에서 함께 추가)
- `tool_errors.py` — 구조화 에러 응답 패턴
- `mcp.json.example` — MCP 서버 설정 템플릿(`${ENV_VAR}` 참조)

## 핵심 함정
- 툴 선택 문제 → 먼저 **툴 설명 개선**(few-shot·라우터보다 우선)
- "툴 많을수록 좋다" → ❌ (선택 신뢰도 저하)
