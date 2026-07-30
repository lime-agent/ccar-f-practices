"""D1 실습 (심화, Tier 2) — 진짜 서브에이전트 병렬 (Claude Agent SDK).

parallel_subagents.py(ThreadPoolExecutor)는 '흉내'였다. 이 파일이 **실제 메커니즘**이다:
코디네이터가 Task 툴로 서브에이전트를 스폰하고, **한 응답에서 Task를 여러 개** 내면
런타임이 병렬로 실행한다. ← 시험(샘플 Q11)의 정답 방식.

⚠️ 이 실습만 준비물이 더 무겁다 (Tier 2):
    npm i -g @anthropic-ai/claude-code      # Agent SDK 실행 엔진(Claude Code CLI)
    pip install claude-agent-sdk
    # Bedrock 라우팅 (같은 베어러 키 재사용):
    export CLAUDE_CODE_USE_BEDROCK=1
    export AWS_REGION=ap-northeast-2
    export ANTHROPIC_MODEL=apac.anthropic.claude-sonnet-4-...   # 리전별 프로파일 ID
    export AWS_BEARER_TOKEN_BEDROCK=<지급 키>

실행: practices/ 에서  python d1-agentic-orchestration/parallel_subagents_agentsdk.py
(첫 실행은 CLI 기동으로 조금 느릴 수 있음)
"""
import os

import anyio
from claude_agent_sdk import AgentDefinition, ClaudeAgentOptions, query

# 1) 서브에이전트 "정의" — 코디네이터가 Task 로 스폰할 전문가.
#    tools=[] → 이 데모에선 외부 툴 없이 추론만 (안전·단순).
RESEARCHER = AgentDefinition(
    description="특정 하위 주제 하나를 조사해 3문장 이내로 요약하는 리서처",
    prompt="너는 리서치 전문가다. 맡은 하위 주제만 조사해 핵심을 3문장 이내로 요약하라.",
    tools=[],
)

# 2) 옵션 — 코디네이터가 Task 로 서브에이전트를 스폰하도록 허용 + Bedrock 라우팅.
options = ClaudeAgentOptions(
    agents={"researcher": RESEARCHER},
    allowed_tools=["Task"],          # 스폰 도구 Task 를 자동 허용(프롬프트 없이)
    permission_mode="acceptEdits",
    env={k: v for k, v in {
        "CLAUDE_CODE_USE_BEDROCK": os.environ.get("CLAUDE_CODE_USE_BEDROCK", "1"),
        "AWS_REGION": os.environ.get("AWS_REGION", "ap-northeast-2"),
        "ANTHROPIC_MODEL": os.environ.get("ANTHROPIC_MODEL", ""),
        "AWS_BEARER_TOKEN_BEDROCK": os.environ.get("AWS_BEARER_TOKEN_BEDROCK", ""),
    }.items() if v},
)

# 3) 코디네이터에게 "병렬로 나눠서" 지시 — 모델이 한 응답에서 Task 여러 개를 냄.
COORDINATOR_PROMPT = (
    "아래 세 하위 주제를 각각 'researcher' 서브에이전트에게 맡겨 "
    "**한 번에(병렬로) Task를 여러 개 호출**해 조사시키고, 끝나면 종합 요약해줘:\n"
    "1) AI 코딩툴 시장 규모와 성장률\n"
    "2) 상위 경쟁사 3곳과 강약점\n"
    "3) AI 관련 최신 규제 이슈"
)


async def main():
    # query() 는 스트리밍 async 제너레이터. 흐르는 메시지에서
    # 코디네이터의 Task 호출(여러 개)과 각 서브에이전트 결과가 보인다.
    async for msg in query(prompt=COORDINATOR_PROMPT, options=options):
        print(msg)


if __name__ == "__main__":
    anyio.run(main)
