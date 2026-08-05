"""D1 실습 (심화, Tier 2) — 세션 관리: resume(이어가기) & fork(독립 분기).

06.4 개념을 실코드로 옮긴다.
  - session_store + session_id 로 대화를 '저장'한다.
  - resume 로 나중에 같은 세션을 '이어받는다'(제자리 — 원본을 계속 씀).
  - fork_session 으로 공통 base 에서 '독립 분기'를 만든다(원본은 보존).

resume vs fork (시험 핵심):
  resume : 같은 세션을 이어감            → "어제 하던 거 계속"
  fork   : 어느 지점에서 복제해 새 분기   → "같은 base 에서 A/B 를 따로 실험"

⚠️ 실제 SDK(0.2.130) 시그니처 — 시험 가이드(v0.1) 의사코드와 다르다:
    fork_session(session_id, directory=None, up_to_message_id=None, title=None)
      → ForkSessionResult(.session_id)
    up_to_message_id 를 생략하면 세션 '전체'를 복제한다(메시지 uuid 플러밍 불필요).

준비 (Tier 2):
    npm i -g @anthropic-ai/claude-code      # Agent SDK 실행 엔진(Claude Code CLI)
    pip install claude-agent-sdk
    export CLAUDE_CODE_USE_BEDROCK=1
    export AWS_REGION=ap-northeast-2
    export AWS_BEARER_TOKEN_BEDROCK=<지급 키>
    # (선택) export ANTHROPIC_MODEL=<리전 프로파일 ID> — 미설정 시 shared/agent_sdk_config 기본값

실행: practices/ 에서  python d1-agentic-orchestration/session_fork_resume_agentsdk.py
"""
import inspect
import os
import sys

import anyio
from claude_agent_sdk import (
    ClaudeAgentOptions,
    InMemorySessionStore,
    ResultMessage,
    fork_session,
    query,
)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from shared.agent_sdk_config import bedrock_agent_env  # noqa: E402

# 데모용 인메모리 저장소(프로세스 종료 시 사라짐) + 고정 base 세션 ID.
STORE = InMemorySessionStore()
BASE_ID = "d1-session-demo-base"
ENV = bedrock_agent_env()


async def run(label: str, prompt: str, options: ClaudeAgentOptions) -> str:
    """query 스트림을 출력하고 최종 텍스트(ResultMessage.result)를 반환한다.

    세션 ID 는 옵션에 명시(BASE_ID)하거나 fork 결과로 이미 알고 있으므로,
    여기서는 스트림에서 결과 텍스트만 뽑는다.
    """
    print(f"\n--- [{label}] {prompt}")
    result_text = ""
    async for msg in query(prompt=prompt, options=options):
        if isinstance(msg, ResultMessage) and msg.result:
            result_text = msg.result
        print(msg)
    return result_text


async def make_fork(session_id: str, title: str) -> str:
    """공통 base 에서 독립 분기를 만들고 새 session_id 를 돌려준다.

    fork_session 은 이 버전에서 동기 함수지만, 버전차로 코루틴일 수 있어
    방어적으로 isawaitable 로 감싼다. up_to_message_id 생략 = 세션 전체 복제.
    """
    res = fork_session(session_id=session_id, title=title)
    if inspect.isawaitable(res):
        res = await res
    return res.session_id


async def main():
    # 1) BASE 세션: 공통 컨텍스트를 심고 session_store 에 저장한다.
    print("\n=== 1) BASE 세션 생성 (공통 기준점) ===")
    base_opts = ClaudeAgentOptions(
        session_id=BASE_ID,
        session_store=STORE,
        env=ENV,
    )
    await run("base", "우리는 결제 지연 버그를 조사 중이다. 상황을 한 문장으로 요약해줘.", base_opts)

    # 2) RESUME: 같은 세션을 '이어받아' 계속(제자리). base 맥락을 기억한다.
    print("\n=== 2) RESUME (이어가기 — 원본을 계속 씀) ===")
    resume_opts = ClaudeAgentOptions(
        session_store=STORE,
        resume=BASE_ID,
        env=ENV,
    )
    await run("resume", "방금 그 버그의 재현 조건 후보 2가지만 짧게.", resume_opts)

    # 3) FORK: 공통 base 에서 '독립 분기' 2개 → 서로/원본과 간섭 없이 A/B 탐색.
    print("\n=== 3) FORK (공통 base에서 독립 분기 A/B) ===")
    try:
        fork_a = await make_fork(BASE_ID, title="approach-a-caching")
        fork_b = await make_fork(BASE_ID, title="approach-b-algorithm")
    except Exception as e:  # noqa: BLE001 — 데모: 환경차로 실패 시 명확히 안내
        print(f"  ⚠️ fork 생략: {type(e).__name__}: {e}")
        print("     (fork_session 이 on-disk 세션을 참조한다. base 실행이 선행돼야 하며,")
        print("      필요 시 directory 인자로 세션 경로를 지정한다.)")
        return

    print(f"  분기 생성: A={fork_a}  B={fork_b}  (원본 {BASE_ID} 는 보존)")

    # 각 분기를 독립적으로 탐색 — 한쪽에서 뭘 하든 다른 쪽/원본에 영향 없음.
    await run("fork-A", "접근법 A: 캐싱으로 해결한다면 핵심 아이디어 1줄.",
              ClaudeAgentOptions(session_store=STORE, resume=fork_a, env=ENV))
    await run("fork-B", "접근법 B: 알고리즘 최적화로 해결한다면 핵심 아이디어 1줄.",
              ClaudeAgentOptions(session_store=STORE, resume=fork_b, env=ENV))

    print("\n=== 정리 ===")
    print("  resume = 같은 세션 이어가기(제자리) / fork = base에서 독립 분기 복제(원본 보존)")


if __name__ == "__main__":
    anyio.run(main)
