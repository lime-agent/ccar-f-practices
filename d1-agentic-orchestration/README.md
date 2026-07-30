# D1 — Agentic Architecture & Orchestration (27%)

가장 배점이 큰 도메인. "에이전트가 언제 멈추고(루프) · 어떻게 나눠 일하고(멀티에이전트) · 무엇을 코드로 강제하나".

## 실습 목표
- `stop_reason` 기반 에이전틱 루프를 직접 구현하고 종료 조건을 관찰한다.
- **프로그래밍적 강제(게이트)** — critical 로직을 프롬프트가 아니라 코드로 막는다.
- 멀티에이전트 병렬을 두 방식으로 비교한다: 흉내(스레드) vs 실제(Task).

## 시드 (5개)
| 파일 | 무엇 | 준비물 |
|---|---|---|
| `agentic_loop.py` | 에이전틱 루프(`stop_reason` 제어). 툴 호출→결과 주입→`end_turn` 종료 | Tier 1 (`anthropic[bedrock]`) |
| `programmatic_gate.py` | **게이트(인라인 강제)** — execute_tool 안에서 검증 전 환불 차단 + $500 한도 | Tier 1 |
| `parallel_subagents.py` | 병렬 **흉내** — 파이썬 `ThreadPoolExecutor`로 Claude 호출 3개 동시 | Tier 1 |
| `parallel_subagents_agentsdk.py` | **진짜 병렬** — 코디네이터가 `Task`를 한 응답에 여러 개 → 런타임 동시 실행 | Tier 2 (Claude Code CLI + `claude-agent-sdk`) |
| `hooks_demo_agentsdk.py` | **진짜 hooks** — `PreToolUse`(차단)·`PostToolUse`(정규화) 런타임 콜백 | Tier 2 |

> **강제(enforcement) 두 방식 구분**:
> - `programmatic_gate.py` = 우리 `execute_tool` 안의 **인라인 강제**(Tier 1). 샘플 **Q1** 직결.
> - `hooks_demo_agentsdk.py` = 시험 Task 1.5가 말하는 **진짜 hooks**(Pre/PostToolUse, Tier 2).
> 둘 다 "코드로 결정론적 강제"라는 목적은 같고, 메커니즘·환경이 다르다.

> ⚠️ **시험 직결**: 정답 메커니즘은 **`agentsdk` 버전(Task 다중 호출)**.
> `parallel_subagents.py`의 "별도 스레드/오케스트레이터 레이어" 방식은 **공식 샘플 Q11의 오답 보기**와 닮았으니 "정답"으로 외우지 말 것. ThreadPool은 동시성 체감용.

## 변형 과제
1. `agentic_loop.py`: 툴을 하나 더 추가하고, 종료를 텍스트 키워드로 바꿔 왜 위험한지(안티패턴) 체감.
2. 두 병렬 버전을 각각 돌려 **"흉내(스레드) vs 실제(Task)"** 차이를 정리.
3. `agentsdk` 버전에서 스트리밍 메시지를 보며 **코디네이터가 Task를 여러 개 내는 순간**을 관찰.

## 핵심 정리
- 멈춤은 `stop_reason == "end_turn"` (텍스트 키워드·고정 횟수 ❌)
- 서브에이전트는 컨텍스트 자동 상속 없음 → 프롬프트로 명시 전달
- 서브에이전트 스폰엔 `allowedTools`에 `"Task"` 필요, 병렬은 한 응답에 Task 여러 개
