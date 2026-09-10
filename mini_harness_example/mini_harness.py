"""
mini_harness.py — 강의용 최소 예제 (실제 Bedrock(Claude) 모델 사용)

같은 과업을 세 단계로 돌린다. 세 단계 모두 실제 Bedrock 모델을 호출하며,
차이는 오직 그 호출을 감싸는 바깥 장치(하네스)의 유무다.

  1) naked      모델에게 한 번 묻고 끝
  2) naive      생각-도구-관찰 루프. 바깥 장치가 없어 에러를 raw로 창에 쌓는다
  3) harness    같은 루프 + 상태 저장 + 에러 정리 + 최대 턴 + 쓰기 승인

사전 준비: shared/.env 에 AWS_BEARER_TOKEN_BEDROCK 필요 (../shared/verify_bedrock.sh 로 검증)

실행:
  python mini_harness.py
  python mini_harness.py naked
  python mini_harness.py naive
  python mini_harness.py harness
  python mini_harness.py demo     # 강의 시연용: 휘발 → 방치 → 중단 → 기록·회복 4단계 대조
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

# shared.bedrock_client 를 쓴다 (practice/ 를 import 경로에 추가)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from shared.bedrock_client import DEFAULT_MODEL, get_client  # noqa: E402

STATE_PATH = Path(__file__).parent / "run_state.json"
ORDERS_PATH = Path(__file__).parent / "orders.txt"
ORDERS_BROKEN_PATH = Path(__file__).parent / "orders_broken.txt"
TOTAL_PATH = Path(__file__).parent / "total.txt"

# 절대경로를 프롬프트에 직접 박아 둔다 — "orders.txt"처럼 상대경로만 주면
# practice/ 루트에서 실행했을 때 모델이 cwd 기준으로 잘못된 경로를 호출할 수 있다.
TASK = f"{ORDERS_PATH} 파일에서 숫자 합계를 구하고 결과를 {TOTAL_PATH} 파일에 저장해 줘"
TASK_BROKEN = f"{ORDERS_BROKEN_PATH} 파일에서 숫자 합계를 구하고 결과를 {TOTAL_PATH} 파일에 저장해 줘"


# ---------------------------------------------------------------------------
# 도구 — 모델이 직접 실행하지 않고, 런타임이 대신 실행한다
# ---------------------------------------------------------------------------

def tool_read_file(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def tool_sum_numbers(text: str) -> str:
    numbers = [int(tok) for tok in text.replace(",", " ").split() if tok.isdigit()]
    if not numbers:
        raise ValueError("숫자는 비어 있고 구조는 그대로다. 같은 덧셈을 반복해도 답이 안 나온다.")
    return str(sum(numbers))


def tool_write_file(path: str, content: str) -> str:
    Path(path).write_text(content, encoding="utf-8")
    return f"wrote {path}"


TOOLS = {
    "read_file": tool_read_file,
    "sum_numbers": tool_sum_numbers,
    "write_file": tool_write_file,
}


# ---------------------------------------------------------------------------
# BedrockModel — 실제 Claude(Bedrock)에게 next_action(task, observation) 인터페이스로 다음 행동을 묻는다
# ---------------------------------------------------------------------------

TOOL_SCHEMA = [
    {
        "name": "read_file",
        "description": "경로의 텍스트 파일을 읽어 내용을 돌려준다.",
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string", "description": "읽을 파일 경로"}},
            "required": ["path"],
        },
    },
    {
        "name": "sum_numbers",
        "description": "텍스트 안의 숫자를 모두 더한 합계를 문자열로 돌려준다.",
        "input_schema": {
            "type": "object",
            "properties": {"text": {"type": "string", "description": "숫자가 섞인 텍스트"}},
            "required": ["text"],
        },
    },
    {
        "name": "write_file",
        "description": "경로에 텍스트 내용을 저장한다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "저장할 파일 경로"},
                "content": {"type": "string", "description": "저장할 내용"},
            },
            "required": ["path", "content"],
        },
    },
]


class BedrockModel:
    """실제 Claude(Bedrock)를 호출하며 next_action(task, observation) 인터페이스를 제공한다."""

    def __init__(self, task: str) -> None:
        self.client = get_client()
        self.model_id = DEFAULT_MODEL
        self.messages: list[dict] = [{"role": "user", "content": task}]
        self.pending_tool_use_id: str | None = None

    def next_action(self, task: str, observation: str | None) -> dict:
        if self.pending_tool_use_id is not None:
            self.messages.append(
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": self.pending_tool_use_id,
                            "content": observation or "",
                        }
                    ],
                }
            )
            self.pending_tool_use_id = None

        resp = self.client.messages.create(
            model=self.model_id,
            max_tokens=1024,
            tools=TOOL_SCHEMA,
            messages=self.messages,
        )
        self.messages.append({"role": "assistant", "content": resp.content})

        if resp.stop_reason == "tool_use":
            for block in resp.content:
                if block.type == "tool_use":
                    self.pending_tool_use_id = block.id
                    return {"type": "tool", "name": block.name, "args": dict(block.input)}

        text = "".join(b.text for b in resp.content if b.type == "text")
        return {"type": "final", "text": text or f"(stop_reason={resp.stop_reason})"}


# ---------------------------------------------------------------------------
# 1) naked: 한 턴 텍스트. 도구도 상태도 없다
# ---------------------------------------------------------------------------

def ask_once(question: str, max_tokens: int = 256) -> str:
    """도구도 대화 기록도 없는 단발 호출 — 매번 새 messages 리스트로 시작한다."""
    client = get_client()
    resp = client.messages.create(
        model=DEFAULT_MODEL,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": question}],
    )
    return "".join(b.text for b in resp.content if b.type == "text")


def run_naked() -> None:
    print("=== 1. naked LLM ===")
    print(f"task: {TASK}")
    text = ask_once(TASK)
    print(f"model: {text!r}")
    print("사실: 모델을 한 번 호출했을 뿐이다. 도구가 없으니 orders.txt도 total.txt도 건드리지 못한다.")
    print(f"total.txt exists? {TOTAL_PATH.exists()}")


def demo_naked_amnesia() -> None:
    """naked LLM은 대화를 '이어가는 것처럼' 안 보이고, 매 호출이 독립적이라는 걸 직접 보여준다."""
    print("=== 데모 1. naked — 휘발 확인 ===")
    q1 = "다음 숫자를 모두 더해서 기억해 둬: 10, 20, 12. 지금은 합계만 말해."
    print(f"[1번째 호출] Q: {q1}")
    a1 = ask_once(q1)
    print(f"[1번째 호출] A: {a1!r}")

    q2 = "방금 내가 알려준 숫자들의 합을 다시 말해줘."
    print(f"\n[2번째 호출] Q: {q2}")
    a2 = ask_once(q2)
    print(f"[2번째 호출] A: {a2!r}")

    print(
        "\n확인: 2번째 호출은 새 messages 리스트로 시작했다 — 1번째 호출의 내용을 전혀 모른다.\n"
        "      모델 자체엔 기억이 없다. '기억'은 매번 대화 기록을 통째로 다시 넣어줘야 생긴다."
    )


# ---------------------------------------------------------------------------
# 2) naive agent: 루프는 있지만 바깥 장치가 없다
# ---------------------------------------------------------------------------

def run_naive(task: str = TASK, max_steps: int = 8, label: str = "2. naive agent (루프만 있음)") -> None:
    print(f"=== {label} ===")
    model = BedrockModel(task)
    observation = None
    for i in range(1, max_steps + 1):
        action = model.next_action(task, observation)
        print(f"\n[{i}] thought/action = {action}")
        if action["type"] == "final":
            print("final:", action["text"])
            return
        try:
            observation = TOOLS[action["name"]](**action["args"])
            print("observation:", observation)
        except Exception as exc:
            # 바깥 장치가 없어 실패를 분류하지 않고 그대로 창에 쌓는다 — 같은 실수를 반복할 수 있음
            observation = f"{type(exc).__name__}: {exc}\n" + "TRACE " * 20
            print("observation (raw error dumped into context, 계속 진행):")
            print(observation[:200], "...")
    print("stopped: no max-step policy, loop just exhausted")


def demo_naive_error() -> None:
    """숫자가 하나도 없는 파일로 sum_numbers를 확실히 실패시키고, naive가 그래도 계속 진행하는 걸 보여준다."""
    print("=== 데모 2. naive — 에러가 나도 계속 진행 ===")
    if STATE_PATH.exists():
        STATE_PATH.unlink()
    print(f"orders_broken.txt 내용: {ORDERS_BROKEN_PATH.read_text(encoding='utf-8')!r}")
    run_naive(task=TASK_BROKEN, label="데모 2. naive (broken file)")
    print(
        f"\n확인: 이 실행에 대한 기록은 어디에도 안 남았다 — "
        f"run_state.json exists? {STATE_PATH.exists()}\n"
        "      에러가 나도 프로그램은 멈추지 않고 다음 턴으로 넘어갔을 뿐, "
        "그 판단(재시도해도 되는지)은 아무도 하지 않았다."
    )


# ---------------------------------------------------------------------------
# 3) harness agent: 같은 루프 + 바깥 장치
# ---------------------------------------------------------------------------

@dataclass
class HarnessState:
    task: str
    step: int = 0
    log: list[dict] = field(default_factory=list)
    last_obs: str | None = None
    done: bool = False

    def save(self, path: Path = STATE_PATH) -> None:
        path.write_text(json.dumps(self.__dict__, ensure_ascii=False, indent=2), encoding="utf-8")


def classify_error(exc: Exception) -> str:
    """재시도해도 되는 실패와, 같은 호출을 반복하면 안 되는 실패를 나눈다."""
    if isinstance(exc, FileNotFoundError):
        return "missing_file"
    if isinstance(exc, ValueError):
        return "bad_input"
    return "unknown"


def run_harness(
    task: str = TASK,
    max_steps: int = 6,
    auto_approve_write: bool = True,
    label: str = "3. harness agent",
) -> None:
    print(f"=== {label} ===")
    print("장치: state file / error class / max_steps / write gate")

    if not ORDERS_PATH.exists():
        ORDERS_PATH.write_text("10\n20\n12\n", encoding="utf-8")

    state = HarnessState(task=task)
    model = BedrockModel(task)

    for _ in range(max_steps):
        state.step += 1
        action = model.next_action(state.task, state.last_obs)
        record = {"step": state.step, "action": action}
        print(f"\n[{state.step}] {action}")

        if action["type"] == "final":
            state.done = True
            record["result"] = action["text"]
            state.log.append(record)
            state.save()
            print("final:", action["text"])
            print("saved:", STATE_PATH)
            print("total.txt:", TOTAL_PATH.read_text(encoding="utf-8") if TOTAL_PATH.exists() else "(none)")
            return

        name = action["name"]
        args = action["args"]

        # Guardrail: 파일 쓰기는 승인 후에만
        if name == "write_file":
            print(f"  ASK: write {args.get('path')} ?")
            if not auto_approve_write:
                print("  DENY — harness blocked the write")
                state.last_obs = "write denied by harness"
                record["gate"] = "deny"
                state.log.append(record)
                state.save()
                continue
            print("  ALLOW")
            record["gate"] = "allow"

        try:
            obs = TOOLS[name](**args)
            state.last_obs = obs
            record["obs"] = obs
        except Exception as exc:
            kind = classify_error(exc)
            # 스택을 창에 넣지 않고, 종류만 관찰로 남긴다
            state.last_obs = f"error_class={kind}: {exc}"
            record["obs"] = state.last_obs
            record["retry_ok"] = kind not in {"bad_input", "missing_file"}
            print("  classified:", state.last_obs)
            if not record["retry_ok"]:
                print("  STOP retry — same tool call will not succeed")
                state.log.append(record)
                state.save()
                return

        state.log.append(record)
        state.save()

    print("STOP: max_steps reached (harness, not the model)")
    state.save()


def _print_state_file() -> None:
    if STATE_PATH.exists():
        print(STATE_PATH.read_text(encoding="utf-8"))
    else:
        print("(no state file)")


def demo_harness_error() -> None:
    """같은 깨진 파일로 harness를 돌려, 실패가 즉시 멈추고 run_state.json에 남는 걸 보여준다."""
    print("=== 데모 3. harness — 에러를 분류하고 즉시 멈춘다 ===")
    if STATE_PATH.exists():
        STATE_PATH.unlink()
    run_harness(task=TASK_BROKEN, label="데모 3. harness (broken file)")
    print(f"\nrun_state.json exists? {STATE_PATH.exists()}  — 프로세스가 끝나도 파일은 그대로 남는다.")
    print("run_state.json 내용:")
    _print_state_file()
    print(
        "\n확인: naive와 똑같은 ValueError를 만났지만, classify_error가 'bad_input'으로 분류해서\n"
        "      같은 도구 호출을 또 시도하지 않고 즉시 멈췄다. 그리고 이 판단 자체가 파일로 남았다."
    )


def demo_harness_recover() -> None:
    """이번엔 정상 파일로 harness를 다시 돌려, 같은 run_state.json이 성공 기록으로 덮어써지는 걸 보여준다."""
    print("=== 데모 4. harness — 같은 상태 파일이 성공 기록으로 갱신된다 ===")
    if TOTAL_PATH.exists():
        TOTAL_PATH.unlink()
    run_harness(task=TASK, label="데모 4. harness (정상 파일)")
    print("\nrun_state.json 내용 (덮어써짐):")
    _print_state_file()
    print(
        "\n확인: 같은 파일(run_state.json)이 이번엔 성공 기록으로 덮어써졌다.\n"
        "      상태가 모델의 머릿속이 아니라 바깥 파일에 있으니, 다른 터미널·다음 실행에서도 그대로 읽을 수 있다."
    )


def run_demo() -> None:
    """강의용 시연 순서 — naked 휘발 → naive 방치 → harness 중단 → harness 기록·회복."""
    if not ORDERS_BROKEN_PATH.exists():
        ORDERS_BROKEN_PATH.write_text("재고없음\n기록없음\n", encoding="utf-8")

    demo_naked_amnesia()
    print("\n" + "=" * 70 + "\n")
    demo_naive_error()
    print("\n" + "=" * 70 + "\n")
    demo_harness_error()
    print("\n" + "=" * 70 + "\n")
    demo_harness_recover()


def main() -> None:
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"
    if not ORDERS_PATH.exists():
        ORDERS_PATH.write_text("10\n20\n12\n", encoding="utf-8")
    if not ORDERS_BROKEN_PATH.exists():
        ORDERS_BROKEN_PATH.write_text("재고없음\n기록없음\n", encoding="utf-8")

    if mode == "demo":
        run_demo()
        return

    if mode in {"all", "naked"}:
        run_naked()
        print()
    if mode in {"all", "naive"}:
        run_naive()
        print()
    if mode in {"all", "harness"}:
        if TOTAL_PATH.exists():
            TOTAL_PATH.unlink()
        run_harness()


if __name__ == "__main__":
    main()
