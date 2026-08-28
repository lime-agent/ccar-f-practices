"""D5 실습 — 구조화 에러 전파로 코디네이터 복구 가능성 만들기 (Task 5.3 / Ch16.2).

시험 D5 핵심(공식 샘플 문제 8): 서브에이전트가 실패했을 때 코디네이터의
**지능적 복구**를 가능케 하는 것은 structured error context다:
  실패 유형 · 시도한 쿼리 · 부분 결과 · 잠재 대안 접근
반대로 안티패턴 3종:
  - 범용 상태("search unavailable")  → 가치 있는 컨텍스트를 숨긴다
  - 조용한 억제(빈 결과를 성공으로)   → 복구 차단 + 불완전 결과 위험
  - 전체 워크플로우 종료             → 복구 가능한 걸 전멸시킨다

이 데모는 두 부분이다:
  1) 결정론적 분기 — access 실패 vs valid empty result 구분(모델 없이 항상 재현).
  2) 라이브 비교 — 같은 실패를 (A)범용 상태 / (B)구조화 컨텍스트로 코디네이터에
     넘겼을 때, 코디네이터가 내놓는 다음 행동이 얼마나 구체적인지.

실행: practices/ 에서  python d5-context-reliability/error_propagation.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from shared.bedrock_client import DEFAULT_MODEL, get_client  # noqa: E402

client = get_client()

QUERY = "2026년 국내 전기차 보조금 정책 변경 내역"

# (A) 안티패턴 — 범용 상태. 코디네이터가 알 수 있는 게 없다.
GENERIC_ERROR = {"status": "search unavailable"}

# (B) 정답 — structured error context 4요소 (+ isRetryable)
STRUCTURED_ERROR = {
    "success": False,
    "errorType": "timeout",                     # ① 실패 유형
    "attemptedQuery": QUERY,                    # ② 시도한 쿼리
    "partialResults": [                         # ③ 부분 결과 (있으면 반드시)
        {"title": "환경부 2026 보조금 개편안 보도자료", "url": "https://example.gov/pr/2026-ev",
         "snippet": "차량 가격 구간별 차등 지급 확대…", "collected_at": "2026-08-27"},
    ],
    "isRetryable": True,
    "suggestedAlternatives": [                  # ④ 대안 접근
        f"{QUERY} site:me.go.kr",
        f"{QUERY} filetype:pdf",
        "쿼리 축소: '2026 전기차 보조금 개편'",
    ],
    "message": "웹 검색 30초 타임아웃. 부분 결과 1건 확보. 쿼리 축소 또는 사이트 한정 재시도 권장.",
}


def classify_tool_outcome(outcome: dict) -> tuple[str, str]:
    """access 실패와 valid empty result를 구분한다 — 뭉개면 코디네이터가 오판한다.

    D2 2.2의 '빈 결과는 에러가 아니다'가 D5에서 다시 나오는 지점.
    """
    if outcome.get("error"):
        return "ACCESS_FAILURE", "재시도 판단 필요 — 데이터가 없는지는 아직 모른다"
    if not outcome.get("results"):
        return "VALID_EMPTY", "정상 성공(매치 없음) — 재시도 무의미, 그대로 보고"
    return "SUCCESS", f"{len(outcome['results'])}건 확보"


def coordinator_next_action(error_payload: dict, label: str) -> str:
    """코디네이터 역할: 서브에이전트의 실패 보고를 받고 다음 행동을 결정한다."""
    resp = client.messages.create(
        model=DEFAULT_MODEL,
        max_tokens=400,
        system=(
            "너는 멀티에이전트 리서치 시스템의 코디네이터다. "
            "웹 검색 서브에이전트가 실패를 보고했다. 아래 보고만 근거로 "
            "다음에 취할 구체적 행동을 결정하라. 보고에 없는 정보는 추측하지 마라. "
            "답변은 3줄 이내."
        ),
        messages=[{
            "role": "user",
            "content": (
                f"[서브에이전트 실패 보고]\n{json.dumps(error_payload, ensure_ascii=False, indent=2)}\n\n"
                "다음 행동은?"
            ),
        }],
    )
    return "".join(b.text for b in resp.content if b.type == "text").strip()


# 복구 가능성 지표: 구체적 복구 수단을 언급했는지 (우리 코드가 판정)
RECOVERY_SIGNALS = ("재시도", "부분", "대안", "site:", "축소", "pdf", "쿼리")


def recovery_score(answer: str) -> tuple[int, list[str]]:
    hits = [s for s in RECOVERY_SIGNALS if s.lower() in answer.lower()]
    return len(hits), hits


if __name__ == "__main__":
    print("=" * 60)
    print("[1] 결정론적 분기 — access 실패 vs valid empty result (모델 호출 없음)")
    fixtures = [
        ("타임아웃", {"error": "timeout"}),
        ("매치 0건", {"results": []}),
        ("정상 3건", {"results": [1, 2, 3]}),
    ]
    for name, outcome in fixtures:
        kind, note = classify_tool_outcome(outcome)
        print(f"  {name:10s} → {kind:15s} : {note}")
    print("  ※ 이 둘을 같은 '실패'로 뭉개면 코디네이터가 '없는 데이터를 계속 재시도'하거나")
    print("     '접근 실패를 데이터 없음으로 오해'한다. (D2 2.2의 원칙이 D5에서 재등장)")

    print()
    print("=" * 60)
    print("[2] 라이브 비교 — 같은 타임아웃, 다른 보고 방식")

    print("\n--- (A) 안티패턴: 범용 상태")
    print(f"보고: {json.dumps(GENERIC_ERROR, ensure_ascii=False)}")
    ans_a = coordinator_next_action(GENERIC_ERROR, "A")
    score_a, hits_a = recovery_score(ans_a)
    print(f"코디네이터: {ans_a}")
    print(f"→ 복구 수단 언급 {score_a}개 {hits_a}")

    print("\n--- (B) 정답: structured error context")
    print(f"보고: errorType={STRUCTURED_ERROR['errorType']}, "
          f"부분결과 {len(STRUCTURED_ERROR['partialResults'])}건, "
          f"대안 {len(STRUCTURED_ERROR['suggestedAlternatives'])}개")
    ans_b = coordinator_next_action(STRUCTURED_ERROR, "B")
    score_b, hits_b = recovery_score(ans_b)
    print(f"코디네이터: {ans_b}")
    print(f"→ 복구 수단 언급 {score_b}개 {hits_b}")

    print()
    print("=" * 60)
    print(f"복구 가능성: (A) {score_a}개 → (B) {score_b}개")
    if score_b > score_a:
        print("→ 구조화 컨텍스트가 코디네이터에게 '판단 재료'를 줬다 (공식 샘플 문제 8의 정답).")
    else:
        print("→ 이번 실행은 차이가 작다(모델·샘플링 변동). 구조는 동일 —")
        print("   (A)는 애초에 재시도할 쿼리도, 쓸 부분 결과도 보고에 없다.")
    print("   확인할 점: (A)에서 코디네이터가 '무엇을' 재시도할지 말할 수 있었나?")

    print(
        "\n교훈: 실패 보고에는 실패 유형·시도한 것·부분 결과·대안을 담는다. "
        "범용 상태는 컨텍스트를 숨기고, 조용한 억제는 복구를 차단하고, 전체 종료는 과잉이다. "
        "서브에이전트는 transient는 로컬 복구하고 해결 불가만 구조화해 전파한다 (Task 5.3)."
    )
