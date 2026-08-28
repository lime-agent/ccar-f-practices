"""D5 실습 — 에스컬레이션 기준 명시의 효과 (Task 5.2 / Ch16.1).

시험 D5 핵심(공식 샘플 문제 3): 에스컬레이션 보정이 틀어졌을 때
가장 효과적인 처방은 **시스템 프롬프트에 명시적 기준 + few-shot** 이다.
- 유효 트리거: 고객의 사람 명시 요청 · 정책 예외/공백 · 진전 불가
- 무효 트리거: 단지 복잡해 보임 · confidence 낮음 · 고객이 화나 보임(감정)
  → 감정·자기 보고 confidence는 **실제 케이스 복잡도의 신뢰할 수 없는 프록시**.

이 데모는 4개 케이스를 두 조건으로 분류해 정확도를 비교한다:
  (A) 기준 없음 — "적절히 판단하라"(모호한 지시)
  (B) 명시적 기준 + few-shot (D4 12.1 패턴 그대로)
판정은 우리 코드가 한다(기대 정답과 대조). enum 스키마로 출력 형식을 고정한다.

실행: practices/ 에서  python d5-context-reliability/escalation_prompt.py
"""
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from shared.bedrock_client import DEFAULT_MODEL, get_client  # noqa: E402

client = get_client()

# tool_use + enum 으로 판단 결과의 '모양'을 고정한다 (D4 13.1 — 형식은 스키마가 책임)
DECIDE_TOOL = [{
    "name": "decide_escalation",
    "description": "고객 문의에 대해 에스컬레이션 여부를 판단한다.",
    "input_schema": {
        "type": "object",
        "properties": {
            "decision": {
                "type": "string",
                "enum": ["escalate", "resolve"],
                "description": "escalate=사람 상담원에게 넘김 / resolve=에이전트가 직접 처리",
            },
            "reason": {"type": "string", "description": "판단 근거 한 문장"},
        },
        "required": ["decision", "reason"],
    },
}]

# 4개 케이스 — 유효/무효 트리거를 골고루 섞었다. expected 는 시험 기준 정답.
CASES = [
    {
        "id": "①명시적 사람 요청",
        "text": "이 문제 정말 지겨워요. 제발 사람 좀 연결해주세요.",
        "expected": "escalate",
        "why": "고객이 명시적으로 사람 연결을 요청 → 조사 시도 없이 즉시 존중",
    },
    {
        "id": "②감정만 표현",
        "text": "배송이 너무 늦었어요! 진짜 화가 나네요! 어떻게 할 거예요?",
        "expected": "resolve",
        "why": "감정 표현은 있으나 사람 요청 없음 + 이슈가 역량 내 → 불만 인정 후 해결 제안",
    },
    {
        "id": "③정책 공백",
        "text": "타사 쇼핑몰이 더 싼데 그 가격으로 맞춰주실 수 있나요?",
        "expected": "escalate",
        "why": "정책은 자사 가격 조정만 다룸 → 정책이 침묵하는 영역(정책 공백)",
    },
    {
        "id": "④표준 손상 교체",
        "text": "받은 컵이 깨져서 왔어요. 사진 첨부합니다. 교환해주세요.",
        "expected": "resolve",
        "why": "사진 증거 있는 표준 손상 교체 → 정책 내 자율 처리 가능",
    },
]

# (A) 모호한 지시 — 기준이 없으면 모델이 실행마다 다르게 해석한다
VAGUE_SYSTEM = (
    "너는 고객 지원 에이전트다. 문의를 보고 적절히 판단해서 "
    "필요하면 사람 상담원에게 에스컬레이션하라."
)

# (B) 명시적 기준 + few-shot — 공식 샘플 문제 3의 정답 처방
EXPLICIT_SYSTEM = """너는 고객 지원 에이전트다. 아래 기준에 따라 에스컬레이션 여부를 판단하라.

## 에스컬레이션하는 경우 (escalate)
- 고객이 "사람 연결", "상담원", "매니저" 등을 명시적으로 요청
- 정책이 다루지 않는 예외/공백 (예: 우리 정책은 자사 이전 가격 매칭만 다루는데 타사 가격 매칭 요구)
- 의미 있는 진전이 불가능
- 법적 조치·언론 제보 언급

## 에스컬레이션하지 않는 경우 (resolve)
- 표준 손상 교체·환불 (증거 있음)
- 일반 배송 지연 보상
- 계정 정보 수정
- ⚠️ 다음은 에스컬레이션 근거가 아니다: 단지 복잡해 보임 / 스스로 확신이 낮음 /
  고객이 화나 보임(감정). 감정과 자기 확신은 실제 케이스 복잡도의 신뢰할 수 없는 프록시다.

## Few-Shot 예시
예시 1) 고객: "이 문제 지겨워요, 사람 연결해주세요." → escalate
        이유: 명시적 사람 연결 요청. 조사 시도 없이 즉시 존중.
예시 2) 고객: "배송이 늦어서 화가 나요!" → resolve
        이유: 감정 표현뿐, 사람 요청 없음. 사과 후 해결 제안. 고객이 재차 요구하면 그때 에스컬레이션.
예시 3) 고객: "타사가 더 싼데 맞춰주세요." → escalate
        이유: 정책이 자사 조정만 다뤄 침묵하는 영역(정책 공백).
"""

RUNS = 2  # 케이스당 반복 — 판단 흔들림을 보기 위해


def decide(system_prompt: str, text: str) -> tuple[str, str]:
    resp = client.messages.create(
        model=DEFAULT_MODEL,
        max_tokens=300,
        tools=DECIDE_TOOL,
        tool_choice={"type": "tool", "name": "decide_escalation"},
        system=system_prompt,
        messages=[{"role": "user", "content": text}],
    )
    for block in resp.content:
        if block.type == "tool_use":
            return block.input.get("decision", "?"), block.input.get("reason", "")
    return "?", ""


def run_condition(label: str, system_prompt: str) -> int:
    print(f"\n--- {label}")
    correct = 0
    for case in CASES:
        votes = Counter()
        last_reason = ""
        for _ in range(RUNS):
            decision, reason = decide(system_prompt, case["text"])
            votes[decision] += 1
            last_reason = reason
        hit = votes[case["expected"]]
        correct += hit
        mark = "○" if hit == RUNS else ("△" if hit else "✗")
        print(f"  {mark} {case['id']}: {dict(votes)} (기대={case['expected']}, {hit}/{RUNS})")
        print(f"      모델 근거: {last_reason[:110]}")
    total = len(CASES) * RUNS
    print(f"  → 정확도 {correct}/{total} ({correct / total:.0%})")
    return correct


if __name__ == "__main__":
    print("=" * 60)
    print("[기준 정답] 시험 기준으로 각 케이스가 왜 그 답인지")
    for case in CASES:
        print(f"  {case['id']} → {case['expected']}: {case['why']}")

    print()
    print("=" * 60)
    print(f"[조건 비교] 케이스 {len(CASES)}개 × {RUNS}회")
    score_a = run_condition("(A) 기준 없음 — '적절히 판단하라'", VAGUE_SYSTEM)
    score_b = run_condition("(B) 명시적 기준 + few-shot", EXPLICIT_SYSTEM)

    print()
    print("=" * 60)
    total = len(CASES) * RUNS
    print(f"정확도: (A) {score_a}/{total} → (B) {score_b}/{total}")
    if score_b > score_a:
        print("→ 명시적 기준 + few-shot이 에스컬레이션 보정을 개선했다 (공식 샘플 문제 3의 정답 처방).")
    elif score_a == total:
        print("→ 이번 실행은 (A)도 다 맞았다. 케이스가 모델에게 쉬웠던 것 —")
        print("   시험 포인트는 점수 우열이 아니라 '기준을 프롬프트에 박는다'는 처방 자체.")
    else:
        print("→ 이번 실행에선 차이가 뚜렷하지 않음(모델·샘플링 변동). 구조적 원칙은 동일.")
    print("   특히 ②(감정만 표현)와 ③(정책 공백)에서 갈리는지 보라 — 시험 함정이 그 두 개다.")

    print(
        "\n교훈: 에스컬레이션 트리거는 '사람 명시 요청 · 정책 공백 · 진전 불가'이며, "
        "'감정·낮은 confidence'는 트리거가 아니다. 처방은 인프라 추가(분류기·감정분석)가 아니라 "
        "시스템 프롬프트의 명시적 기준 + few-shot이다 (Task 5.2, 공식 샘플 문제 3)."
    )
