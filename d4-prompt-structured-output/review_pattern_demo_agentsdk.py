"""D4 실습 (Tier 2, Claude Agent SDK) — 리뷰 아키텍처 (Ch14, 샘플 37·38·39).

review_pattern_demo.py 의 Agent SDK 버전.
Tier1의 "독립 인스턴스"는 맥락 없는 새 API 호출이었다. 여기서는 더 강한 격리를 보여준다:
Claude Agent SDK 의 서브에이전트는 코디네이터의 대화 히스토리를 **상속하지 않는다**(D1 05.3).

세 가지를 한 실행에서 대비한다:
  1) 자기 리뷰(코디네이터, "내가 짠 코드") vs reviewer 서브에이전트(코드만 Task)
  2) 멀티패스 — 파일별 file_reviewer → 로컬 결과만 integrator에 전달 (샘플 39)
  3) 각 이슈에 confidence를 붙여 ≥0.8 자동 / 0.4–0.8 인간 / <0.4 무시

Batch API(14.1)는 Bedrock에서 호출하지 않는다 — 개념만 (50%·24h·SLA 없음, 비차단만).

주의: 이 데모는 결정론적으로 재현되지 않는다(모델·실행마다 다를 수 있음).
핵심은 결과의 절대적 우열이 아니라 서브에이전트가 코디네이터 편향을 상속하지 않는다는 구조다.
Tier1은 발견율·버킷 분류를 우리 코드가 하고, 여기서는 비교·라우팅 판정도 코디네이터 텍스트 출력이다.

준비(Tier 2): npm i -g @anthropic-ai/claude-code · pip install claude-agent-sdk + Bedrock env
실행: practice/ 에서  python d4-prompt-structured-output/review_pattern_demo_agentsdk.py
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

PR_FILES = {
    "pricing.py": (
        "TAX_RATE = 0.10\n"
        "def tax(amount):\n"
        "    return amount * TAX_RATE\n"
    ),
    "checkout.py": (
        "def checkout(price):\n"
        "    tax = price * 0.08\n"
        "    return price + tax\n"
    ),
}

# 05.3: 서브에이전트는 코디네이터 대화를 상속하지 않는다 → 코드/로컬 결과만 Task로 실어 보낸다.
REVIEWER = AgentDefinition(
    description="코드만 보고 버그를 찾는 독립 리뷰어. 코드의 작성 배경·의도를 모른 채 코드 자체만 평가한다.",
    prompt="너는 독립 코드 리뷰어다. 주어진 코드에서 버그를 찾아 구체적으로 설명하라.",
    tools=[],
)
FILE_REVIEWER = AgentDefinition(
    description="한 파일의 로컬 이슈만 찾는 리뷰어. 다른 파일은 보지 않는다.",
    prompt="너는 단일 파일 리뷰어다. 주어진 파일만 보고 로컬 이슈를 짧게 보고하라. 다른 파일은 추측하지 마라.",
    tools=[],
)
INTEGRATOR = AgentDefinition(
    description="파일 소스와 로컬 리뷰를 나란히 보고 크로스파일 불일치만 찾는 리뷰어.",
    prompt=(
        "너는 크로스파일 통합 리뷰어다. 반드시 소스에서 숫자를 직접 비교하라. "
        "로컬 요약만 믿지 마라. 없는 함수 호출·없는 import는 지어내지 마라. "
        "상수와 리터럴이 파일마다 다르면 그 불일치를 구체적으로 보고하라."
    ),
    tools=[],
)

options = ClaudeAgentOptions(
    agents={
        "reviewer": REVIEWER,
        "file_reviewer": FILE_REVIEWER,
        "integrator": INTEGRATOR,
    },
    allowed_tools=["Task"],
    permission_mode="acceptEdits",
    setting_sources=[],  # 개인 로컬 설정 미로드 — 재현성
    thinking={"type": "disabled"},
    env=bedrock_agent_env(),
)

SELF_VS_INDEP_PROMPT = (
    f"다음은 네가 방금 작성했다고 가정한 코드다:\n```python\n{BUGGY_CODE}```\n\n"
    "1) 먼저 너 스스로(같은 맥락에서, '내가 짠 코드'라는 관점으로) 이 코드에 버그가 있는지 리뷰해봐.\n"
    "2) 그 다음, 'reviewer' 서브에이전트에게 Task로 **코드만** 넘겨 독립적으로 리뷰시켜봐 "
    "(누가 왜 짰는지, 네가 이미 찾은 버그는 주지 마).\n"
    "3) 두 리뷰 결과를 비교해서 알려줘."
)

_pr_blob = "\n\n".join(
    f"=== {path} ===\n```python\n{content}```" for path, content in PR_FILES.items()
)
MULTIPASS_PROMPT = (
    "아래는 2개 파일 PR이다. 한 pass에 몰아넣지 마라.\n\n"
    f"{_pr_blob}\n\n"
    "Pass 1: 각 파일을 'file_reviewer' 서브에이전트에 **파일 하나씩** Task로 넘겨 "
    "로컬 이슈만 찾아라. 다른 파일 내용은 Task에 넣지 마.\n"
    "Pass 2: 'integrator'에게 두 파일 **소스**와 Pass 1 로컬 결과를 함께 넘겨라. "
    "로컬 요약만 주면 숫자가 빠져 세율 불일치(0.10 vs 0.08)를 못 찾는다. "
    "checkout이 pricing.tax를 호출한다고 지어내지 마라.\n"
    "마지막에 모든 이슈에 confidence(0.0-1.0)를 붙이고 "
    ">=0.8 auto_flagged / 0.4 이상 0.8 미만 human_review / 0.4 미만 ignored 로 나눠라.\n"
    "신뢰도 기준: 1.0=확실한 버그, 0.8 이상=높은 확률, "
    "0.4 이상 0.8 미만=의심, 0.4 미만=가능성 낮음."
)


async def run(title, prompt):
    print(f"\n{'=' * 60}\n{title}\n")
    async for msg in query(prompt=prompt, options=options):
        print(msg)


async def main():
    await run("[1] 자기 리뷰 vs 독립 서브에이전트 (샘플 37·38)", SELF_VS_INDEP_PROMPT)
    await run("[2] 멀티패스 + 신뢰도 라우팅 (샘플 39)", MULTIPASS_PROMPT)
    print(
        "\n교훈: 서브에이전트는 코디네이터 편향을 상속하지 않는다. "
        "멀티패스는 개별 파일 → 크로스파일, 신뢰도로 인간 검토를 우선순위화한다. "
        "Batch API는 호출하지 않음 — 야간 배치만 적합, pre-merge는 실시간."
    )


if __name__ == "__main__":
    anyio.run(main)
