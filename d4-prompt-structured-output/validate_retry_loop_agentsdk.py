"""D4 실습 (Tier 2, Claude Agent SDK) — 스키마 검증-재시도 루프 (Ch13.3).

validate_retry_loop.py 의 Agent SDK 버전.
Tier1은 우리가 while 루프를 직접 돌며 tool_result(is_error)를 만들어 넣었지만,
여기서는 검증 로직을 커스텀 MCP 툴 안에 넣고 에이전트의 **내장 루프**가
is_error 응답을 보고 스스로 재시도하게 한다.

Ch13.3 핵심을 SDK에 옮긴 방법:
  - RETRYABLE(범위 오류)만 is_error=True → 에이전트가 재시도.
  - NOT_RETRYABLE(본문 부재·환각)은 is_error=False로 에스컬레이션 → 재시도를 유도하지 않음.
    (is_error=True를 주면 에이전트가 없는 정보를 찾으려 루프를 낭비한다.)

준비(Tier 2): npm i -g @anthropic-ai/claude-code · pip install claude-agent-sdk + Bedrock env
실행: practice/ 에서  python d4-prompt-structured-output/validate_retry_loop_agentsdk.py
"""
import os
import re
import sys

import anyio
from claude_agent_sdk import ClaudeAgentOptions, create_sdk_mcp_server, query, tool

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from shared.agent_sdk_config import bedrock_agent_env  # noqa: E402

TRICKY_TEXT = "저희 할머니는 마을에서 300살 먹은 나무보다 오래 사신 것처럼 느껴지지만, 실제로는 45세이십니다."
NO_AGE_TEXT = "저희 할머니는 최근에 이사를 하셨고, 요즘은 정원 가꾸기에 재미를 붙이셨습니다."

# query() 직전에 채운다. 툴이 원문 grounding을 하려면 추출 대상 문장이 필요함.
_source = {"text": ""}


def age_in_source(age, text):
    if not isinstance(age, int):
        return False
    return re.search(rf"(?<!\d){age}(?!\d)", text) is not None


EXTRACT_AGE_SCHEMA = {
    "type": "object",
    "properties": {
        "age": {"type": ["integer", "null"]},
        "found": {"type": "boolean", "description": "본문에 실제 나이가 명시돼 있었는지"},
    },
    "required": ["age", "found"],
}


@tool(
    "extract_age",
    "텍스트에서 사람의 실제 나이를 기록한다. "
    "본문에 있으면 found=true와 정수 age, 없으면 found=false와 age=null (추측 금지).",
    EXTRACT_AGE_SCHEMA,
)
async def extract_age(args):
    age = args.get("age")
    found = args.get("found")
    text = _source["text"]

    if not found or age is None:
        # NOT_RETRYABLE: 에러로 안 돌려야 에이전트가 재시도 루프를 안 돈다
        return {"content": [{"type": "text", "text":
            "ESCALATE: 본문에 실제 나이 정보가 없습니다. "
            "이 툴을 다시 호출하지 말고 사람에게 에스컬레이션하세요."}]}
    if not age_in_source(age, text):
        return {"content": [{"type": "text", "text":
            f"ESCALATE: age={age!r}는 본문에 없는 숫자입니다(환각). "
            "재시도해도 없는 정보는 생기지 않습니다. 툴을 다시 호출하지 마세요."}]}
    if not isinstance(age, int) or not (0 <= age <= 120):
        return {
            "content": [{"type": "text", "text":
                f"RETRYABLE: age={age!r}는 유효하지 않습니다. 사람 나이는 0~120 사이 정수여야 합니다. "
                "과장된 숫자(예: '300살 먹은 나무')는 실제 나이가 아닙니다. "
                "본문에서 실제 사람 나이를 다시 찾아 정수로 반환하세요."}],
            "is_error": True,
        }
    return {"content": [{"type": "text", "text": f"기록 완료: age={age}"}]}


age_server = create_sdk_mcp_server(name="ages", version="1.0.0", tools=[extract_age])

options = ClaudeAgentOptions(
    mcp_servers={"ages": age_server},
    allowed_tools=["mcp__ages__extract_age"],
    permission_mode="acceptEdits",
    setting_sources=[],
    thinking={"type": "disabled"},
    env=bedrock_agent_env(),
)


async def run_case(title, text):
    print(f"\n{title}")
    print(f"문장: {text}")
    _source["text"] = text
    async for msg in query(
        prompt=(
            f"다음 문장에서 사람의 실제 나이를 extract_age 툴로 기록해줘. "
            f"본문에 없으면 found=false, age=null (추측 금지): {text}"
        ),
        options=options,
    ):
        print(msg)


async def main():
    await run_case("[케이스 1] RETRYABLE — 범위 오류면 is_error로 재시도", TRICKY_TEXT)
    await run_case("[케이스 2] NOT_RETRYABLE — 부재/환각은 ESCALATE (is_error 아님)", NO_AGE_TEXT)


if __name__ == "__main__":
    anyio.run(main)
