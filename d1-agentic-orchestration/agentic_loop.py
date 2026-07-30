"""D1 실습 시드 — 기본 에이전틱 루프 (AnthropicBedrock).

anthropic SDK(`AnthropicBedrock`)로 작성 → 시험 예제와 동일 문법
(`client.messages.create` / `resp.stop_reason` / `tool_use`).

핵심 학습 포인트(시험 D1): stop_reason 기반 루프 제어.
  - "tool_use"  → 툴 실행 후 대화에 결과를 넣고 계속
  - "end_turn"  → 정상 종료
안티패턴(시험 함정): 텍스트 키워드나 '고정 횟수'로 완료를 판단하는 것.
  아래 max_turns 는 '완료 판단'이 아니라 무한루프 방지용 안전 상한일 뿐이다.

사전: shared/.env 채우고 verify_bedrock.sh 통과 후 실행.
실행: practices/ 디렉토리에서  python d1-agentic-orchestration/agentic_loop.py
"""
import json
import os
import sys

# practices/ 를 import 경로에 추가 (shared 패키지 사용)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from shared.bedrock_client import DEFAULT_MODEL, get_client  # noqa: E402

client = get_client()


def execute_tool(name, tool_input):
    """실습용 더미 툴 — 실제 로직으로 교체해가며 학습."""
    if name == "get_weather":
        return {"city": tool_input.get("city"), "temp_c": 27, "sky": "맑음"}
    return {"error": f"unknown tool: {name}"}


TOOLS = [
    {
        "name": "get_weather",
        "description": "도시의 현재 날씨를 조회한다. 사용자가 특정 도시의 날씨를 물을 때 사용.",
        "input_schema": {
            "type": "object",
            "properties": {"city": {"type": "string", "description": "도시 이름"}},
            "required": ["city"],
        },
    }
]


def run_agent(user_message, max_turns=8):
    messages = [{"role": "user", "content": user_message}]

    for _ in range(max_turns):  # 안전 상한 (완료 판단 아님)
        resp = client.messages.create(
            model=DEFAULT_MODEL,
            max_tokens=1024,
            tools=TOOLS,
            messages=messages,
        )

        if resp.stop_reason == "end_turn":  # ✅ 모델이 완료 신호
            return "".join(b.text for b in resp.content if b.type == "text")

        if resp.stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": resp.content})  # 모델 요청 기록
            tool_results = []
            for block in resp.content:
                if block.type == "tool_use":
                    result = execute_tool(block.name, block.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,          # 어느 요청에 대한 답인지 짝지음
                        "content": json.dumps(result, ensure_ascii=False),
                    })
            messages.append({"role": "user", "content": tool_results})
            continue  # 다음 턴(모델 재호출)으로 — 아래 break 로 새지 않도록

        break  # end_turn/tool_use 외(max_tokens 등)

    return "예기치 않은 종료 (max_turns 도달 또는 처리하지 않은 stop_reason)"


if __name__ == "__main__":
    print(run_agent("서울 날씨 알려주고, 우산 챙길지 한 줄로 조언해줘."))
