"""D1 실습 — 병렬 서브에이전트 '흉내' (AnthropicBedrock + 파이썬 스레드).

⚠️ 이건 개념(동시성) 체감용 '흉내'다. 시험 정답 메커니즘은 아니다.
    실제/시험 정답: 코디네이터가 한 응답에서 Task 를 여러 개 호출 → 런타임 병렬.
    (그 '진짜' 버전은 parallel_subagents_agentsdk.py)
    "별도 스레드/오케스트레이터 레이어" 방식은 공식 샘플 Q11의 오답 보기와 닮았으니
    "정답"으로 외우지 말 것.

실행: practices/ 디렉토리에서  python d1-agentic-orchestration/parallel_subagents.py
"""
import os
import sys
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from shared.bedrock_client import DEFAULT_MODEL, get_client  # noqa: E402

client = get_client()


def run_subagent(task):
    resp = client.messages.create(
        model=DEFAULT_MODEL,
        max_tokens=400,
        system=f"너는 '{task['role']}' 전문가다. 3문장 이내로 답하라.",
        messages=[{"role": "user", "content": task["description"]}],
    )
    return task["role"], "".join(b.text for b in resp.content if b.type == "text")


TASKS = [
    {"role": "시장분석", "description": "AI 코딩툴 시장 규모와 성장률 요약"},
    {"role": "경쟁분석", "description": "상위 경쟁사 3곳과 강약점 요약"},
    {"role": "규제분석", "description": "AI 관련 최신 규제 이슈 요약"},
]

if __name__ == "__main__":
    with ThreadPoolExecutor(max_workers=len(TASKS)) as ex:
        for role, out in ex.map(run_subagent, TASKS):
            print(f"\n[{role}]\n{out}")
