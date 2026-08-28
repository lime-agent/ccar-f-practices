"""D5 실습 — Progressive summarization 위험 vs case facts 블록 (Task 5.1 / Ch15.3).

시험 D5 핵심: 요약을 거듭하면 **수치·백분율·날짜·고객이 명시한 기대치**가
모호한 문장으로 압축된다("고객이 여러 주문에 문제를 제기, 환불 필요" → 처리 불가).
→ 거래 사실을 **요약 히스토리 외부의 지속 "case facts" 블록**으로 빼내
   매 프롬프트에 포함한다.

이론 배경(Context Engineering): 압축은 **반드시 정보 손실을 수반**한다.
그래서 "잃어도 되는 정보"를 미리 정해야 한다 — 수치는 잃어선 안 되는 쪽이다.

이 데모는 세 조건을 같은 질문으로 비교한다:
  (A) 요약만        — 긴 히스토리를 모델이 요약한 것만 주고 질문
  (B) 요약 + case facts — 같은 요약 + 사실 블록을 함께 주고 질문
  (C) 원본 히스토리   — 대조군(상한선). 길지만 사실은 다 있다.
판정은 우리 코드가 한다: 필수 수치가 답변에 그대로 살아있는지 문자열로 확인.

실행: practices/ 에서  python d5-context-reliability/case_facts_block.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from shared.bedrock_client import DEFAULT_MODEL, get_client  # noqa: E402

client = get_client()

# 여러 턴에 걸쳐 사실이 흩어져 있는 고객 지원 대화 (요약 압박이 걸리는 상황)
CONVERSATION = """
[턴 1] 고객: 안녕하세요, 주문 두 개가 문제가 있어서요.
[턴 2] 상담: 네, 주문번호를 알려주시겠어요?
[턴 3] 고객: 하나는 ORD-001인데 키보드가 박스째로 찌그러져 왔어요. 45.99달러요.
[턴 4] 상담: 확인했습니다. 다른 하나는요?
[턴 5] 고객: ORD-002는 배송이 9일 걸렸어요. 원래 이틀이라고 했는데.
        이건 전액은 아니고 120.00달러 중 일부만 보상받으면 됩니다.
[턴 6] 상담: 부분 환불로 접수하겠습니다.
[턴 7] 고객: 그리고 이거 급해요. 영업일 3일 안에 처리돼야 합니다.
        제 고객번호는 CUST-2024-789예요.
[턴 8] 상담: 알겠습니다. 확인 후 연락드리겠습니다.
[턴 9] 고객: 아, ORD-001은 교환이 아니라 환불로 해주세요. 같은 제품 또 오면 곤란해요.
[턴 10] 상담: 네, 환불로 처리하겠습니다.
"""

# 요약 히스토리 '외부'에 유지하는 지속 블록 — 압축 대상이 아니다.
CASE_FACTS = """## CASE FACTS (항상 참조, 압축 금지)
고객 ID: CUST-2024-789
- 주문 ORD-001: $45.99 전액 환불 (제품 손상, 교환 아닌 환불로 확정)
- 주문 ORD-002: $120.00 중 부분 환불 (배송 9일 지연, 약속 2일)
- 총 환불 대상 금액: $45.99 + ORD-002 부분액
- 고객 명시 기한: 영업일 3일 이내
"""

QUESTION = (
    "이 케이스를 처리해야 한다. 다음을 정확히 답하라: "
    "(1) 고객 ID (2) 각 주문번호와 금액 (3) 각각 전액/부분 환불 여부 (4) 고객이 요구한 기한."
)

# 답변에 반드시 살아있어야 하는 사실들 — 우리 코드가 판정한다.
REQUIRED_FACTS = {
    "고객 ID": ("CUST-2024-789",),
    "ORD-001": ("ORD-001",),
    "ORD-001 금액": ("45.99",),
    "ORD-002": ("ORD-002",),
    "ORD-002 금액": ("120",),
    "기한": ("3", "영업일"),
}


def summarize(conversation: str) -> str:
    """상담 히스토리를 요약한다 — 여기서 수치 손실이 일어난다."""
    resp = client.messages.create(
        model=DEFAULT_MODEL,
        max_tokens=300,
        messages=[{
            "role": "user",
            "content": (
                "다음 고객 상담 대화를 3문장 이내로 간결하게 요약하라:\n" + conversation
            ),
        }],
    )
    return "".join(b.text for b in resp.content if b.type == "text").strip()


def answer_from(context_text: str, label: str) -> str:
    """주어진 컨텍스트만 근거로 케이스 질문에 답하게 한다."""
    resp = client.messages.create(
        model=DEFAULT_MODEL,
        max_tokens=400,
        system=(
            "너는 환불 처리 담당자다. 아래 제공된 컨텍스트만 근거로 답하라. "
            "컨텍스트에 없는 값은 추측하지 말고 '정보 없음'이라고 답하라."
        ),
        messages=[{"role": "user", "content": f"[컨텍스트]\n{context_text}\n\n[요청]\n{QUESTION}"}],
    )
    return "".join(b.text for b in resp.content if b.type == "text").strip()


def check_facts(answer: str) -> tuple[int, list[str]]:
    """필수 사실이 답변에 살아있는지 확인. (보존 개수, 누락 항목명)"""
    missing = []
    for name, needles in REQUIRED_FACTS.items():
        if not all(n in answer for n in needles):
            missing.append(name)
    return len(REQUIRED_FACTS) - len(missing), missing


def report(label: str, answer: str) -> int:
    kept, missing = check_facts(answer)
    total = len(REQUIRED_FACTS)
    print(f"\n--- {label} → 사실 보존 {kept}/{total}")
    if missing:
        print(f"    누락: {', '.join(missing)}")
    print(f"    답변: {answer[:300]}{'...' if len(answer) > 300 else ''}")
    return kept


if __name__ == "__main__":
    print("=" * 60)
    print("[0] 요약 생성 — 여기서 무엇이 사라지는지 관찰")
    summary = summarize(CONVERSATION)
    print(f"\n요약문:\n{summary}\n")
    s_kept, s_missing = check_facts(summary)
    print(f"→ 요약문 자체의 사실 보존: {s_kept}/{len(REQUIRED_FACTS)}")
    if s_missing:
        print(f"  요약 단계에서 이미 사라진 것: {', '.join(s_missing)}")

    print()
    print("=" * 60)
    print("[1] 세 조건 비교 — 같은 질문, 다른 컨텍스트")
    kept_a = report("(A) 요약만", answer_from(summary, "A"))
    kept_b = report(
        "(B) 요약 + case facts 블록", answer_from(f"{CASE_FACTS}\n## 요약 히스토리\n{summary}", "B")
    )
    kept_c = report("(C) 원본 히스토리(대조군)", answer_from(CONVERSATION, "C"))

    print()
    print("=" * 60)
    print(f"사실 보존 비교: (A) 요약만 {kept_a} / (B) 요약+casefacts {kept_b} / (C) 원본 {kept_c}")
    if kept_b > kept_a:
        print("→ case facts 블록이 요약 손실을 복구했다 (B > A).")
    elif kept_a == len(REQUIRED_FACTS):
        print("→ 이번 실행은 요약이 운 좋게 수치를 다 담았다(모델·샘플링 변동).")
        print("   핵심은 '운에 맡기지 않는다'는 구조 — case facts는 압축 대상 밖이라 항상 살아남는다.")
    else:
        print("→ 이번 실행에선 차이가 뚜렷하지 않음(모델·샘플링 변동). 구조적 원칙은 동일.")

    print(
        "\n교훈: 요약은 필연적으로 손실을 낸다 — 수치·날짜·번호·명시 기한은 "
        "요약 히스토리 '외부'의 case facts 블록으로 빼서 매 프롬프트에 포함한다. "
        "(B)가 (A)보다 짧은 컨텍스트로 (C)에 가까운 정확도를 낸다는 게 이 패턴의 값이다 (Task 5.1)."
    )
