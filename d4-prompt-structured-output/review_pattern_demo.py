"""D4 실습 — 자기 리뷰 vs 독립 인스턴스 리뷰 (Ch14, 샘플 37·38).

시험 D4 핵심: 같은 대화(방금 자신이 만든 결과물)를 이어서 리뷰하면 스스로의
판단·프레이밍을 그대로 이어받아 같은 실수를 놓치기 쉽다(자기 리뷰의 한계).
반면 **독립적인 새 인스턴스**(코드만 넘기고 "누가 언제 왜 짰는지" 맥락을 주지
않음)는 편향 없이 코드 자체만 보고 판단한다.

주의: 이 데모는 결정론적으로 재현되지 않는다(모델·실행마다 다를 수 있음).
핵심은 결과의 절대적 우열이 아니라 "독립 인스턴스가 구조적으로 편향이 적다"는 원칙.

실행: practice/ 에서  python d4-prompt-structured-output/review_pattern_demo.py
"""
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from shared.bedrock_client import DEFAULT_MODEL, get_client  # noqa: E402

client = get_client()

# 일부러 넣은 버그: range(1, n)은 n을 제외 → "1부터 n까지(n 포함) 합"에서 n이 빠지는 off-by-one
BUGGY_CODE = """def sum_up_to(n):
    \"\"\"1부터 n까지(n 포함)의 합을 구한다.\"\"\"
    total = 0
    for i in range(1, n):
        total += i
    return total
"""

BUG_KEYWORDS = ("off-by-one", "off by one", "range(1, n", "n을 제외", "n이 빠짐", "n 포함", "range(1, n+1)")
RUNS = 3


def catches_bug(review_text):
    lowered = review_text.lower()
    return any(k.lower() in lowered for k in BUG_KEYWORDS)


def self_review():
    """같은 대화 흐름 안에서 '내가 방금 짠 코드'라는 프레이밍으로 리뷰."""
    messages = [
        {"role": "user", "content": "1부터 n까지(n 포함)의 합을 구하는 함수를 짜줘."},
        {"role": "assistant", "content": f"```python\n{BUGGY_CODE}```\n요청하신 함수입니다."},
        {"role": "user", "content": "방금 네가 짠 이 코드, 버그 있는지 스스로 리뷰해줘."},
    ]
    resp = client.messages.create(model=DEFAULT_MODEL, max_tokens=512, messages=messages)
    return "".join(b.text for b in resp.content if b.type == "text")


def independent_review():
    """맥락 없는 새 호출 — '누가 언제 왜 짰는지' 정보 없이 코드만 리뷰."""
    resp = client.messages.create(
        model=DEFAULT_MODEL, max_tokens=512,
        messages=[{"role": "user", "content": f"다음 코드를 리뷰해서 버그를 찾아줘:\n```python\n{BUGGY_CODE}```"}],
    )
    return "".join(b.text for b in resp.content if b.type == "text")


if __name__ == "__main__":
    print(f"버그 코드:\n{BUGGY_CODE}")
    print(f"({RUNS}회씩 실행 — 버그 키워드 언급 여부로 판정, 결과는 모델·실행마다 달라질 수 있음)\n")

    self_results = Counter(catches_bug(self_review()) for _ in range(RUNS))
    indep_results = Counter(catches_bug(independent_review()) for _ in range(RUNS))

    print(f"자기 리뷰(같은 대화 이어서)   → 버그 발견 {self_results.get(True, 0)}/{RUNS}")
    print(f"독립 인스턴스 리뷰(새 호출)   → 버그 발견 {indep_results.get(True, 0)}/{RUNS}")

    print(
        "\n교훈: 리뷰 품질을 높이려면 자기 리뷰보다 독립 인스턴스 리뷰가 구조적으로 유리하다 "
        "(같은 편향을 공유하지 않으므로) — 멀티패스 리뷰는 개별 파일 → 크로스파일 순으로 (Ch14, 샘플 37·38·39)."
    )
