"""D2 실습 — tool_choice 3가지 (Task 2.3).

시험 D2 핵심: tool_choice 로 모델의 툴 사용을 제어한다.
  - "auto"                       : 모델이 알아서 (필요 없으면 그냥 텍스트로 답)
  - "any"                        : 반드시 '어떤' 툴이든 하나 호출
  - {"type":"tool","name":...}   : 특정 툴 강제

'툴이 필요 없는' 질문을 던져 세 모드의 차이를 극명하게 본다:
  auto → 텍스트만(end_turn) / any → 굳이 툴 호출(tool_use) / forced → 지정 툴 호출

실행: practices/ 에서  python d2-tools-mcp/tool_choice_demo.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from shared.bedrock_client import DEFAULT_MODEL, get_client  # noqa: E402

client = get_client()

TOOLS = [{
    "name": "get_weather",
    "description": "도시의 현재 날씨를 조회한다.",
    "input_schema": {"type": "object", "properties": {"city": {"type": "string"}}, "required": ["city"]},
}]

# 일부러 날씨가 필요 없는 질문 → 모드 차이가 드러남
QUERY = "그냥 반갑게 한 줄 인사만 해줘. 날씨는 안 궁금해."


def run(label, tool_choice):
    resp = client.messages.create(
        model=DEFAULT_MODEL, max_tokens=256, tools=TOOLS,
        tool_choice=tool_choice,
        messages=[{"role": "user", "content": QUERY}],
    )
    called = [b.name for b in resp.content if b.type == "tool_use"]
    text = "".join(b.text for b in resp.content if b.type == "text")
    print(f"[{label:16}] stop_reason={resp.stop_reason:9} 툴호출={called or '없음'}  텍스트={text[:40]!r}")


if __name__ == "__main__":
    print(f"질문(툴 불필요): {QUERY}\n")
    run("auto", {"type": "auto"})
    run("any", {"type": "any"})
    run("forced weather", {"type": "tool", "name": "get_weather"})
    print("\n교훈: auto=자율 / any=반드시 툴 / forced=특정 툴 강제. "
          "구조화 출력 보장이 필요하면 any 나 forced 로 툴 사용을 강제 (Task 2.3).")
