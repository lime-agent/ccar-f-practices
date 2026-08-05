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
    export AWS_BEARER_TOKEN_BEDROCK=<지급 키>
    # (선택) export ANTHROPIC_MODEL=<리전 프로파일 ID> — 미설정 시 shared/agent_sdk_config 기본값

실행: practices/ 에서  python d1-agentic-orchestration/parallel_subagents_agentsdk.py
(첫 실행은 CLI 기동으로 조금 느릴 수 있음)
"""
import json
import os
import sys

import anyio
from claude_agent_sdk import AgentDefinition, ClaudeAgentOptions, query

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from shared.agent_sdk_config import bedrock_agent_env  # noqa: E402

# 1) 서브에이전트 "정의" — 코디네이터가 Task 로 스폰할 전문가.
#    tools=[] → 이 데모에선 외부 툴 없이 추론만 (안전·단순).
RESEARCHER = AgentDefinition(
    description="특정 하위 주제 하나를 조사해 구조화 요약을 반환하는 리서처",
    # 05.3 패턴1: 서브의 정체성/출력 규약을 prompt(=system 성격)에 고정.
    #            메타데이터/콘텐츠 분리 → claim(주장)과 source(출처)를 따로 담게 강제.
    prompt=(
        "너는 리서치 전문가다. 맡은 하위 주제만 조사한다.\n"
        "반드시 아래 JSON 구조로만 답하라 (주장과 근거·출처를 분리):\n"
        '{"claim":"...", "evidence":"...", '
        '"source":{"url":"...","date":"YYYY-MM-DD"}, "confidence":0.0~1.0}'
    ),
    tools=[],
)

# 2) 옵션 — 코디네이터가 Task 로 서브에이전트를 스폰하도록 허용 + Bedrock 라우팅.
options = ClaudeAgentOptions(
    agents={"researcher": RESEARCHER},
    allowed_tools=["Task"],          # 스폰 도구 Task 를 자동 허용(프롬프트 없이)
    permission_mode="acceptEdits",
    setting_sources=[],  # 개인 로컬 설정(~/.claude/settings.json 훅·권한·MCP 등) 미로드 — 재현성 + 개인 훅 로그 노이즈 제거
    env=bedrock_agent_env(),
)

# 05.3: 서브에이전트는 코디네이터의 컨텍스트를 상속하지 않는다.
#        공통 배경 중 "핵심만" 추려(요약 전달) 각 Task prompt 에 명시적으로 실어 보낸다.
PROJECT_CONTEXT = {
    "client": "전략팀",
    "goal": "AI 코딩툴 시장 진입 판단",
    "deadline": "2026-Q3",
    "constraints": ["국내 규제 우선", "B2B 관점"],  # 상위 제약만
}

# 3) 코디네이터에게 "병렬로 나눠서" 지시 — 모델이 한 응답에서 Task 여러 개를 냄.
COORDINATOR_PROMPT = (
    f"[프로젝트 컨텍스트]\n{json.dumps(PROJECT_CONTEXT, ensure_ascii=False)}\n\n"
    "아래 세 하위 주제를 각각 'researcher' 서브에이전트에게 맡겨 "
    "**한 번에(병렬로) Task를 여러 개 호출**해 조사시켜라.\n"
    "⚠️ 각 Task 호출 시, 위 컨텍스트 중 그 서브에이전트에게 필요한 부분을 "
    "prompt 에 **명시적으로 복사해 넣어라**(서브는 이 대화를 상속하지 않음). "
    "전역 상태 공유 금지.\n"
    "1) AI 코딩툴 시장 규모와 성장률\n"
    "2) 상위 경쟁사 3곳과 강약점\n"
    "3) AI 관련 최신 규제 이슈\n"
    "끝나면 각 결과의 source 를 유지한 채 종합 요약하라."
)


async def main():
    # query() 는 스트리밍 async 제너레이터. 흐르는 메시지에서
    # 코디네이터의 Task 호출(여러 개)과 각 서브에이전트 결과가 보인다.
    async for msg in query(prompt=COORDINATOR_PROMPT, options=options):
        print(msg)


if __name__ == "__main__":
    anyio.run(main)
