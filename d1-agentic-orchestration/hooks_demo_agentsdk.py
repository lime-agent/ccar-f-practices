"""D1 실습 (심화, Tier 2) — 진짜 hooks: PreToolUse / PostToolUse (Claude Agent SDK).

programmatic_gate.py 는 우리가 짠 execute_tool 안에서 한 '인라인 강제'였다(Tier 1, hooks 아님).
이 파일이 시험(D1 Task 1.5)이 말하는 **진짜 hooks** — 런타임이 툴 실행 '전후'에 자동으로 부르는 콜백:
  PreToolUse  : 툴 실행 '전'  → permissionDecision "deny" 로 차단 (정책 강제)
  PostToolUse : 툴 실행 '후'  → 결과 관찰/정규화

여기선 built-in Bash 툴로 시연한다(가장 단순·확실). 시험의 "환불 $500 초과 차단"도
동일한 PreToolUse 메커니즘이며, 그건 커스텀(MCP) 툴 등록이 추가로 필요할 뿐이다.

준비 (Tier 2):
    npm i -g @anthropic-ai/claude-code
    pip install claude-agent-sdk
    export CLAUDE_CODE_USE_BEDROCK=1
    export AWS_REGION=ap-northeast-2
    export AWS_BEARER_TOKEN_BEDROCK=<지급 키>
    # (선택) export ANTHROPIC_MODEL=<리전 프로파일 ID> — 미설정 시 shared/agent_sdk_config 기본값

실행: practices/ 에서  python d1-agentic-orchestration/hooks_demo_agentsdk.py
"""
import os
import sys

import anyio
from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient, HookMatcher

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from shared.agent_sdk_config import bedrock_agent_env  # noqa: E402

BLOCK_PATTERN = "prod"   # 정책 예시: 'prod' 포함 명령은 금지


async def pre_tool_use(input_data, tool_use_id, context):
    """툴 실행 '전' — 정책 위반이면 deny 로 차단(결정론적)."""
    if input_data.get("tool_name") != "Bash":
        return {}
    command = input_data.get("tool_input", {}).get("command", "")
    if BLOCK_PATTERN in command:
        print(f"  [PreToolUse] ⛔ 차단: '{command}' (금지 패턴 '{BLOCK_PATTERN}')")
        return {"hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": f"'{BLOCK_PATTERN}' 포함 명령은 정책상 금지",
        }}
    print(f"  [PreToolUse] ✅ 허용: '{command}'")
    return {}


async def post_tool_use(input_data, tool_use_id, context):
    """툴 실행 '후' — 결과 관찰(여기서 정규화도 가능: updatedToolOutput)."""
    print(f"  [PostToolUse] {input_data.get('tool_name')} 완료 — 결과 정규화 지점")
    return {}


options = ClaudeAgentOptions(
    allowed_tools=["Bash"],
    permission_mode="acceptEdits",
    setting_sources=[],  # 개인 로컬 설정(~/.claude/settings.json 훅·권한·MCP 등) 미로드 — 재현성 + 개인 훅 로그 노이즈 제거
    hooks={
        "PreToolUse": [HookMatcher(matcher="Bash", hooks=[pre_tool_use])],
        "PostToolUse": [HookMatcher(matcher="Bash", hooks=[post_tool_use])],
    },
    env=bedrock_agent_env(),
)

# 하나는 허용(echo hello), 하나는 'prod' 포함이라 PreToolUse 가 차단 → 대비가 보임
PROMPT = (
    'bash로 두 가지를 순서대로 실행해줘: '
    '(1) echo "hello from hook demo"   '
    '(2) echo "push to prod"'
)


async def main():
    async with ClaudeSDKClient(options=options) as client:
        await client.query(PROMPT)
        async for msg in client.receive_response():
            print(msg)


if __name__ == "__main__":
    anyio.run(main)
