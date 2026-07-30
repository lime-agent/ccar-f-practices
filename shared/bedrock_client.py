"""Bedrock 실습 공용 클라이언트 (AnthropicBedrock).

Claude 구독 없이 Bedrock API 키(bearer token)만으로 Anthropic Messages 포맷을 호출한다.
anthropic SDK 의 `AnthropicBedrock` 을 쓰므로, 실습 코드가 시험 예제와 동일한 문법
(`client.messages.create` / `resp.stop_reason` / `tool_use`) 이 된다. (boto3 는 SDK 내부에서 자동 사용)

환경변수:
  AWS_BEARER_TOKEN_BEDROCK  Bedrock API 키(베어러 토큰)   ← .env
  AWS_REGION                리전 (기본 ap-northeast-2)
  BEDROCK_MODEL_ID / ANTHROPIC_MODEL  모델 프로파일 ID

설치: pip install "anthropic[bedrock]"   (0.99.x 이상)
검증: python -c "from shared.bedrock_client import ping; ping()"
"""
import os

from anthropic import AnthropicBedrock

# 리전별 교차추론 프로파일 ID는 콘솔에서 확인. 스모크 테스트 기본값은 검증된 haiku 프로파일.
DEFAULT_MODEL: str = (
    os.environ.get("BEDROCK_MODEL_ID")
    or os.environ.get("ANTHROPIC_MODEL")
    or "apac.anthropic.claude-3-haiku-20240307-v1:0"
)


def get_client() -> AnthropicBedrock:
    """환경변수로 구성된 AnthropicBedrock 클라이언트를 돌려준다.

    api_key 에 베어러 키를 명시하면 SDK 가 bearer 모드로 인증한다.
    (env `AWS_BEARER_TOKEN_BEDROCK` 만 설정해도 SDK 가 자동 인식)
    """
    return AnthropicBedrock(
        aws_region=os.environ.get("AWS_REGION", "ap-northeast-2"),
        api_key=os.environ.get("AWS_BEARER_TOKEN_BEDROCK"),
    )


def ping() -> None:
    """환경 검증용 단발 호출 — 키/리전/모델이 정상인지 빠르게 확인."""
    client = get_client()
    resp = client.messages.create(
        model=DEFAULT_MODEL,
        max_tokens=64,
        messages=[{"role": "user", "content": "한 문장으로 인사해줘."}],
    )
    text = "".join(b.text for b in resp.content if b.type == "text")
    print(f"[bedrock ok] stop={resp.stop_reason} :: {text}")


if __name__ == "__main__":
    ping()
