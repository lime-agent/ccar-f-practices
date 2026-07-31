# CCA-F 실습 모음 (practices)

Claude Certified Architect – Foundations(CCA-F) **핸즈온 실습 코드** 모음.

## 준비 (한 번만)
```bash
cd practices
python3 -m venv .venv           # 최초 1회
source .venv/bin/activate       # 터미널 새로 열 때마다 (프롬프트에 (.venv) 표시)
pip install -r shared/requirements.txt

cp shared/.env.example .env     
nano .env  #.env 열어 AWS_BEARER_TOKEN_BEDROCK 채우기 (⚠️ 커밋 금지!)
AWS_REGION=ap-northeast-2 ./shared/verify_bedrock.sh   # 키 검증(입력값 파일에 안 남김)
```
설치 확인:
```bash
python -c "from anthropic import AnthropicBedrock; print('ok')"
```

## OS별 참고
- **macOS / Linux**: 위 명령 **그대로** 동작 (둘 다 Unix — venv `bin/activate`·`.sh` 실행 동일).
- **Windows**: 활성화 경로가 다름 → `.venv\Scripts\activate`. `verify_bedrock.sh`(.sh)는 Git Bash/WSL 필요(또는 `python -c "from shared.bedrock_client import ping; ping()"`로 검증). → **WSL 권장**(리눅스와 동일해짐).
- 공통 전제: **Python 3.10+** (Tier 2만 Node 18+).

## 준비 단계 두 가지 (Tier)
| Tier | 추가 설치 | 대상 |
|---|---|---|
| **1 (대부분)** | `anthropic[bedrock]` (requirements에 포함) | D1 루프 · D2 · D4 · D5 API 실습 |
| **2 (심화)** | `npm i -g @anthropic-ai/claude-code` + `pip install claude-agent-sdk` | D1 진짜 Task 병렬(`*_agentsdk.py`) · D3(Claude Code) |

> 대부분 실습은 **Tier 1**만으로 됩니다. Claude Code CLI는 진짜 서브에이전트(Task)·D3에만 필요.

## 폴더 (도메인별, 가중치순)
| 폴더 | 도메인 | 가중치 |
|---|---|---|
| `d1-agentic-orchestration/` | Agentic Architecture & Orchestration | 27% |
| `d3-claude-code/` | Claude Code Configuration & Workflows | 20% |
| `d4-prompt-structured-output/` | Prompt Engineering & Structured Output | 20% |
| `d2-tools-mcp/` | Tool Design & MCP Integration | 18% |
| `d5-context-reliability/` | Context Management & Reliability | 15% |

각 폴더 `README.md`에 실습 목표·시드·과제가 있습니다.

## 실행 예 (D1)
```bash
source .venv/bin/activate
python d1-agentic-orchestration/agentic_loop.py            # 에이전틱 루프
python d1-agentic-orchestration/parallel_subagents.py      # 병렬(스레드 흉내)
# (Tier 2) python d1-agentic-orchestration/parallel_subagents_agentsdk.py   # 진짜 Task 병렬
```

## 주의
- **`.env`(실제 키)는 절대 커밋하지 마세요** — `.gitignore`로 제외돼 있습니다.
- 키는 개별 전달받아 각자 로컬 `.env`에만 두세요.
