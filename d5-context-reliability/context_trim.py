"""D5 실습 — 툴 결과 트리밍으로 컨텍스트 예산 지키기 (Task 5.1 / Ch15.1).

시험 D5 핵심: 툴 결과가 컨텍스트에 누적되면서 **관련성 대비 과도하게 토큰을 소비**한다.
예: order lookup 하나가 40+ 필드를 반환하는데 환불 처리에 필요한 건 5개뿐.
→ 장황한 출력이 컨텍스트에 누적되기 **전에** 관련 필드만 트리밍한다.

이 데모는 두 부분이다:
  1) 결정론적 측정 — 원본 vs 트리밍의 크기·필드 수를 모델 호출 없이 비교(항상 재현됨).
  2) 라이브 확인 — 트리밍된 5개 필드만으로도 환불 판단이 되는지 실제 호출로 확인.

정신모델: 컨텍스트는 유한한 예산이다. 토큰 소비는 **관련성에 비례**해야 한다.

실행: practices/ 에서  python d5-context-reliability/context_trim.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from shared.bedrock_client import DEFAULT_MODEL, get_client  # noqa: E402

client = get_client()

# 현실적인 order lookup 응답 — 실제 커머스 API는 이보다 더 많은 필드를 준다.
RAW_ORDER = {
    "order_id": "ORD-98213",
    "status": "delivered",
    "items": [{"sku": "KB-771", "name": "무선 키보드", "qty": 1, "price": 45.99}],
    "total_amount": 45.99,
    "customer_id": "CUST-2024-789",
    # ↓ 아래부터는 환불 판단에 쓰이지 않는 필드들 (컨텍스트만 잡아먹는다)
    "warehouse_id": "WH-SEOUL-03",
    "warehouse_zone": "A-14-3",
    "picker_employee_id": "EMP-3391",
    "packer_employee_id": "EMP-4102",
    "carrier": "CJ대한통운",
    "carrier_account": "ACCT-99120",
    "tracking_number": "123456789012",
    "tracking_url": "https://tracking.example.com/123456789012",
    "shipping_method": "standard",
    "shipping_cost": 3.0,
    "insurance_applied": False,
    "signature_required": False,
    "package_weight_kg": 0.82,
    "package_dims_cm": [30, 20, 6],
    "label_printed_at": "2026-08-20T09:12:00Z",
    "manifest_id": "MAN-2026-08-20-017",
    "route_code": "SEL-GN-014",
    "delivery_attempts": 1,
    "delivered_at": "2026-08-22T14:03:00Z",
    "recipient_name": "홍길동",
    "recipient_relation": "본인",
    "gift_wrap": False,
    "gift_message": None,
    "coupon_code": None,
    "loyalty_points_earned": 45,
    "loyalty_tier_at_purchase": "silver",
    "payment_gateway": "PG-KCP",
    "payment_auth_code": "AUTH-77120391",
    "card_bin": "512345",
    "card_last4": "1234",
    "installment_months": 0,
    "tax_invoice_issued": False,
    "channel": "mobile_app",
    "app_version": "4.12.1",
    "device_os": "iOS 18.2",
    "utm_source": "instagram",
    "utm_campaign": "summer_sale_2026",
    "created_at": "2026-08-20T08:40:00Z",
    "updated_at": "2026-08-22T14:03:00Z",
}

# 환불 판단에 실제로 필요한 필드 — 이 목록이 곧 "관련성" 정의다.
REFUND_RELEVANT_FIELDS = ("order_id", "status", "items", "total_amount", "customer_id")


def trim_order_result(raw_order: dict, keep: tuple = REFUND_RELEVANT_FIELDS) -> dict:
    """관련 필드만 남긴다. 컨텍스트에 '누적되기 전에' 적용하는 것이 핵심."""
    return {k: raw_order[k] for k in keep if k in raw_order}


def size_of(payload: dict) -> tuple[int, int]:
    """(필드 수, 직렬화 문자 수). 문자 수는 토큰 비용의 대리 지표."""
    serialized = json.dumps(payload, ensure_ascii=False)
    return len(payload), len(serialized)


def ask_refund_decision(order_payload: dict) -> str:
    """주어진 주문 정보만으로 환불 가능 여부를 판단하게 한다."""
    resp = client.messages.create(
        model=DEFAULT_MODEL,
        max_tokens=256,
        system=(
            "너는 환불 심사 담당자다. 주어진 주문 정보만 근거로 판단하라. "
            "정책: status가 'delivered'이고 금액이 $100 이하면 환불 승인 가능."
        ),
        messages=[{
            "role": "user",
            "content": (
                "다음 주문의 환불 승인 가능 여부를 한 문장으로 판단하고, "
                f"근거로 쓴 필드명을 나열하라:\n{json.dumps(order_payload, ensure_ascii=False)}"
            ),
        }],
    )
    return "".join(b.text for b in resp.content if b.type == "text").strip()


if __name__ == "__main__":
    trimmed = trim_order_result(RAW_ORDER)

    print("=" * 60)
    print("[1] 결정론적 측정 — 모델 호출 없이 크기 비교")
    raw_fields, raw_chars = size_of(RAW_ORDER)
    trim_fields, trim_chars = size_of(trimmed)
    print(f"  원본 툴 결과   : 필드 {raw_fields}개 / {raw_chars:,}자")
    print(f"  트리밍 후      : 필드 {trim_fields}개 / {trim_chars:,}자")
    print(f"  → 필드 {raw_fields - trim_fields}개 제거, 문자 수 {1 - trim_chars / raw_chars:.0%} 절감")
    print(f"  유지한 필드: {', '.join(trimmed)}")
    print()
    print("  ※ 툴을 4번 호출하는 세션이면 이 차이가 4배로 누적된다 —")
    print("     '한 번은 괜찮다'가 아니라 '누적되기 전에 자른다'가 원칙.")

    print()
    print("=" * 60)
    print("[2] 라이브 확인 — 트리밍된 5개 필드만으로 판단이 되는가")
    print(f"입력: {json.dumps(trimmed, ensure_ascii=False)}\n")
    decision = ask_refund_decision(trimmed)
    print(f"  판단: {decision}")
    print()
    print("  확인할 점: 제거한 35개 필드(운송장·결제 BIN·UTM 등)는 애초에")
    print("  환불 판단의 근거가 아니었다 — 관련성 없는 토큰을 지불하지 않은 것.")

    print(
        "\n교훈: 툴 결과는 '누적되기 전에' 관련 필드만 트리밍한다. "
        "나중에 다른 필드가 필요하면 다시 조회하는 게(적시 검색) 40필드를 계속 들고 다니는 것보다 싸다. "
        "다만 재조회가 불가능한 일회성 데이터는 트리밍 대상에서 제외해야 한다 (Task 5.1)."
    )
