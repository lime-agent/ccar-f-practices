"""D4 실습 (Tier 2, Claude Agent SDK) — 스키마 검증-재시도 루프 (Ch13).

validate_retry_loop.py 의 Agent SDK 버전.
Tier1은 우리가 while 루프를 직접 돌며 tool_result(is_error)를 만들어 넣었지만,
여기서는 검증 로직을 커스텀 MCP 툴 안에 넣고 에이전트의 **내장 루프**가
is_error 응답을 보고 스스로 재시도하게 한다 — 사람이 짠 재시도 루프가 필요 없다.
(D2 structured_tool_errors_agentsdk.py 와 같은 패턴 — 여긴 검증 실패가
"몇 번째 시도인지"가 아니라 "값이 실제로 유효한지"에 달려 있다는 점이 다르다.)

준비(Tier 2): npm i -g @anthropic-ai/claude-code · pip install claude-agent-sdk + Bedrock env
실행: practices/ 에서  python d4-prompt-structured-output/validate_retry_loop_agentsdk.py
"""
import os
import sys

import anyio
from claude_agent_sdk import ClaudeAgentOptions, create_sdk_mcp_server, query, tool

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from shared.agent_sdk_config import bedrock_agent_env  # noqa: E402

# 일부러 헷갈리게: "300살"이라는 과장 표현과 실제 나이(45)가 같은 문장에 있음
TRICKY_TEXT = "저희 할머니는 마을에서 300살 먹은 나무보다 오래 사신 것처럼 느껴지지만, 실제로는 45세이십니다."


@tool("extract_age", "추출한 사람의 나이(정수)를 기록한다. 0~120 범위의 실제 사람 나이만 유효.", {"age": int})
async def extract_age(args):
    age = args["age"]
    if not isinstance(age, int) or not (0 <= age <= 120):
        # 구조화 에러: 검증 실패 사유를 담아 되돌림 → 에이전트가 스스로 재시도 판단
        return {
            "content": [{"type": "text", "text":
                f"age={age!r}는 유효하지 않습니다. 사람 나이는 0~120 사이 정수여야 합니다. "
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
    setting_sources=[],  # 개인 로컬 설정(~/.claude/settings.json 등) 미로드 — 재현성
    thinking={"type": "disabled"},  # 다중 턴 tool_use 시 'thinking 블록 필요' 400 회피
    env=bedrock_agent_env(),
)


async def main():
    # 모델이 (a) 300을 잘못 기록 시도 → is_error → (b) 스스로 45로 고쳐 재시도하는 흐름을 관찰.
    async for msg in query(
        prompt=f"다음 문장에서 사람의 실제 나이를 extract_age 툴로 기록해줘: {TRICKY_TEXT}",
        options=options,
    ):
        print(msg)


if __name__ == "__main__":
    anyio.run(main)
