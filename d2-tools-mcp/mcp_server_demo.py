"""D2 실습 (심화, Tier 2) — 진짜 in-process MCP 서버 (Task 2.4).

Claude Agent SDK 의 @tool + create_sdk_mcp_server 로 커스텀 MCP 툴을 만들고,
에이전트가 그 툴을 호출하게 한다. (앞의 Tier1 데모는 Messages API 툴이었고,
이건 'MCP 서버'로 노출하는 진짜 방식)

네이밍 규칙: allowed_tools 에는  mcp__<서버이름>__<툴이름>  형식으로 적는다.

준비 (Tier 2):
    npm i -g @anthropic-ai/claude-code
    pip install claude-agent-sdk
    export CLAUDE_CODE_USE_BEDROCK=1
    export AWS_REGION=ap-northeast-2
    export AWS_BEARER_TOKEN_BEDROCK=<지급 키>
    # (선택) export ANTHROPIC_MODEL=<리전 프로파일 ID> — 미설정 시 shared/agent_sdk_config 기본값

실행: practices/ 에서  python d2-tools-mcp/mcp_server_demo.py
"""
import os
import sys

import anyio
from claude_agent_sdk import ClaudeAgentOptions, create_sdk_mcp_server, query, tool

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from shared.agent_sdk_config import bedrock_agent_env  # noqa: E402


# 1) 커스텀 MCP 툴 정의 — @tool(이름, 설명, 입력스키마)
@tool("get_order_status", "주문번호(예: #12345)로 주문 상태를 조회한다.", {"order_id": str})
async def get_order_status(args):
    # 실제로는 DB/외부 API 조회. 데모는 더미 데이터.
    oid = args["order_id"]
    return {"content": [{"type": "text", "text": f"주문 {oid}: 배송중, 도착예정 2026-08-08"}]}


# 2) in-process MCP 서버 생성
orders_server = create_sdk_mcp_server(name="orders", version="1.0.0", tools=[get_order_status])

# 3) 옵션 — 서버 등록 + 툴 허용(네이밍: mcp__orders__get_order_status) + Bedrock
options = ClaudeAgentOptions(
    mcp_servers={"orders": orders_server},
    allowed_tools=["mcp__orders__get_order_status"],
    permission_mode="acceptEdits",
    setting_sources=[],  # 개인 로컬 설정(~/.claude/settings.json 훅·권한·MCP 등) 미로드 — 재현성 + 개인 훅 로그 노이즈 제거
    thinking={"type": "disabled"},  # 확장 사고 off — 다중 턴 tool_use 시 'thinking 블록 필요' 400 회피
    env=bedrock_agent_env(),
)


async def main():
    # 모델이 우리가 만든 MCP 툴(get_order_status)을 호출하는 흐름이 스트리밍으로 보인다.
    async for msg in query(prompt="주문 #12345 상태 알려줘", options=options):
        print(msg)


if __name__ == "__main__":
    anyio.run(main)
