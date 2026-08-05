"""Claude Agent SDK (Tier 2) 공용 Bedrock 설정.

`bedrock_client.py` 가 Tier1(AnthropicBedrock messages)용이라면, 이 모듈은
Tier2 — Claude Agent SDK(내부적으로 `claude` CLI 를 스폰) — 용 env 를 한 곳에서
해석한다. 각 `*_agentsdk.py` 스크립트가 `ClaudeAgentOptions(env=...)` 를
인라인으로 중복 구성하던 것을 대체한다.

함정 방지: ANTHROPIC_MODEL 이 비어 있으면 예전 인라인 코드는 그 키를 통째로
빼버렸고, 그러면 Claude Code 가 리전 access 없는 기본 모델로 폴백해 실패했다.
여기서는 검증된 APAC 교차추론 프로파일로 폴백하므로 모델 키가 절대 비지 않는다.

환경변수(있으면 우선, 없으면 기본값):
  CLAUDE_CODE_USE_BEDROCK     Bedrock 라우팅 on (기본 "1")
  AWS_REGION                  리전 (기본 ap-northeast-2)
  ANTHROPIC_MODEL             메인 모델 (기본 DEFAULT_AGENT_MODEL)
  ANTHROPIC_SMALL_FAST_MODEL  보조·빠른 모델 (기본 DEFAULT_SMALL_FAST_MODEL)
  AWS_BEARER_TOKEN_BEDROCK    Bedrock 베어러 키 (필수 — 없으면 CLI 인증 실패)
"""
import os

# 검증된 APAC 교차추론 프로파일 (2026-08-06 hooks 데모 실행으로 동작 확인).
# 리전이 바뀌면 콘솔에서 해당 리전의 프로파일 ID 로 교체한다.
DEFAULT_AGENT_MODEL: str = "apac.anthropic.claude-sonnet-4-20250514-v1:0"
DEFAULT_SMALL_FAST_MODEL: str = "apac.anthropic.claude-3-haiku-20240307-v1:0"


def bedrock_agent_env() -> dict[str, str]:
    """Agent SDK(`ClaudeAgentOptions.env`)용 Bedrock 라우팅 env 를 만든다.

    셸 환경변수가 있으면 그대로 쓰고, 없으면 검증된 기본값으로 채운다.
    값이 빈 항목은 넣지 않는다(빈 ANTHROPIC_MODEL 을 넘겨 CLI 가 기본 모델로
    떨어지는 함정 방지). AWS_BEARER_TOKEN_BEDROCK 만은 기본값이 없으므로,
    미설정 시 해당 키가 빠지고 CLI 가 인증 단계에서 실패한다(의도된 fail-fast).
    """
    resolved = {
        "CLAUDE_CODE_USE_BEDROCK": os.environ.get("CLAUDE_CODE_USE_BEDROCK", "1"),
        "AWS_REGION": os.environ.get("AWS_REGION", "ap-northeast-2"),
        "ANTHROPIC_MODEL": os.environ.get("ANTHROPIC_MODEL") or DEFAULT_AGENT_MODEL,
        "ANTHROPIC_SMALL_FAST_MODEL": (
            os.environ.get("ANTHROPIC_SMALL_FAST_MODEL") or DEFAULT_SMALL_FAST_MODEL
        ),
        "AWS_BEARER_TOKEN_BEDROCK": os.environ.get("AWS_BEARER_TOKEN_BEDROCK", ""),
    }
    return {k: v for k, v in resolved.items() if v}
