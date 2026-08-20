"""D4 실습 — 스키마 검증-재시도 루프 + 재시도 유용성 판정 (Ch13.3).

시험 D4 핵심: `tool_use`는 JSON **구문** 오류만 API가 막는다. 값이 스키마의
**의미적 제약**(범위·원문 근거)을 지키는지는 별도 검증이 필요하다. 검증 실패를
`tool_result`(is_error=true)로 되돌려주면 모델이 고쳐서 재시도한다.

Ch13.3 `is_retry_useful`: 모든 검증 실패가 재시도로 해결되진 않는다.
  - RETRYABLE: 본문에 있는 숫자지만 범위/형식 오류 → 다시 보면 고칠 수 있음.
  - NOT_RETRYABLE: 본문에 정보가 없음(또는 본문에 없는 숫자를 지어냄) → 재시도 무의미.
    모델이 실수/환각을 안 해도, 검증 함수가 이 둘을 구분해야 한다.

실행: practice/ 에서  python d4-prompt-structured-output/validate_retry_loop.py
"""
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from shared.bedrock_client import DEFAULT_MODEL, get_client  # noqa: E402

client = get_client()

EXTRACT_AGE_TOOL = [{
    "name": "extract_age",
    "description": (
        "텍스트에서 사람의 실제 나이를 추출한다. "
        "본문에 실제 나이가 명시돼 있으면 found=true와 정수 age를, "
        "명시돼 있지 않으면 found=false와 age=null을 반환한다(추측 금지)."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "age": {"type": ["integer", "null"]},
            "found": {"type": "boolean", "description": "본문에 실제 나이가 명시돼 있었는지"},
        },
        "required": ["age", "found"],
    },
}]

# RETRYABLE 후보: 과장된 300과 실제 나이 45가 같은 문장에 있음
TRICKY_TEXT = "저희 할머니는 마을에서 300살 먹은 나무보다 오래 사신 것처럼 느껴지지만, 실제로는 45세이십니다."

# NOT_RETRYABLE: 나이 정보가 본문에 전혀 없음
NO_AGE_TEXT = "저희 할머니는 최근에 이사를 하셨고, 요즘은 정원 가꾸기에 재미를 붙이셨습니다."

MAX_RETRIES = 3


def age_in_source(age, text):
    """추출한 정수가 원문에 숫자로 등장하는지(환각 차단). '45세', '300살' 허용."""
    if not isinstance(age, int):
        return False
    return re.search(rf"(?<!\d){age}(?!\d)", text) is not None


def validate(age, found, text):
    """의미 검증. 사유 접두어로 재시도 유용성(RETRYABLE / NOT_RETRYABLE)을 표시한다."""
    if not found or age is None:
        return False, "NOT_RETRYABLE: 본문에 실제 나이 정보가 없습니다. 재시도해도 찾을 수 없습니다."
    if not age_in_source(age, text):
        return False, (
            f"NOT_RETRYABLE: age={age!r}는 본문에 없는 숫자입니다(환각). "
            "재시도해도 없는 정보는 생기지 않습니다."
        )
    if not isinstance(age, int) or not (0 <= age <= 120):
        return False, (
            f"RETRYABLE: age={age!r}는 유효하지 않습니다. 사람 나이는 0~120 사이 정수여야 합니다. "
            "과장된 숫자(예: '300살 먹은 나무')는 실제 나이가 아닙니다. "
            "본문에서 실제 사람 나이를 다시 찾아 정수로 반환하세요."
        )
    return True, None


def is_retryable(reason):
    """Ch13.3 is_retry_useful: 사유 태그로 재시도가 도움될지 판단."""
    return reason is not None and reason.startswith("RETRYABLE")


def show_validate_fixtures():
    """모델이 어떤 값을 내든, 13.3 분기는 픽스처로 항상 보여 준다."""
    print("[검증 분기 시연] 모델 호출 없이 validate()만 적용\n")
    fixtures = [
        ("케이스1 잘못된 추출(300)", 300, True, TRICKY_TEXT),
        ("케이스1 올바른 추출(45)", 45, True, TRICKY_TEXT),
        ("케이스2 환각(70)", 70, True, NO_AGE_TEXT),
        ("케이스2 정직한 부재", None, False, NO_AGE_TEXT),
    ]
    for label, age, found, text in fixtures:
        ok, reason = validate(age, found, text)
        if ok:
            print(f"  {label}: age={age!r} found={found} → ✅ 유효 / 재시도 불필요")
        else:
            useful = "예" if is_retryable(reason) else "아니오"
            print(f"  {label}: age={age!r} found={found} → ❌ {reason}")
            print(f"    is_retry_useful? {useful}")
    print()


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
        found = tool_block.input.get("found")
        ok, reason = validate(age, found, text)
        print(f"  시도 {attempt}: age={age!r} found={found!r} → {'✅ 유효' if ok else f'❌ 무효 — {reason}'}")
        if ok:
            return age

        if not is_retryable(reason):
            print("  ⛔ 재시도 무의미(정보 자체 없음/환각) — 즉시 에스컬레이션, 남은 시도 낭비 안 함")
            return None

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
    show_validate_fixtures()

    print("[케이스 1] RETRYABLE — 형식/범위 오류 (라이브 추출)")
    print(f"문장: {TRICKY_TEXT}")
    result1 = extract_with_retry(TRICKY_TEXT)
    print(f"최종 결과: age={result1}\n")

    print("[케이스 2] NOT_RETRYABLE — 정보 자체가 없음 (라이브 추출)")
    print(f"문장: {NO_AGE_TEXT}")
    result2 = extract_with_retry(NO_AGE_TEXT)
    print(f"최종 결과: age={result2}")

    print("\n관찰:")
    if result1 == 45:
        print(
            "  - 케이스1 최종값은 45(정답). 첫 시도가 45면 재시도는 안 열림 — 위 픽스처의 300 분기를 볼 것. "
            "(아키텍처 덕이 아니라 문장이 모델에게 쉬워서다 — Tier2 실행도 똑같이 첫 시도에 45가 나올 수 있음)"
        )
    else:
        print(f"  - 케이스1 최종값 age={result1!r} (기대: 45, 또는 재시도 한도 초과 시 None)")
    if result2 is None:
        print(
            "  - 케이스2는 에스컬레이션됨(재시도 없음). 이번 실행은 found=False 분기로 막힌 것이고, "
            "환각 숫자(예: 70) 차단은 grounding 분기(age_in_source)로 위 픽스처에서 별도로 확인됐다."
        )
    else:
        print(f"  - 케이스2가 age={result2!r}를 반환함 — grounding이 놓친 경우, 로그 확인.")
    print(
        "\n교훈: 검증 실패가 '형식/범위 오류'(RETRYABLE)면 tool_result(is_error)로 재시도가 유효하지만, "
        "'정보 자체가 없음/환각'(NOT_RETRYABLE)이면 몇 번을 다시 시켜도 못 찾는다 — 이걸 구분해서 "
        "무의미한 재시도를 조기에 끊고 사람에게 넘기는 것이 Ch13.3 재시도 유용성 판정의 핵심이다."
    )
