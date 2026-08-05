# D2 — Tool Design & MCP Integration (18%)

툴을 신뢰성 있게 설계하고, MCP로 외부 시스템을 통합하는 도메인.

## 실습 목표
- 툴 설명이 툴 선택을 좌우함을 체감 (2.1)
- 구조화된 에러(`isError`·`errorCategory`·`isRetryable`)로 재시도 판단 (2.2)
- `tool_choice`(auto/any/forced) 차이 (2.3)
- 진짜 MCP 서버 제작·연결 + `.mcp.json` 설정 (2.4)

## 시드

**Tier 1 — Messages API (`anthropic[bedrock]`)**
| 파일 | 다루는 것 |
|---|---|
| `tool_descriptions.py` | 나쁜 vs 좋은 툴 설명 → 툴 선택 신뢰도 (2.1) |
| `structured_tool_errors.py` | 구조화 에러 + 재시도 판단(transient만 재시도) (2.2) |
| `tool_choice_demo.py` | `auto`/`any`/`forced` 3가지 비교 (2.3) |

**Tier 2 — Claude Agent SDK (`claude-agent-sdk` + Claude Code CLI)**
| 파일 | 다루는 것 |
|---|---|
| `tool_descriptions_agentsdk.py` | 커스텀 `@tool` 설명이 선택을 좌우 (2.1) |
| `structured_tool_errors_agentsdk.py` | `@tool`이 `is_error`+구조화 메시지로 재시도 유도 (2.2) |
| `mcp_server_demo.py` | `@tool`+`create_sdk_mcp_server`로 **진짜 MCP 서버** (2.4) |

**참고 파일**
| 파일 | 다루는 것 |
|---|---|
| `.mcp.json.example` | 외부(stdio) MCP 서버 설정 + `${ENV}` 참조 (2.4) |

> `tool_choice`(2.3)는 Messages API 레벨 개념이라 Tier1 버전만 있음(Agent SDK는 툴 호출을 추상화). 같은 개념을 두 레벨로 보고 싶으면 Tier1 ↔ Tier2 짝(`_agentsdk`)을 비교하세요.

## 실행 예
```bash
source .venv/bin/activate
python d2-tools-mcp/tool_descriptions.py        # (Tier1)
python d2-tools-mcp/structured_tool_errors.py   # (Tier1, 모델 없이 결정론)
python d2-tools-mcp/tool_choice_demo.py         # (Tier1)
# (Tier2) python d2-tools-mcp/mcp_server_demo.py
```

## 핵심 정리
- 툴 선택 문제 → **먼저 툴 설명 개선**(few-shot·라우터보다 우선)
- "툴 많을수록 좋다" → ❌ (4~5개로 스코프, 선택 신뢰도 유지)
- 에러는 **구조화**(재시도 가능 여부를 알려줘야) — transient만 재시도
- MCP: `.mcp.json`(프로젝트=팀공유) vs `~/.claude.json`(개인), 비밀은 `${ENV}` 참조
- MCP 툴 네이밍: `mcp__<서버>__<툴>`
