# D4 — Prompt Engineering & Structured Output (20%)

명시적 기준 설계·few-shot·구조화 출력(신뢰성 사다리)으로 정확하고 검증 가능한 결과를 얻는 도메인.

## 실습 목표
- `tool_use` + JSON 스키마로 구조화 추출, `nullable`로 환각 방지(없는 값 → null). (교재 A4 #3)
- few-shot 예시 2~4개로 정확도 개선을 관찰한다.
- 검증-재시도 루프를 구현한다.
- 자기 리뷰 vs 독립 인스턴스 리뷰, 멀티패스(개별 파일 → 크로스파일), 신뢰도 라우팅을 관찰한다. (Ch14)
- Batch API는 **개념만** (Bedrock 키로는 실습 불가, Anthropic 1st-party 전용).

## 시드

**Tier 1 — Messages API (`anthropic[bedrock]`, 필수)**
| 파일 | 다루는 것 |
|---|---|
| `extract_structured.py` | `tool_use` + nullable 스키마로 환각 방지 (교재 A4 #3) + enum·"other"·detail 확장 설계(13.2) |
| `few_shot_accuracy.py` | 지시없음→명시적 기준만(12.1)→기준+few-shot(12.2) 3조건 비교 — 정답률로 검증 |
| `validate_retry_loop.py` | 스키마 검증 실패 → `tool_result`(is_error)로 재시도 + 재시도 유용성 판정(13.3, RETRYABLE vs NOT_RETRYABLE) |
| `review_pattern_demo.py` | 자기 리뷰 vs 독립 인스턴스(37·38) + 멀티패스(39) + 신뢰도 라우팅 |

**Tier 2 — Claude Agent SDK (`claude-agent-sdk` + Claude Code CLI, 선택·심화)**
| 파일 | 다루는 것 |
|---|---|
| `validate_retry_loop_agentsdk.py` | 검증을 커스텀 MCP 툴 안에 넣어, 에이전트의 **내장 루프**가 `is_error`를 보고 스스로 재시도 (D2 `structured_tool_errors_agentsdk.py`와 같은 패턴) |
| `review_pattern_demo_agentsdk.py` | 독립 리뷰를 **서브에이전트**(Task)로 구현(D1 05.3) + 멀티패스(file_reviewer → integrator) + 신뢰도 버킷 |

> 명시적 기준·few-shot은 순수 프롬프팅 개념이라 Tier2로 옮겨도 새로 보여줄 게 없어 짝을 만들지 않았다.
> Batch API(Ch14)는 Anthropic 1st-party 전용이라 Bedrock 키로는(Tier1/Tier2 무관) 실행할 수 없다 — 개념은 강의자료·실습가이드에서 설명만 다룬다.

## 실행 예
```bash
source .venv/bin/activate
python d4-prompt-structured-output/extract_structured.py        # (Tier1)
python d4-prompt-structured-output/few_shot_accuracy.py          # (Tier1)
python d4-prompt-structured-output/validate_retry_loop.py        # (Tier1)
python d4-prompt-structured-output/review_pattern_demo.py        # (Tier1)
# (Tier2, 선택) python d4-prompt-structured-output/validate_retry_loop_agentsdk.py
# (Tier2, 선택) python d4-prompt-structured-output/review_pattern_demo_agentsdk.py
```

## 핵심 정리
- `tool_use`는 **구문 오류**만 막아준다 — 의미적 정확성(환각 등)은 별도 검증 필요
- nullable 필드 = `["type", "null"]` + "없으면 null, 추측 금지" 명시
- few-shot은 2~4개, **서로 다른 케이스**로 기준을 못박을 때 효과적
- 검증 실패는 `tool_result(is_error=true)`로 모델에 돌려주면 스스로 재시도
- 리뷰는 자기 리뷰 < 독립 인스턴스 리뷰, 멀티패스는 개별 파일 → 크로스파일, 신뢰도 ≥0.8 자동 / 0.4–0.8 인간 / <0.4 무시
- Batch API: 최대 24h·50% 절감·SLA 없음 → 야간 배치·대량 분류엔 적합, 실시간·pre-merge엔 부적합

## 교재 매핑
Ch12 프롬프트 기초 · Ch13 구조화 출력 · Ch14 배치/리뷰 · 시나리오6
