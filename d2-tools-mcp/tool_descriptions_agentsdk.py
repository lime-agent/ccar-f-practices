"""D2 실습 (Tier 2, Claude Agent SDK) — 툴 설명이 선택을 좌우 (Task 2.1).

tool_descriptions.py(Messages API)의 Agent SDK 버전.
커스텀 MCP 툴 2개를 '좋은 설명'으로 정의하면, 모델이 질문에 맞는 툴을 고른다.
(설명을 부실하게 바꾸면 오선택 → 아래 주석 참고)

준비(Tier 2): npm i -g @anthropic-ai/claude-code · pip install claude-agent-sdk
  + Bedrock env (shared/agent_sdk_config.bedrock_agent_env 가 해석; AWS_BEARER_TOKEN_BEDROCK 필수)
실행: practices/ 에서  python d2-tools-mcp/tool_descriptions_agentsdk.py
"""
import os
import sys

import anyio
from claude_agent_sdk import ClaudeAgentOptions, create_sdk_mcp_server, query, tool

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from shared.agent_sdk_config import bedrock_agent_env  # noqa: E402


# 좋은 설명 — 사용 시점 + 유사 툴과의 구분을 명시 (이게 선택을 좌우한다)
@tool("customer_lookup",
      "고객을 이메일로 조회한다. 계정(사람) 정보가 필요할 때만 사용. 주문 조회에는 쓰지 말 것(→ order_lookup).",
      {"email": str})
async def customer_lookup(args):
    return {"content": [{"type": "text", "text": f"고객 {args['email']}: active"}]}


@tool("order_lookup",
      "주문번호(예: #12345)로 주문 상태를 조회한다. 사용자가 특정 주문을 물을 때 사용.",
      {"order_id": str})
async def order_lookup(args):
    return {"content": [{"type": "text", "text": f"주문 {args['order_id']}: 배송중, 도착예정 2026-08-08"}]}
# 실험: 위 두 설명을 "고객 정보 조회"/"주문 정보 조회"처럼 모호하게 바꾸면 오선택이 늘어난다.

support = create_sdk_mcp_server(name="support", version="1.0.0", tools=[customer_lookup, order_lookup])

options = ClaudeAgentOptions(
    mcp_servers={"support": support},
    allowed_tools=["mcp__support__customer_lookup", "mcp__support__order_lookup"],
    permission_mode="acceptEdits",
    setting_sources=[],  # 개인 로컬 설정(~/.claude/settings.json 훅·권한·MCP·모델) 미로드 — 재현성
    thinking={"type": "disabled"},  # 확장 사고 off — 다중 턴 tool_use 시 'thinking 블록 필요' 400 회피
    env=bedrock_agent_env(),
)


async def main():
    # "주문 #12345" → 좋은 설명 덕에 order_lookup 을 고르는 흐름을 관찰.
    async for msg in query(prompt="주문 #12345 상태 알려줘", options=options):
        print(msg)


if __name__ == "__main__":
    anyio.run(main)
