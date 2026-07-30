# D4 — Prompt Engineering & Structured Output (20%)

## 실습 목표
- `tool_use` + JSON 스키마로 구조화 추출, `nullable`로 환각 방지(없는 값 → null).
- few-shot 예시 2~4개로 정확도 개선을 관찰한다.
- 검증-재시도 루프를 구현한다.
- Batch API는 **개념만** (Bedrock 키로는 실습 불가, Anthropic 1st-party 전용).

## 시드 (세션에서 함께 추가)
- `extract_structured.py` — nullable 추출(구조화 출력)

## 핵심 정리
- `tool_use`는 **JSON 구문 오류**를 제거(의미 검증은 별도 필요)
- 없는 값은 `["type","null"]` + null 지시로 환각 방지
- Batch API: 24h·50% 절감·SLA 없음 → 실시간/pre-merge엔 부적합
