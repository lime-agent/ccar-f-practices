"""D4 실습 — tool_use + JSON 스키마로 구조화 추출, nullable로 환각 방지 (Ch12·Ch13, 교재 A4 #3).

시험 D4 핵심: `tool_use`는 **JSON 구문 오류**를 API가 제거해주지만(파서 불필요),
**의미적 정확성**(값이 맞는지)까지는 보장하지 않는다 — 별도 검증이 필요하다.
특히 텍스트에 없는 값을 모델이 "그럴듯하게 지어내는" 환각이 위험하다.

해결: 값이 없을 수 있는 필드를 `"type": ["string", "null"]`(nullable)로 선언하고,
설명(description)에 "텍스트에 없으면 null. 추측하지 말 것."을 명시한다.

(A) 나쁜 스키마 — 필드가 전부 필수 string(null 불허) + 지시 없음 → 없는 값도 어떻게든 채운다.
(B) 좋은 스키마 — nullable + "추측 금지" 지시 → 없는 값은 null로 정직하게 반환.
(C) 13.2 확장 패턴 — enum + "other" + detail: 카테고리를 고정 enum으로 제한하면서도
    예상 못한 값은 "other" + 상세 설명(nullable)으로 받아내 스키마가 안 깨지게 한다.

주의: (A)에서 모델이 정확히 무엇을 채우는지는 모델마다 다르다(빈 문자열 vs 지어낸 값 등).
핵심은 "있음/없음을 구분할 명시적 신호(null)가 스키마에 없다"는 구조적 문제.

실행: practice/ 에서  python d4-prompt-structured-output/extract_structured.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from shared.bedrock_client import DEFAULT_MODEL, get_client  # noqa: E402

client = get_client()

# 고객 문의: 환불 금액(refund_amount_requested)이 텍스트에 없음 — 정직하게 null이어야 정답.
TICKET_TEXT = (
    "안녕하세요, 주문 #98213인데 배송이 3일째 안 와요. "
    "환불은 원하지 않고 그냥 배송 상태만 확인하고 싶어요."
)

# (A) 나쁜 스키마 — 전부 string 필수, null 불허, "없으면 어떻게 하라"는 지시 없음
BAD_TOOL = [{
    "name": "extract_ticket",
    "description": "고객 문의에서 정보를 추출한다.",
    "input_schema": {
        "type": "object",
        "properties": {
            "order_id": {"type": "string"},
            "complaint": {"type": "string"},
            "refund_amount_requested": {"type": "string", "description": "요청한 환불 금액"},
            "desired_action": {"type": "string"},
        },
        "required": ["order_id", "complaint", "refund_amount_requested", "desired_action"],
    },
}]

# (B) 좋은 스키마 — nullable(["string","null"]) + "없으면 null, 추측 금지" 명시
GOOD_TOOL = [{
    "name": "extract_ticket",
    "description": "고객 문의에서 정보를 추출한다. 텍스트에 명시되지 않은 항목은 추측하지 말고 null을 반환한다.",
    "input_schema": {
        "type": "object",
        "properties": {
            "order_id": {"type": "string"},
            "complaint": {"type": "string"},
            "refund_amount_requested": {
                "type": ["string", "null"],
                "description": "요청한 환불 금액. 텍스트에 금액이 명시되지 않으면 null(추측 금지).",
            },
            "desired_action": {"type": "string"},
        },
        "required": ["order_id", "complaint", "refund_amount_requested", "desired_action"],
    },
}]


# (C) enum + "other" + detail — desired_action을 고정 카테고리로 제한하되,
#     안 맞는 요청은 "other"로 받고 desired_action_detail(nullable)에 실제 요청을 담는다.
EXTENDED_TOOL = [{
    "name": "extract_ticket",
    "description": "고객 문의에서 정보를 추출한다. 텍스트에 명시되지 않은 항목은 추측하지 말고 null을 반환한다.",
    "input_schema": {
        "type": "object",
        "properties": {
            "order_id": {"type": "string"},
            "complaint": {"type": "string"},
            "refund_amount_requested": {
                "type": ["string", "null"],
                "description": "요청한 환불 금액. 텍스트에 금액이 명시되지 않으면 null(추측 금지).",
            },
            "desired_action": {
                "type": "string",
                "enum": ["refund", "delivery_status", "exchange", "other"],
                "description": "고객이 원하는 조치. 아래 정의된 값에 안 맞으면 'other'.",
            },
            "desired_action_detail": {
                "type": ["string", "null"],
                "description": "desired_action이 'other'일 때만 구체적으로 설명. 그 외엔 null.",
            },
        },
        "required": [
            "order_id", "complaint", "refund_amount_requested",
            "desired_action", "desired_action_detail",
        ],
    },
}]

# enum "other"가 실제로 걸리는 케이스 — 미리 정의한 카테고리(refund/delivery_status/exchange) 밖의 요청
OTHER_TICKET_TEXT = "제품은 만족하는데, 이 브랜드 굿즈 콜라보 이벤트가 있으면 알려주실 수 있나요?"


def extract(tools, text=None):
    resp = client.messages.create(
        model=DEFAULT_MODEL, max_tokens=512, tools=tools,
        tool_choice={"type": "tool", "name": "extract_ticket"},
        messages=[{"role": "user", "content": text or TICKET_TEXT}],
    )
    for b in resp.content:
        if b.type == "tool_use":
            return b.input
    return None


if __name__ == "__main__":
    print(f"문의: {TICKET_TEXT}\n")

    print("(A) 나쁜 스키마(null 불허) →")
    result_a = extract(BAD_TOOL)
    print(f"  {result_a}")
    refund_a = result_a.get("refund_amount_requested")
    flag_a = "⚠️ 값이 채워짐(환각 가능성) — 원문엔 금액 언급 없음" if refund_a else "(비어있음)"
    print(f"  ← refund_amount_requested = {refund_a!r}  {flag_a}")

    print("\n(B) 좋은 스키마(nullable + 추측 금지 지시) →")
    result_b = extract(GOOD_TOOL)
    print(f"  {result_b}")
    refund_b = result_b.get("refund_amount_requested")
    flag_b = "✅ 정직한 null" if refund_b is None else "⚠️ 값이 채워짐 — 원문 재확인 필요"
    print(f"  ← refund_amount_requested = {refund_b!r}  {flag_b}")

    print("\n(C) enum + 'other' + detail 확장성 (Ch13.2) →")
    result_c1 = extract(EXTENDED_TOOL, TICKET_TEXT)
    print(f"  일반 문의 → desired_action={result_c1.get('desired_action')!r}, "
          f"detail={result_c1.get('desired_action_detail')!r}")
    result_c2 = extract(EXTENDED_TOOL, OTHER_TICKET_TEXT)
    print(f"  예상 밖 문의 → desired_action={result_c2.get('desired_action')!r}, "
          f"detail={result_c2.get('desired_action_detail')!r}")
    print(
        "  ← 미리 정의한 카테고리에 맞으면 그 값을, 안 맞으면 'other'+detail로 받아내 "
        "스키마가 안 깨짐(고정 enum만 썼다면 여기서 에러가 났을 상황)."
    )

    print(
        "\n교훈: tool_use는 '구문 오류'만 막아준다 — '없는 값을 지어내는 환각'은 "
        "nullable 스키마 + 명시적 지시로 직접 방지해야 한다 (Ch13, 샘플 35). "
        "그리고 enum+'other'+detail 패턴으로 예상 못한 입력에도 스키마가 안 깨지게 설계한다 (Ch13.2)."
    )
