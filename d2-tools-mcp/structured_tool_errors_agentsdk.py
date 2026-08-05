"""D2 실습 (Tier 2, Claude Agent SDK) — 구조화 에러 & 재시도 (Task 2.2).

structured_tool_errors.py 의 Agent SDK 버전.
커스텀 MCP 툴이 실패를 `is_error`=True + 구조화 메시지(errorCategory/isRetryable)로 알리면,
모델이 그 신호를 보고 재시도할지 판단한다. 여기선 transient 에러 1회 후 성공하도록 했다.

준비(Tier 2): npm i -g @anthropic-ai/claude-code · pip install claude-agent-sdk + Bedrock env
실행: practices/ 에서  python d2-tools-mcp/structured_tool_errors_agentsdk.py
"""
import os
import sys

import anyio
from claude_agent_sdk import ClaudeAgentOptions, create_sdk_mcp_server, query, tool

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from shared.agent_sdk_config import bedrock_agent_env  # noqa: E402

_state = {"attempts": 0}


@tool("charge_payment", "결제를 처리한다. 금액(USD)을 받는다.", {"amount": float})
async def charge_payment(args):
    _state["attempts"] += 1
    if _state["attempts"] < 2:
        # 구조화 에러: transient(재시도 가능)임을 명시 → 모델이 재시도 판단 가능
        return {
            "content": [{"type": "text", "text":
                '{"errorCategory":"transient","isRetryable":true,'
                '"message":"결제 게이트웨이 일시 오류. 잠시 후 재시도 권장."}'}],
            "is_error": True,
        }
    return {"content": [{"type": "text", "text": f"결제 성공: ${args['amount']}"}]}


pay = create_sdk_mcp_server(name="pay", version="1.0.0", tools=[charge_payment])

options = ClaudeAgentOptions(
    mcp_servers={"pay": pay},
    allowed_tools=["mcp__pay__charge_payment"],
    permission_mode="acceptEdits",
    env=bedrock_agent_env(),
)


async def main():
    # transient 에러 → 모델이 재시도해서 성공하는 흐름을 관찰.
    async for msg in query(
        prompt="100달러 결제해줘. 일시적(transient) 오류가 나면 한 번 재시도해줘.",
        options=options,
    ):
        print(msg)


if __name__ == "__main__":
    anyio.run(main)
