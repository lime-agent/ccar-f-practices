"""D4 실습 (Tier 2, Claude Agent SDK) — 자기 리뷰 vs 독립 서브에이전트 리뷰 (Ch14, 샘플 37·38).

review_pattern_demo.py 의 Agent SDK 버전.
Tier1의 "독립 인스턴스"는 그냥 맥락 없는 새 API 호출이었다. 여기서는 더 강한 격리를 보여준다:
Claude Agent SDK 의 서브에이전트는 코디네이터의 대화 히스토리를 **상속하지 않는다**(D1 05.3).
그래서 코디네이터 자신의 "자기 리뷰"(같은 맥락, "내가 짠 코드"라는 프레이밍)와,
독립 'reviewer' 서브에이전트에게 **코드만** Task로 넘긴 리뷰를 한 실행 안에서 대비시킨다.

주의: 이 데모는 결정론적으로 재현되지 않는다(모델·실행마다 다를 수 있음).
핵심은 결과의 절대적 우열이 아니라 "서브에이전트는 구조적으로 코디네이터의 편향을 상속하지 않는다"는 원칙.

준비(Tier 2): npm i -g @anthropic-ai/claude-code · pip install claude-agent-sdk + Bedrock env
실행: practices/ 에서  python d4-prompt-structured-output/review_pattern_demo_agentsdk.py
"""
import os
import sys

import anyio
from claude_agent_sdk import AgentDefinition, ClaudeAgentOptions, query

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from shared.agent_sdk_config import bedrock_agent_env  # noqa: E402

# 일부러 넣은 버그: range(1, n)은 n을 제외 → "1부터 n까지(n 포함) 합"에서 n이 빠지는 off-by-one
BUGGY_CODE = """def sum_up_to(n):
    \"\"\"1부터 n까지(n 포함)의 합을 구한다.\"\"\"
    total = 0
    for i in range(1, n):
        total += i
    return total
"""

# 05.3 패턴: 서브에이전트는 코디네이터의 대화를 상속하지 않는다.
# → "누가 왜 짰는지" 맥락이 구조적으로 차단되어, 코드 자체만 놓고 평가하게 된다.
REVIEWER = AgentDefinition(
    description="코드만 보고 버그를 찾는 독립 리뷰어. 코드의 작성 배경·의도를 모른 채 코드 자체만 평가한다.",
    prompt="너는 독립 코드 리뷰어다. 주어진 코드에서 버그를 찾아 구체적으로 설명하라.",
    tools=[],
)

options = ClaudeAgentOptions(
    agents={"reviewer": REVIEWER},
    allowed_tools=["Task"],          # 코디네이터가 reviewer 서브에이전트를 스폰하도록 허용
    permission_mode="acceptEdits",
    setting_sources=[],  # 개인 로컬 설정 미로드 — 재현성
    thinking={"type": "disabled"},  # 다중 턴 tool_use 시 'thinking 블록 필요' 400 회피
    env=bedrock_agent_env(),
)

PROMPT = (
    f"다음은 네가 방금 작성했다고 가정한 코드다:\n```python\n{BUGGY_CODE}```\n\n"
    "1) 먼저 너 스스로(같은 맥락에서, '내가 짠 코드'라는 관점으로) 이 코드에 버그가 있는지 리뷰해봐.\n"
    "2) 그 다음, 'reviewer' 서브에이전트에게 Task로 **코드만** 넘겨 독립적으로 리뷰시켜봐 "
    "(누가 왜 짰는지 맥락은 주지 마).\n"
    "3) 두 리뷰 결과를 비교해서 알려줘."
)


async def main():
    async for msg in query(prompt=PROMPT, options=options):
        print(msg)


if __name__ == "__main__":
    anyio.run(main)
