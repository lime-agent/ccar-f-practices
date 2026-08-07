"""D2 실습 — 툴 설명(description)이 툴 선택을 좌우한다 (Task 2.1).

시험 D2 핵심: 툴 설명은 LLM이 어떤 툴을 쓸지 정하는 '1차 메커니즘'.
설명이 부실하거나 유사 툴끼리 겹치면 오선택이 난다.
같은 질문("주문 상태")을 (A) 나쁜 설명 / (B) 좋은 설명 두 툴셋에 던져
모델이 고르는 툴이 어떻게 달라지는지 관찰한다.

주의: (A)/(B)는 툴 '이름'(lookup_order)이 이미 강한 힌트라서 나쁜 설명으로도
정답이 나오곤 한다. 설명만의 효과를 재현성 있게 보려면 (C) 통제 실험을 볼 것.

실행: practices/ 에서  python d2-tools-mcp/tool_descriptions.py
"""
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from shared.bedrock_client import DEFAULT_MODEL, get_client  # noqa: E402

client = get_client()

# (A) 나쁜 설명 — 최소·모호, 유사 툴 구분 안 됨
BAD_TOOLS = [
    {"name": "get_customer", "description": "고객 정보를 가져옵니다.",
     "input_schema": {"type": "object", "properties": {"id": {"type": "string"}}, "required": ["id"]}},
    {"name": "lookup_order", "description": "주문 정보를 가져옵니다.",
     "input_schema": {"type": "object", "properties": {"id": {"type": "string"}}, "required": ["id"]}},
]

# (B) 좋은 설명 — 사용 시점·입력 형식·유사 툴과의 구분 명시
GOOD_TOOLS = [
    {"name": "get_customer",
     "description": "고객을 이메일로 조회·검증한다. 사람(계정) 정보가 필요할 때만 사용. 주문 조회에는 쓰지 말 것(→ lookup_order).",
     "input_schema": {"type": "object", "properties": {"email": {"type": "string"}}, "required": ["email"]}},
    {"name": "lookup_order",
     "description": "주문번호(예: #12345)로 주문 상태를 조회한다. 사용자가 특정 주문을 물을 때 사용. 고객 계정 조회에는 쓰지 말 것(→ get_customer).",
     "input_schema": {"type": "object", "properties": {"order_id": {"type": "string"}}, "required": ["order_id"]}},
]


# (C) 통제 실험 — 툴 이름을 중립화(tool_a/tool_b)해 '이름 힌트'를 제거.
#     남은 변수는 description·input_schema 뿐이라, 설명 품질의 효과가 그대로 드러난다.
NEUTRAL_BAD_TOOLS = [
    {"name": "tool_a", "description": "고객 정보를 가져옵니다.",
     "input_schema": {"type": "object", "properties": {"id": {"type": "string"}}, "required": ["id"]}},
    {"name": "tool_b", "description": "주문 정보를 가져옵니다.",
     "input_schema": {"type": "object", "properties": {"id": {"type": "string"}}, "required": ["id"]}},
]

NEUTRAL_GOOD_TOOLS = [
    {"name": "tool_a",
     "description": "고객을 이메일로 조회·검증한다. 사람(계정) 정보가 필요할 때만 사용. 주문 조회에는 쓰지 말 것(→ tool_b).",
     "input_schema": {"type": "object", "properties": {"email": {"type": "string"}}, "required": ["email"]}},
    {"name": "tool_b",
     "description": "주문번호(예: #12345)로 주문 상태를 조회한다. 사용자가 특정 주문을 물을 때 사용. 고객 계정 조회에는 쓰지 말 것(→ tool_a).",
     "input_schema": {"type": "object", "properties": {"order_id": {"type": "string"}}, "required": ["order_id"]}},
]

# 툴 선택은 확률적이라 1회 실행으로는 판단 불가 — 같은 질문을 여러 번 던져 분포를 본다.
RUNS = 3

# (C)에서 '주문 조회'를 담당하는 툴 = 주문번호 질문의 정답. tool_a 는 고객 조회(=오선택).
NEUTRAL_ORDER_TOOL = "tool_b"


def which_tool(tools, query):
    """tool_choice=any 로 '반드시 툴 선택'하게 하고, 어떤 툴을 골랐는지 반환."""
    resp = client.messages.create(
        model=DEFAULT_MODEL, max_tokens=512, tools=tools,
        tool_choice={"type": "any"},
        messages=[{"role": "user", "content": query}],
    )
    for b in resp.content:
        if b.type == "tool_use":
            return b.name, b.input
    return None, None


def pick_counts(tools, query, runs=RUNS):
    """같은 질문을 runs 회 던져 (선택된 툴, 인자) 분포를 센다. 값이 흩어지면 = 불안정."""
    picks = [which_tool(tools, query) for _ in range(runs)]
    return Counter(f"{name}{args}" for name, args in picks)


def render_counts(counts):
    """중립 이름은 그 자체로 정답 여부를 알 수 없으니 정답/오선택 판정을 붙여 출력."""
    return " | ".join(
        f"{'OK  정답(주문)' if pick.startswith(NEUTRAL_ORDER_TOOL) else 'NG  오선택(고객)'} {pick} ×{n}"
        for pick, n in counts.most_common()
    )


if __name__ == "__main__":
    q = "주문 #12345 상태 확인해줘"
    print(f"질문: {q}\n")
    print("(A) 나쁜 설명 →", which_tool(BAD_TOOLS, q))
    print("     ← 이름 'lookup_order' 가 정답을 흘려주므로 맞힐 수도 있음(설명은 근거를 못 줌)")
    print("(B) 좋은 설명 →", which_tool(GOOD_TOOLS, q))
    print("     ← 같은 정답이라도 인자 이름이 order_id: 받는 코드가 '주문번호'임을 알 수 있음")

    # (C) 이름 힌트 제거 + 모호한 질문("주문"이라는 단어 없음) → 설명 품질만으로 승부
    ambiguous_q = "12345 확인해줘"
    print(f"\n(C) 통제 실험 — tool_a=고객 조회 / tool_b=주문 조회(정답), 질문: {ambiguous_q!r}, {RUNS}회")
    print("  나쁜 설명 →", render_counts(pick_counts(NEUTRAL_BAD_TOOLS, ambiguous_q)))
    print("  좋은 설명 →", render_counts(pick_counts(NEUTRAL_GOOD_TOOLS, ambiguous_q)))
    print("     ← 같은 모델·같은 질문인데 툴셋만 바꿔서 정반대 툴을 고른다면 그게 설명의 효과.")
    print("     ← 나쁜 설명이 3/3 일관되게 틀리는 것은 '흔들림'보다 나쁨(근거 없이 확신 → 재시도해도 그대로).")

    print("\n교훈: 툴 선택 문제는 few-shot·라우터보다 '툴 설명 개선'이 1순위 (Task 2.1).")
