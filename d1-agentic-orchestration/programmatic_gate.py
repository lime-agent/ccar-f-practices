"""D1 실습 — 프로그래밍적 강제 (게이트 패턴).

시험 D1 / 공식 샘플 Q1의 핵심:
  critical 로직(예: 환불 전 고객 검증)은 **프롬프트가 아니라 '코드 게이트'로 강제**한다.
  프롬프트 지시는 확률적이라 "12% 케이스에서 고객확인을 건너뜀" 같은 실패가 난다.
  → 정답은 few-shot·프롬프트 강화가 아니라 '선행조건 게이트'.

이 파일은 execute_tool 안에서 선행조건을 코드로 강제한다:
  게이트1) get_customer 로 검증된 customer_id 나오기 전엔 process_refund 차단
  게이트2) $500 초과 환불 차단 (business rule)
모델이 순서를 어기려 해도 코드가 구조화된 에러를 돌려주어 '결정론적으로' 막힌다.

참고: 이건 우리가 짠 execute_tool 안의 '인라인 강제'(Tier 1)다 — 시험이 말하는 '진짜 hooks'
(PreToolUse/PostToolUse)는 아니다. 목적(코드로 강제)은 같고, 훅 버전은 hooks_demo_agentsdk.py 참고.

실행: practices/ 에서  python d1-agentic-orchestration/programmatic_gate.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from shared.bedrock_client import DEFAULT_MODEL, get_client  # noqa: E402

client = get_client()

REFUND_LIMIT = 500  # $500 초과는 수동 승인


class State:
    """대화 동안 유지되는 상태 — 게이트 판단의 근거."""
    def __init__(self):
        self.verified_customer_id = None


def execute_tool(state, name, tool_input):
    # --- 게이트(코드 강제) : 실제 툴 실행 전에 선행조건·정책을 검사 ---
    if name == "process_refund":
        if state.verified_customer_id is None:                      # 게이트1: 선행조건
            return {"isError": True, "errorCategory": "validation", "isRetryable": False,
                    "message": "먼저 get_customer로 고객을 검증해야 합니다."}
        if tool_input.get("amount", 0) > REFUND_LIMIT:              # 게이트2: business rule
            return {"isError": True, "errorCategory": "business", "isRetryable": False,
                    "message": f"${REFUND_LIMIT} 초과 환불은 수동 승인이 필요합니다."}

    # --- 실제 툴 실행 ---
    if name == "get_customer":
        cid = f"CUST-{abs(hash(tool_input.get('email', ''))) % 10000:04d}"
        state.verified_customer_id = cid                            # 검증 성공 → 게이트 열림
        return {"customer_id": cid, "name": tool_input.get("name", "고객"), "status": "active"}
    if name == "process_refund":
        return {"ok": True, "customer_id": state.verified_customer_id, "amount": tool_input.get("amount")}
    return {"error": f"unknown tool: {name}"}


TOOLS = [
    {"name": "get_customer",
     "description": "이메일로 고객을 조회·검증한다. 환불 등 계정 작업 전에 반드시 먼저 호출.",
     "input_schema": {"type": "object",
                      "properties": {"email": {"type": "string"}, "name": {"type": "string"}},
                      "required": ["email"]}},
    {"name": "process_refund",
     "description": "검증된 고객에게 환불을 처리한다.",
     "input_schema": {"type": "object",
                      "properties": {"amount": {"type": "number", "description": "환불 금액(USD)"}},
                      "required": ["amount"]}},
]


def run_agent(user_message, max_turns=8):
    state = State()
    messages = [{"role": "user", "content": user_message}]
    for _ in range(max_turns):
        resp = client.messages.create(model=DEFAULT_MODEL, max_tokens=1024, tools=TOOLS, messages=messages)
        if resp.stop_reason == "end_turn":
            return "".join(b.text for b in resp.content if b.type == "text")
        if resp.stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": resp.content})
            results = []
            for b in resp.content:
                if b.type == "tool_use":
                    out = execute_tool(state, b.name, b.input)
                    flag = "⛔차단" if out.get("isError") else "✅허용"
                    print(f"  [tool] {b.name}({b.input}) → {flag}: {out.get('message', out)}")
                    results.append({"type": "tool_result", "tool_use_id": b.id,
                                    "content": json.dumps(out, ensure_ascii=False)})
            messages.append({"role": "user", "content": results})
            continue
        break
    return "예기치 않은 종료"


if __name__ == "__main__":
    # Part A — 모델 없이 '게이트가 코드'임을 증명 (모델 행동과 무관하게 결정론적)
    print("=== Part A: 게이트 단위 증명 (모델 없음) ===")
    s = State()
    print(" 환불 먼저 시도:", execute_tool(s, "process_refund", {"amount": 30}))   # 검증 전 → 차단
    print(" 고객 검증:", execute_tool(s, "get_customer", {"email": "a@b.com"}))     # 게이트 열림
    print(" 환불 재시도:", execute_tool(s, "process_refund", {"amount": 30}))       # 이제 허용
    print(" 한도 초과 환불:", execute_tool(s, "process_refund", {"amount": 800}))   # business 게이트 차단

    # Part B — 에이전트 실행 (모델이 순서를 어기려 해도 게이트가 강제)
    print("\n=== Part B: 에이전트 실행 ===")
    print(run_agent("고객 이메일 hong@example.com. 25달러 환불해줘."))
