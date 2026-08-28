# D5 — Context Management & Reliability (15%)

긴 컨텍스트·다단계·장기 세션에서 정보 손실을 막고, 에스컬레이션·에러 전파·출처 보존을 신뢰성 있게 설계하는 도메인.

정신모델: **컨텍스트는 유한한 예산** — 채우는 기술이 아니라 지키는 기술.

## 실습 목표
- 툴 결과를 누적 **전에** 트리밍해 컨텍스트 예산을 지킨다 (5.1)
- 요약이 수치를 뭉개는 것을 관찰하고 **case facts 블록**으로 막는다 (5.1)
- 에스컬레이션 기준을 명시적으로 박아 판단 보정을 개선한다 (5.2)
- **structured error context**로 코디네이터의 복구 가능성을 만든다 (5.3)

## 시드 (4개, 전부 Tier 1 — `anthropic[bedrock]`)
| 파일 | 다루는 것 |
|---|---|
| `context_trim.py` | 44필드 툴 결과 → 관련 5필드 트리밍(87% 절감) + 트리밍 후에도 판단 가능한지 확인 (5.1 / Ch15.1) |
| `case_facts_block.py` | 요약만 vs 요약+case facts vs 원본 3조건 비교 — 수치 보존율을 코드가 판정 (5.1 / Ch15.3) |
| `escalation_prompt.py` | 기준 없음 vs 명시적 기준+few-shot — 4케이스 정확도 비교 (5.2 / Ch16.1, 공식 샘플 문제 3) |
| `error_propagation.py` | 범용 에러 vs structured error context — 코디네이터 복구 가능성 비교 (5.3 / Ch16.2, 공식 샘플 문제 8) |

> 각 스크립트는 **결정론 파트**(모델 호출 없이 항상 재현되는 픽스처·분기)와
> **라이브 파트**(실제 호출)를 나눠 담았다. 모델·샘플링 변동으로 라이브 결과가 흔들려도
> 결정론 파트에서 개념이 확정적으로 보인다. (D4 실습에서 얻은 교훈)

## 실행 예
```bash
source .venv/bin/activate
python d5-context-reliability/context_trim.py
python d5-context-reliability/case_facts_block.py
python d5-context-reliability/escalation_prompt.py
python d5-context-reliability/error_propagation.py
```

## 다루지 않는 것 (강의로만)
- **Task 5.4 대규모 코드베이스 탐색**: scratchpad·서브에이전트 위임·`/compact`·manifest 크래시 복구
  → Claude Code 세션 자체가 실습 환경(D3 데모 repo에서 체감). 여기 스크립트로는 재현 부적합.
- **Task 5.5 human review·confidence 보정**: stratified sampling·labeled validation 셋 보정
  → 라벨링된 검증셋이 필요해 스터디 범위 밖. ⚠️ **교재 Ch15·16에 아예 없는 태스크**라 강의자료로 보완.
- **Task 5.6 provenance**: claim-source 매핑·상충 통계 주석
  → D4 `review_pattern_demo.py`의 claim-source 구조와 겹쳐 개념 설명으로 대체.

## 핵심 정리
- 툴 결과는 **누적되기 전에** 관련 필드만 트리밍 (재조회가 가능하면 "적시 검색"이 더 싸다)
- Lost-in-the-Middle: 처음·끝은 안정, **중간 누락** → 핵심 요약을 앞에 + 섹션 헤더
- 요약은 **반드시 손실을 낸다** → 수치·날짜·번호는 요약 밖 **case facts 블록**으로
- 에스컬레이션 = **사람 명시 요청 · 정책 공백 · 진전 불가** (감정 ❌ / confidence 점수 ❌)
- 복수 매치 → 휴리스틱 선택 ❌, **추가 식별자 요청**
- 에러 전파 4요소 = **실패 유형 · 시도한 쿼리 · 부분 결과 · 대안**
- **access 실패 vs valid empty result** 구분 (D2 2.2가 D5에서 재등장)
- 상충 정보는 임의 선택 ❌ → 둘 다 **출처와 함께** 보고

## 교재 매핑
Ch15 컨텍스트 관리(15.1~15.3) · Ch16 에스컬레이션·신뢰성(16.1~16.4) · 시나리오1(고객지원)·시나리오3(멀티에이전트)
