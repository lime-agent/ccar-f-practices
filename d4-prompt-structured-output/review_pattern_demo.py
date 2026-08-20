"""D4 실습 — 리뷰 아키텍처 (Ch14, 샘플 37·38·39).

시험 D4 핵심 세 가지:
  1) 자기 리뷰 < 독립 인스턴스 리뷰 — 같은 대화에서 이어서 리뷰하면 생성 당시
     편향을 공유해 같은 실수를 놓친다. 코드만 넘긴 새 호출이 구조적으로 유리하다.
  2) 멀티패스 — 파일이 많으면 한 pass에 몰아넣지 말고, 개별 파일(로컬) →
     별도 인스턴스의 크로스파일 통합 순서로 나눈다 (샘플 39).
  3) 신뢰도 라우팅 — 이슈에 0.0–1.0을 붙이고 ≥0.8 자동 / 0.4–0.8 인간 / <0.4 무시.

Batch API(14.1)는 Anthropic 1st-party 전용이라 Bedrock 키로는 호출하지 않는다.
특성만 기억: 50% 절감 · 최대 24h · SLA 없음 → 야간 배치만, pre-merge는 실시간.

주의: 라이브 리뷰는 결정론적으로 재현되지 않는다(모델·실행마다 다를 수 있음).
핵심은 결과의 절대적 우열이 아니라 구조(독립 인스턴스·패스 분리·라우팅 임계값)다.

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

# 2파일 PR — 각 파일만 보면 그럴듯하고, 나란히 봐야 세율 불일치가 보인다 (샘플 39).
PR_FILES = {
    "pricing.py": (
        "TAX_RATE = 0.10\n"
        "def tax(amount):\n"
        "    return amount * TAX_RATE\n"
    ),
    "checkout.py": (
        "def checkout(price):\n"
        "    tax = price * 0.08\n"
        "    return price + tax\n"
    ),
}

BUG_KEYWORDS = ("off-by-one", "off by one", "range(1, n", "n을 제외", "n이 빠짐", "n 포함", "range(1, n+1)")
RUNS = 3
# 교재 예시 문구는 "0.3 미만은 보고하지 말 것"도 있지만, 라우팅 버킷 경계는 0.8 / 0.4.
# 모델 설명도 이 경계에 맞춘다 — 점수를 매기는 쪽과 나누는 쪽이 어긋나면 수업에서 혼란이 난다.
AUTO_MIN = 0.8
HUMAN_MIN = 0.4

CONFIDENCE_TOOL = [{
    "name": "submit_review",
    "description": "코드 리뷰 이슈와 각 이슈의 신뢰도(0.0-1.0)를 제출한다.",
    "input_schema": {
        "type": "object",
        "properties": {
            "issues": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "confidence": {
                            "type": "number",
                            "description": (
                                "1.0=확실한 버그(재현 가능), 0.8 이상=높은 확률(자동 처리), "
                                "0.4 이상 0.8 미만=의심(인간 검토), 0.4 미만=가능성 낮음(보고 생략)"
                            ),
                        },
                    },
                    "required": ["title", "confidence"],
                },
            },
        },
        "required": ["issues"],
    },
}]


def _text(resp):
    return "".join(b.text for b in resp.content if b.type == "text")


def catches_bug(review_text):
    lowered = review_text.lower()
    return any(k.lower() in lowered for k in BUG_KEYWORDS)


def _compact(text):
    return "".join(text.lower().split())


def catches_tax_mismatch(text):
    """Pass 2가 심은 버그(0.10 vs 0.08)를 말했는지. 우리 코드가 판정한다."""
    t = _compact(text)
    has_10 = "0.10" in t or "10%" in t or "10퍼" in t
    has_08 = "0.08" in t or "8%" in t or "8퍼" in t
    return has_10 and has_08


def _one_line(text, limit=220):
    line = " ".join(text.split())
    return line if len(line) <= limit else line[:limit] + "..."


def self_review():
    """같은 대화 흐름 안에서 '내가 방금 짠 코드'라는 프레이밍으로 리뷰."""
    messages = [
        {"role": "user", "content": "1부터 n까지(n 포함)의 합을 구하는 함수를 짜줘."},
        {"role": "assistant", "content": f"```python\n{BUGGY_CODE}```\n요청하신 함수입니다."},
        {"role": "user", "content": "방금 네가 짠 이 코드, 버그 있는지 스스로 리뷰해줘."},
    ]
    resp = client.messages.create(model=DEFAULT_MODEL, max_tokens=512, messages=messages)
    return _text(resp)


def independent_review(code=None):
    """맥락 없는 새 호출 — '누가 언제 왜 짰는지' 정보 없이 코드만 리뷰."""
    snippet = BUGGY_CODE if code is None else code
    resp = client.messages.create(
        model=DEFAULT_MODEL, max_tokens=512,
        messages=[{"role": "user", "content": f"다음 코드를 리뷰해서 버그를 찾아줘:\n```python\n{snippet}```"}],
    )
    return _text(resp)


def analyze_single_file(path, content):
    """Pass 1: 파일 하나만 보고 로컬 이슈. 다른 파일·작성 맥락은 안 넣는다."""
    resp = client.messages.create(
        model=DEFAULT_MODEL, max_tokens=512,
        messages=[{
            "role": "user",
            "content": (
                f"파일 `{path}` 만 보고, 이 파일 안의 동작 이슈만 한두 줄로 말해라. "
                "네이밍/스타일은 생략. 다른 파일은 존재하지 않는다. 추측 금지.\n```python\n"
                f"{content}```"
            ),
        }],
    )
    return _text(resp)


def analyze_cross_file_issues(pr_files, file_issues):
    """Pass 2: 별도 인스턴스. 소스를 나란히 본다(요약만 주면 숫자가 빠져 불일치를 못 찾음)."""
    sources = "\n\n".join(
        f"=== {path} (소스) ===\n```python\n{content}```"
        for path, content in pr_files.items()
    )
    local = "\n\n".join(
        f"=== {path} (Pass 1 로컬 리뷰, 참고) ===\n{result}"
        for path, result in file_issues.items()
    )
    resp = client.messages.create(
        model=DEFAULT_MODEL, max_tokens=1024,
        messages=[{
            "role": "user",
            "content": (
                "같은 PR의 파일 소스다. Pass 1은 파일별로만 봤다. "
                "너는 소스를 나란히 보고, 파일 사이에만 보이는 불일치를 찾아라. "
                "없는 함수 호출·없는 import는 지어내지 마라.\n\n"
                f"{sources}\n\n"
                f"{local}\n\n"
                "숫자(상수 vs 리터럴)가 파일마다 다른지 소스에서 직접 확인하라."
            ),
        }],
    )
    return _text(resp)


def review_large_pr(pr_files):
    """멀티패스: 개별 파일 → 크로스파일 통합 (한 pass에 몰아넣지 않음)."""
    print("  심은 버그: pricing.py TAX_RATE=0.10 인데 checkout.py 는 0.08 리터럴.")
    print("  판정: Pass 2 텍스트에 두 숫자가 함께 나오면 YES (우리 코드가 키워드로 확인).\n")
    file_issues = {}
    for path, content in pr_files.items():
        print(f"  Pass 1 로컬: {path}")
        file_issues[path] = analyze_single_file(path, content)
        print(f"    {_one_line(file_issues[path])}")
    print("  Pass 2 크로스파일 (독립 인스턴스, 소스 포함)")
    integration = analyze_cross_file_issues(pr_files, file_issues)
    print(f"    {_one_line(integration, 360)}")
    found = catches_tax_mismatch(integration)
    print(f"  → Pass 2가 세율 불일치(0.10 vs 0.08)를 말했는가? {'YES' if found else 'NO'}")
    if not found:
        print("    (이번 실행은 모델이 숫자를 못 짚음. 패스가 나뉜 구조는 그대로고, 판정만 실패한 것.)")
    return file_issues, integration


def route_by_confidence(issues):
    """Ch14 신뢰도 라우팅. 임계값은 우리 코드가 적용한다(모델이 버킷을 고르지 않음)."""
    auto_flagged, human_review, ignored = [], [], []
    for issue in issues:
        c = issue["confidence"]
        if c >= AUTO_MIN:
            auto_flagged.append(issue)
        elif c >= HUMAN_MIN:
            human_review.append(issue)
        else:
            ignored.append(issue)
    return {
        "auto_flagged": auto_flagged,
        "human_review": human_review,
        "ignored": ignored,
    }


def print_routed(routed):
    labels = (
        ("auto_flagged", f"자동 처리 (>= {AUTO_MIN})"),
        ("human_review", f"인간 검토 ({HUMAN_MIN}–{AUTO_MIN})"),
        ("ignored", f"무시 (< {HUMAN_MIN})"),
    )
    for key, label in labels:
        items = routed[key]
        print(f"  {label}: {len(items)}건")
        for issue in items:
            print(f"    - {issue['title']} (confidence={issue['confidence']})")


def show_routing_fixtures():
    """모델이 어떤 점수를 내든, 라우팅 분기는 픽스처로 항상 보여 준다."""
    print("[신뢰도 라우팅 시연] 모델 호출 없이 route_by_confidence()만 적용\n")
    fixtures = [
        {"title": "range(1, n) off-by-one — n이 합에서 빠짐", "confidence": 1.0},
        {"title": "경계: confidence=0.8 → 자동 처리", "confidence": 0.8},
        {"title": "함수명 sum_up_to가 모호함", "confidence": 0.55},
        {"title": "경계: confidence=0.4 → 인간 검토", "confidence": 0.4},
        {"title": "변수명을 total 대신 acc가 나을 수 있음", "confidence": 0.2},
    ]
    print_routed(route_by_confidence(fixtures))
    print()


def review_with_confidence(code):
    """라이브: 모델은 이슈+confidence만 제출, 버킷 분류는 우리 코드."""
    resp = client.messages.create(
        model=DEFAULT_MODEL, max_tokens=512,
        tools=CONFIDENCE_TOOL,
        tool_choice={"type": "tool", "name": "submit_review"},
        messages=[{
            "role": "user",
            "content": (
                "코드를 리뷰하고 각 이슈에 신뢰도(0.0-1.0)를 붙여 submit_review로 제출해라.\n"
                "1.0: 확실한 버그 / 0.8 이상: 높은 확률 / "
                "0.4 이상 0.8 미만: 의심 / 0.4 미만: 가능성 낮음.\n"
                f"```python\n{code}```"
            ),
        }],
    )
    tool_block = next(b for b in resp.content if b.type == "tool_use")
    issues = tool_block.input.get("issues") or []
    print(f"  모델이 제출한 이슈 {len(issues)}건")
    print_routed(route_by_confidence(issues))
    print("  (라이브 이슈 제목·점수는 실행마다 다름. 볼 것은 우리 코드가 0.8/0.4로 버킷을 나눈다는 구조.)")


if __name__ == "__main__":
    print("=" * 60)
    print("[1] 자기 리뷰 vs 독립 인스턴스 (샘플 37·38)")
    print(f"버그 코드:\n{BUGGY_CODE}")
    print(f"({RUNS}회씩 실행 — 버그 키워드 언급 여부로 판정, 결과는 모델·실행마다 달라질 수 있음)\n")

    self_results = Counter(catches_bug(self_review()) for _ in range(RUNS))
    indep_results = Counter(catches_bug(independent_review()) for _ in range(RUNS))

    print(f"자기 리뷰(같은 대화 이어서)   → 버그 발견 {self_results.get(True, 0)}/{RUNS}")
    print(f"독립 인스턴스 리뷰(새 호출)   → 버그 발견 {indep_results.get(True, 0)}/{RUNS}")
    if self_results.get(True, 0) == RUNS and indep_results.get(True, 0) == RUNS:
        print(
            "  (이번 실행은 양쪽이 모두 찾음 — off-by-one이 모델에게 너무 분명해서다. "
            "시험 포인트는 점수 우열이 아니라, 자기 리뷰는 생성 편향을 구조적으로 공유한다는 점.)"
        )

    print()
    print("=" * 60)
    print("[2] 멀티패스 PR 리뷰 (샘플 39) — 개별 파일 → 크로스파일")
    print("기대: Pass 1은 파일 하나라 세율 충돌을 단정할 수 없고, Pass 2가 0.10 vs 0.08을 집어야 한다.\n")
    review_large_pr(PR_FILES)

    print()
    print("=" * 60)
    print("[3] 신뢰도 기반 라우팅")
    show_routing_fixtures()
    print("[라이브] submit_review + 우리 코드가 버킷 분류")
    review_with_confidence(BUGGY_CODE)

    print(
        "\n교훈: 리뷰는 자기 리뷰보다 독립 인스턴스가 구조적으로 유리하고, "
        "멀티패스는 개별 파일 → 크로스파일 순이며, 신뢰도 점수로 인간 검토를 우선순위화한다. "
        "Batch API는 여기선 호출하지 않음(Bedrock 불가) — 야간 대량 작업만 적합, "
        "개발자가 기다리는 pre-merge 체크는 실시간 API가 필수다."
    )
