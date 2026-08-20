"""D4 실습 — few-shot 예시 2~4개로 정확도·일관성 개선을 관찰 (Ch12, 샘플 33).

시험 D4 핵심: few-shot은 **2~4개, 서로 다른 케이스**(edge case·출력 형식 다양성)를 보여줄 때
가장 효과적이다. 모호한 입력에서 0-shot은 판단이 흔들리기 쉽고, few-shot은
"어떤 기준으로 분류하는지"를 예시로 못박아 일관성을 높인다.

과제: 고객 문의를 (urgent / normal / spam) 3종으로 분류한다. 모호한 입력 하나를
0-shot과 few-shot(서로 다른 케이스 2개) 각각 여러 번 실행해 분포를 비교한다.

주의: 모델·샘플링에 따라 이번 실행에서 차이가 뚜렷하지 않을 수 있다 — 핵심은
"few-shot 예시가 정답 나열이 아니라 분류 기준을 못박는 것"이라는 원칙.

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

# 모호한 입력: 화가 났지만 서비스 중단 언급은 없음 — urgent인지 normal인지 애매
AMBIGUOUS_TICKET = "이거 두 번째로 말하는 건데 왜 아직도 답이 없어요? 진짜 너무하네요."

# "정답": 서비스 중단 언급이 없으므로, few-shot이 못박는 기준("서비스 중단 여부")상 정답은 normal.
# (감정이 격하다는 이유만으로 urgent로 분류하면, 일관되더라도 기준에는 안 맞는 것)
EXPECTED_CATEGORY = "normal"

# few-shot 예시 2개 — 서로 다른 케이스(urgent 1 · normal 1)로 분류 기준을 못박음
FEW_SHOT_EXAMPLES = """
예시 1: "서버가 다운돼서 결제가 전혀 안 됩니다. 지금 당장 도와주세요!" → urgent (서비스 중단·긴급성 명시)
예시 2: "재문의 드립니다만 답이 늦어 답답합니다. 확인 부탁드려요." → normal (감정 표현은 있지만 서비스 중단 없음, 반복 재문의는 정상 응대 범위)

분류 기준: '서비스가 실제로 중단·차단됐는지'가 urgent 여부를 가른다. 단순히 답이 늦어 화난 것은 normal.
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


if __name__ == "__main__":
    print(f"모호한 문의: {AMBIGUOUS_TICKET!r}")
    print(f"(기준상 정답: 서비스 중단 언급 없음 → '{EXPECTED_CATEGORY}')\n")

    zero_shot = distribution("당신은 고객 문의 분류 담당자입니다.", AMBIGUOUS_TICKET)
    zero_match = zero_shot.get(EXPECTED_CATEGORY, 0) / RUNS
    print(f"0-shot ({RUNS}회) → {dict(zero_shot)}  (정답률 {zero_match:.0%})")

    few_shot = distribution(
        f"당신은 고객 문의 분류 담당자입니다.\n{FEW_SHOT_EXAMPLES}", AMBIGUOUS_TICKET
    )
    few_match = few_shot.get(EXPECTED_CATEGORY, 0) / RUNS
    print(f"few-shot 2개 ({RUNS}회) → {dict(few_shot)}  (정답률 {few_match:.0%})")

    print(f"\n분포 폭: 0-shot {len(zero_shot)}종 vs few-shot {len(few_shot)}종")
    if few_match > zero_match:
        # 폭(종류 수)이 같아도(둘 다 완전 일관) 정답률로 가르는 경우를 놓치지 않는다 —
        # "일관성 ≠ 정확성"이 이 실습의 진짜 핵심일 수 있다.
        print("→ few-shot이 '기준에 맞는 정답'에 더 잘 수렴함 — 일관성만으론 부족, 정확성도 봐야 함")
    elif len(few_shot) < len(zero_shot):
        print("→ few-shot이 분포를 더 좁게(일관되게) 만듦")
    else:
        print("→ 이번 실행에서는 차이가 뚜렷하지 않음(모델·샘플링에 따라 변동)")

    print(
        "\n교훈: few-shot은 '정답 예시 나열'이 아니라 "
        "'서로 다른 케이스로 분류 기준을 못박는 것'이 핵심 — 2~4개가 적정선 (Ch12, 샘플 33)."
    )
