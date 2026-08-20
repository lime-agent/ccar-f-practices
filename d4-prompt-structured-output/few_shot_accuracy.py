"""D4 실습 — 신뢰성 사다리의 첫 두 칸: 명시적 기준(12.1) → few-shot(12.2).

시험 D4 핵심:
  12.1 명시적 기준 — "보수적으로" 같은 모호한 지시 대신, 판단 기준을 문장으로 못박는다.
  12.2 few-shot   — 2~4개, 서로 다른 케이스(edge case·출력 형식 다양성)를 보여줄 때 가장 효과적.
few-shot의 진짜 역할은 "정답 예시 나열"이 아니라 "기준을 예시로도 못박는 것" — 그래서
아래는 세 조건(① 지시 없음 → ② 기준 문장만 → ③ 기준+예시)을 나란히 비교해, 12.1과 12.2가
각각 얼마나 기여하는지 분리해서 본다.

과제: 고객 문의를 (urgent / normal / spam) 3종으로 분류한다. 모호한 입력 하나를
①②③ 조건 각각 여러 번 실행해 분포·정답률을 비교한다.

주의: 모델·샘플링에 따라 이번 실행에서 사다리가 깔끔하게 안 나올 수 있다 — 핵심은
"명시적 기준·few-shot 각각이 판단 기준을 못박는 수단"이라는 원칙.

실행: practice/ 에서  python d4-prompt-structured-output/few_shot_accuracy.py
"""
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from shared.bedrock_client import DEFAULT_MODEL, get_client  # noqa: E402

client = get_client()

CLASSIFY_TOOL = [{
    "name": "classify_ticket",
    "description": "고객 문의를 urgent/normal/spam 중 하나로 분류한다.",
    "input_schema": {
        "type": "object",
        "properties": {"category": {"type": "string", "enum": ["urgent", "normal", "spam"]}},
        "required": ["category"],
    },
}]

BASE_SYSTEM = "당신은 고객 문의 분류 담당자입니다."

# 모호한 입력: 화가 났지만 서비스 중단 언급은 없음 — urgent인지 normal인지 애매
AMBIGUOUS_TICKET = "이거 두 번째로 말하는 건데 왜 아직도 답이 없어요? 진짜 너무하네요."

# "정답": 서비스 중단 언급이 없으므로, 아래 기준("서비스 중단 여부")상 정답은 normal.
# (감정이 격하다는 이유만으로 urgent로 분류하면, 일관되더라도 기준에는 안 맞는 것)
EXPECTED_CATEGORY = "normal"

# 12.1 명시적 기준 — 예시 없이 판단 기준 문장만. FEW_SHOT_EXAMPLES 에도 그대로 재사용해
# "기준 문장은 동일하게 유지한 채 예시만 추가했을 때"를 깨끗하게 비교한다.
CRITERION = "분류 기준: '서비스가 실제로 중단·차단됐는지'가 urgent 여부를 가른다. 단순히 답이 늦어 화난 것은 normal."

# 12.2 few-shot 예시 2개(서로 다른 케이스: urgent 1 · normal 1) + 위 기준을 함께 제공
FEW_SHOT_EXAMPLES = f"""
예시 1: "서버가 다운돼서 결제가 전혀 안 됩니다. 지금 당장 도와주세요!" → urgent (서비스 중단·긴급성 명시)
예시 2: "재문의 드립니다만 답이 늦어 답답합니다. 확인 부탁드려요." → normal (감정 표현은 있지만 서비스 중단 없음, 반복 재문의는 정상 응대 범위)

{CRITERION}
"""

RUNS = 5


def classify(system_prompt, text):
    resp = client.messages.create(
        model=DEFAULT_MODEL, max_tokens=256, tools=CLASSIFY_TOOL,
        tool_choice={"type": "tool", "name": "classify_ticket"},
        system=system_prompt,
        messages=[{"role": "user", "content": text}],
    )
    for b in resp.content:
        if b.type == "tool_use":
            return b.input.get("category")
    return None


def distribution(system_prompt, text, runs=RUNS):
    return Counter(classify(system_prompt, text) for _ in range(runs))


def match_rate(counter, expected=EXPECTED_CATEGORY, runs=RUNS):
    return counter.get(expected, 0) / runs


if __name__ == "__main__":
    print(f"모호한 문의: {AMBIGUOUS_TICKET!r}")
    print(f"(기준상 정답: 서비스 중단 언급 없음 → '{EXPECTED_CATEGORY}')\n")

    zero_shot = distribution(BASE_SYSTEM, AMBIGUOUS_TICKET)
    zero_match = match_rate(zero_shot)
    print(f"① 0-shot — 지시 없음 ({RUNS}회) → {dict(zero_shot)}  (정답률 {zero_match:.0%})")

    criterion_only = distribution(f"{BASE_SYSTEM}\n{CRITERION}", AMBIGUOUS_TICKET)
    criterion_match = match_rate(criterion_only)
    print(f"② 명시적 기준만(12.1, 예시 없음, {RUNS}회) → {dict(criterion_only)}  (정답률 {criterion_match:.0%})")

    few_shot = distribution(f"{BASE_SYSTEM}\n{FEW_SHOT_EXAMPLES}", AMBIGUOUS_TICKET)
    few_match = match_rate(few_shot)
    print(f"③ 기준+few-shot 예시 2개(12.1+12.2, {RUNS}회) → {dict(few_shot)}  (정답률 {few_match:.0%})")

    print(f"\n정답률 흐름: ① {zero_match:.0%} → ② {criterion_match:.0%} → ③ {few_match:.0%}")
    if criterion_match >= zero_match and few_match >= criterion_match:
        print("→ 신뢰성 사다리가 그대로 보임: 지시 없음 ≤ 기준만 ≤ 기준+예시 (단조 개선)")
    elif criterion_match >= zero_match:
        print("→ 명시적 기준 한 문장만으로 이미 개선됨 — 이번 실행에서 예시(few-shot)의 추가 기여는 뚜렷하지 않음")
    else:
        print("→ 이번 실행에서는 뚜렷한 사다리 패턴이 안 보임(모델·샘플링에 따라 변동)")

    print(
        "\n교훈: ① 모호한 지시 → ② 명시적 기준(12.1)만으로도 개선 가능 → ③ 서로 다른 케이스의 "
        "few-shot(12.2)을 더하면 판단 기준이 예시로도 못박힘 — 이게 '신뢰성 사다리'의 첫 두 칸이다 (Ch12, 샘플 33)."
    )
