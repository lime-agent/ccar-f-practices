"""D2 실습 — 구조화된 툴 에러 응답 (Task 2.2).

시험 D2 핵심: 툴이 실패를 알릴 때 '구조화된 에러'를 돌려줘야 에이전트가
올바른 복구 판단(재시도 vs 중단)을 한다. 균일한 "Operation failed"는 판단 불가.

에러 계약: isError · errorCategory · isRetryable · message
  - transient   : 재시도 가능 (타임아웃, 일시 서버오류)
  - validation  : 재시도 무의미 (입력 형식 오류)
  - business    : 재시도 무의미 (정책 위반)
  - permission  : 재시도 무의미 (권한 없음)

이 데모는 모델 없이 '에러 계약 + 재시도 판단'을 결정론적으로 보여준다.
(에이전트에서는 모델이 isRetryable/errorCategory 를 보고 같은 판단을 내린다.)

실행: practices/ 에서  python d2-tools-mcp/structured_tool_errors.py
"""

RETRYABLE = {"transient": True, "validation": False, "business": False, "permission": False}


def structured_error(category, message):
    return {"isError": True, "errorCategory": category, "isRetryable": RETRYABLE[category], "message": message}


# 결제: 게이트웨이가 처음엔 일시 오류(transient) → 재시도하면 성공
_attempts = {"charge": 0}


def charge_payment(amount):
    _attempts["charge"] += 1
    if _attempts["charge"] < 2:
        return structured_error("transient", "결제 게이트웨이 일시 오류(잠시 후 재시도)")
    return {"isError": False, "ok": True, "amount": amount}


# 환불: $500 초과는 정책 위반(business) → 재시도해도 소용없음
def process_refund(amount):
    if amount > 500:
        return structured_error("business", "$500 초과 환불은 수동 승인 필요")
    return {"isError": False, "ok": True, "amount": amount}


def call_with_retry(fn, *args, max_retries=3):
    """isRetryable=True 인 에러만 재시도한다."""
    out = {}
    for i in range(max_retries + 1):
        out = fn(*args)
        if not out.get("isError"):
            print(f"  ✅ 성공: {out}")
            return out
        if out.get("isRetryable"):
            print(f"  ↻ 재시도 {i + 1} — [{out['errorCategory']}] {out['message']}")
            continue
        print(f"  ⛔ 중단(재시도 무의미) — [{out['errorCategory']}] {out['message']}")
        return out
    print("  ⛔ 재시도 한도 초과")
    return out


if __name__ == "__main__":
    print("[결제] transient 에러 → 재시도로 성공")
    call_with_retry(charge_payment, 100)
    print("\n[환불 $800] business 에러 → 재시도 안 함")
    call_with_retry(process_refund, 800)
    print("\n교훈: errorCategory + isRetryable 로 '재시도 가능 여부'를 툴이 알려줘야 한다 (Task 2.2).")
