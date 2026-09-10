# 강의용 최소 예제 — 에이전트 vs 하네스 에이전트

실습 레포(`harness_agent`) 전체를 나누지 않고, **같은 과업을 세 번** 돌리는 파일 하나다.
세 번 모두 실제 Bedrock(Claude) 모델을 호출하며, 차이는 오직 호출을 감싸는 **바깥 장치(하네스)의 유무**다.

과업: `orders.txt` 숫자 합계를 구해 `total.txt`에 저장한다.

| 모드 | 무엇을 보여 주나 | 결과 |
|---|---|---|
| `naked` | 모델 한 번 호출, 도구 없음 | 말은 한다. 파일은 안 생긴다. |
| `naive` | 생각-도구-관찰 루프만 | 에이전트처럼 보이지만, 에러를 분류하지 않고 raw로 창에 쌓아 같은 실수를 반복할 수 있다. |
| `harness` | 같은 루프 + 바깥 장치 | 상태를 `run_state.json`에 남기고, 에러를 분류하고, 쓰기는 승인 후에, 턴 수에 멈춘다. |

세 모드 모두 실제 모델을 호출하므로 **Bedrock 키가 필요하다**.

## 사전 준비

`practice/shared/bedrock_client.py`(다른 실습 예제와 동일한 `AnthropicBedrock` 클라이언트)를 재사용한다.
실습 환경이 이미 세팅돼 있다면(루트 `README.md` 참고) 아래는 확인만 하면 된다.

```bash
source ../.venv/bin/activate               # practice/.venv, mini_harness_example/ 기준 경로
pip install "anthropic[bedrock]"           # 없다면 설치
../shared/verify_bedrock.sh                # 키/리전/모델 검증
```

환경변수(`practice/shared/.env` 또는 `practice/.env`):
- `AWS_BEARER_TOKEN_BEDROCK` — Bedrock API 키(베어러 토큰)
- `AWS_REGION` — 기본 `ap-northeast-2`
- `BEDROCK_MODEL_ID` 또는 `ANTHROPIC_MODEL` — 미지정 시 기본값(`apac.anthropic.claude-3-haiku-20240307-v1:0`) 사용

## 실행

> ⚠️ `python mini_harness_example/` 처럼 **디렉토리를 직접 실행하면 안 된다** — 안에 `__main__.py`가 없어서 에러가 난다.
> 항상 `mini_harness.py` **파일 경로**를 지정하거나, `cd`로 폴더에 들어간 뒤 실행한다.

`practice/` 루트에서 실행하는 경우 (`cd` 없이):
```bash
source .venv/bin/activate
python mini_harness_example/mini_harness.py           # naked / naive / harness 연속
python mini_harness_example/mini_harness.py naked
python mini_harness_example/mini_harness.py naive
python mini_harness_example/mini_harness.py harness
```

`mini_harness_example/` 폴더로 이동해서 실행하는 경우:
```bash
cd mini_harness_example
python mini_harness.py           # naked / naive / harness 연속
python mini_harness.py naked
python mini_harness.py naive
python mini_harness.py harness
python mini_harness.py demo      # 강의 시연용 4단계 (아래 참고)
```

## 라이브 데모 (`demo` 모드) — "휘발 / 방치 / 중단·기록"을 눈으로 확인

`naked`/`naive`/`harness`만 따로 보면 차이가 잘 안 느껴진다. `demo` 모드는 같은 실패를 세 방식에 나란히 흘려보내 **결과의 차이**를 직접 보여준다.

```bash
python mini_harness.py demo
```

| 단계 | 무엇을 하나 | 학생에게 강조할 포인트 |
|---|---|---|
| 1. naked 휘발 | "숫자 기억해 둬"라고 한 뒤, **완전히 새 호출**로 "방금 알려준 합을 말해줘"라고 물음 | 2번째 호출은 1번째 대화를 전혀 모른다 — 매 호출은 독립적인 messages 리스트다. |
| 2. naive 방치 | 숫자가 하나도 없는 `orders_broken.txt`로 `sum_numbers`를 확정적으로 실패시킴 | 에러가 나도 프로그램이 멈추지 않고 다음 턴으로 넘어간다. 실행이 끝나도 `run_state.json`이 **존재하지 않는다** — 무슨 일이 있었는지 기록이 안 남는다. |
| 3. harness 중단 | 같은 `orders_broken.txt`로 harness를 돌림 | `classify_error`가 `bad_input`으로 분류해 **같은 도구를 다시 시도하지 않고 즉시 멈춘다**. 그리고 이 판단이 `run_state.json`에 **남는다** — 데모 중 실제로 `cat mini_harness_example/run_state.json` 을 열어서 보여줘도 좋다. |
| 4. harness 회복 | 정상 파일로 harness를 다시 돌림 | 같은 `run_state.json`이 성공 기록으로 **덮어써진다** — 상태가 모델 머릿속이 아니라 파일에 있으니, 프로세스가 끝나도·다른 터미널에서도 그대로 읽을 수 있다. |

`orders_broken.txt`는 첫 실행 시 자동 생성된다(`재고없음\n기록없음\n` — 숫자가 없어 `sum_numbers`가 항상 `ValueError`를 낸다).

## 코드에서 볼 위치

1. `TOOLS` — 모델이 아니라 런타임이 실행
2. `BedrockModel` — 실제 Claude(Bedrock) 호출을 `next_action(task, observation)` 인터페이스로 감싼 것. `messages.create` 결과의 `stop_reason`(`tool_use`/`end_turn`)으로 다음 행동을 판단
3. `run_naked` — 한 턴, 도구 없이 호출
4. `run_naive` — 루프만. `except`에서 원본 에러를 그대로 observation에 넣음 (에러 분류 없음)
5. `run_harness` — `HarnessState.save`, `classify_error`, `max_steps`, write ASK/ALLOW
6. `demo_naked_amnesia` / `demo_naive_error` / `demo_harness_error` / `demo_harness_recover` — `demo` 모드가 순서대로 호출하는 대조 시연 함수
7. `create_agent(...)` 같은 프레임워크는 없다. 강의 공식만 재현한다.

## 학생에게 한 줄

에이전트는 목표를 향해 도구를 고르는 루프다.  
하네스 에이전트는 그 루프가 기억하고, 실패를 분류하고, 위험한 쓰기를 묻고, 턴 수에 멈추도록 **바깥을 붙인** 에이전트다.
