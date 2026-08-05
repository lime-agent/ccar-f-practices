"""D2 실습 — 툴 설명(description)이 툴 선택을 좌우한다 (Task 2.1).

시험 D2 핵심: 툴 설명은 LLM이 어떤 툴을 쓸지 정하는 '1차 메커니즘'.
설명이 부실하거나 유사 툴끼리 겹치면 오선택이 난다.
같은 질문("주문 상태")을 (A) 나쁜 설명 / (B) 좋은 설명 두 툴셋에 던져
모델이 고르는 툴이 어떻게 달라지는지 관찰한다.

실행: practices/ 에서  python d2-tools-mcp/tool_descriptions.py
"""
import os
import sys

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


if __name__ == "__main__":
    q = "주문 #12345 상태 확인해줘"
    print(f"질문: {q}\n")
    print("(A) 나쁜 설명 →", which_tool(BAD_TOOLS, q), "  ← get_customer 로 오선택되기 쉬움")
    print("(B) 좋은 설명 →", which_tool(GOOD_TOOLS, q), "  ← lookup_order 로 올바르게")
    print("\n교훈: 툴 선택 문제는 few-shot·라우터보다 '툴 설명 개선'이 1순위 (Task 2.1).")
