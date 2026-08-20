"""D4 실습 — 스키마 검증-재시도 루프 (Ch13, 실습 목표 3).

시험 D4 핵심: `tool_use`는 JSON **구문** 오류를 API가 막아주지만, 값이 스키마의
**의미적 제약**(범위·형식)을 지키는지는 별도로 검증해야 한다. 검증 실패를
`tool_result`(is_error=true)로 모델에 되돌려주면, 모델이 스스로 원인을 읽고
고쳐서 재시도한다 — 파서를 새로 짜거나 사람이 개입할 필요가 없다.

과제: 문장에서 "나이(age)"를 추출하되 0~120 범위를 벗어나면 무효 처리하고,
왜 무효인지 알려줘서 재시도시킨다.

실행: practice/ 에서  python d4-prompt-structured-output/validate_retry_loop.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from shared.bedrock_client import DEFAULT_MODEL, get_client  # noqa: E402

client = get_client()

EXTRACT_AGE_TOOL = [{
    "name": "extract_age",
    "description": "텍스트에서 사람의 나이를 정수로 추출한다.",
    "input_schema": {
        "type": "object",
        "properties": {"age": {"type": "integer"}},
        "required": ["age"],
    },
}]

# 일부러 헷갈리게: "300살"이라는 과장 표현과 실제 나이(45)가 같은 문장에 있음
TRICKY_TEXT = "저희 할머니는 마을에서 300살 먹은 나무보다 오래 사신 것처럼 느껴지지만, 실제로는 45세이십니다."

MAX_RETRIES = 3


def validate(age):
    """스키마의 의미적 제약: 0~120 범위. 벗어나면 이유를 담아 반환."""
    if not isinstance(age, int) or not (0 <= age <= 120):
        return False, (
            f"age={age!r}는 유효하지 않습니다. 사람 나이는 0~120 사이 정수여야 합니다. "
            "과장된 숫자(예: '300살 먹은 나무')는 실제 나이가 아닙니다. "
            "본문에서 실제 사람 나이를 다시 찾아 정수로 반환하세요."
        )
    return True, None


def extract_with_retry(text, max_retries=MAX_RETRIES):
    messages = [{"role": "user", "content": text}]
    for attempt in range(1, max_retries + 1):
        resp = client.messages.create(
            model=DEFAULT_MODEL, max_tokens=256, tools=EXTRACT_AGE_TOOL,
            tool_choice={"type": "tool", "name": "extract_age"},
            messages=messages,
        )
        tool_block = next(b for b in resp.content if b.type == "tool_use")
        age = tool_block.input.get("age")
        ok, reason = validate(age)
        print(f"  시도 {attempt}: age={age!r} → {'✅ 유효' if ok else f'❌ 무효 — {reason}'}")
        if ok:
            return age

        # 검증 실패를 tool_result(is_error)로 돌려줘 모델이 스스로 고치게 한다
        messages.append({"role": "assistant", "content": resp.content})
        messages.append({
            "role": "user",
            "content": [{
                "type": "tool_result",
                "tool_use_id": tool_block.id,
                "content": reason,
                "is_error": True,
            }],
        })
    print("  ⛔ 재시도 한도 초과 — 사람 개입 필요")
    return None


if __name__ == "__main__":
    print(f"문장: {TRICKY_TEXT}\n")
    result = extract_with_retry(TRICKY_TEXT)
    print(f"\n최종 결과: age={result}")
    print(
        "\n교훈: 스키마 검증 실패를 tool_result(is_error)로 모델에 되돌려주면 "
        "모델이 스스로 원인을 읽고 고쳐서 재시도한다 — 검증-재시도 루프의 핵심 (Ch13)."
    )
