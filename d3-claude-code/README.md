# D3 — Claude Code Configuration & Workflows (20%)

> 이 도메인은 **Claude Code CLI**가 실습 대상 그 자체입니다(Tier1 API 경로 없음).
> 지금 쓰는 Claude Code(on Bedrock)가 곧 실습 환경 — **전원 설치 전제**, 미설치자는 데모/캡쳐로 따라옵니다.

## 실습 방식 — 데모 repo 클론
완비된 `.claude/` 구조가 담긴 **`demo/`** 폴더를 열어 관찰·수정합니다. 순서·확인 포인트는 [`demo/README.md`](./demo/README.md).

```bash
npm i -g @anthropic-ai/claude-code
export CLAUDE_CODE_USE_BEDROCK=1 AWS_REGION=ap-northeast-2 AWS_BEARER_TOKEN_BEDROCK=<지급 키>
cd practices/d3-claude-code/demo && claude
```

## 태스크 → 데모 매핑
| Task | 주제 | 데모 위치 |
|---|---|---|
| 3.1 | CLAUDE.md 계층 · `@import` | `CLAUDE.md`, `docs/style.md`, `backend/CLAUDE.md` |
| 3.2 | slash command · skill(`context: fork`) | `.claude/commands/review.md`, `.claude/skills/summarize/SKILL.md` |
| 3.3 | path-specific rules(글롭 조건부) | `.claude/rules/{testing,api}.md` + `src/`·`api/` |
| 3.4 | Plan mode vs Direct(판단) | `scenarios/plan-mode.md` |
| 3.5 | 반복 정제(예시·TDD·interview) | `scenarios/iterative-refinement.md` |
| 3.6 | CI/CD 헤드리스 | `ci/review.sh`, `ci/review-schema.json` |

## 핵심 정리
- CLAUDE.md 우선순위: **서브디렉토리 > 프로젝트 > 사용자**. `~/.claude/CLAUDE.md`는 개인 전용(팀 공유 ❌).
- 팀 공유 커맨드 = `.claude/commands/` · 개인 = `~/.claude/commands/`.
- `.claude/rules/` `paths:` 글롭 = **매칭 파일 편집 시에만** 로드(토큰 절약).
- Plan Mode = 대규모·다중파일·아키텍처 결정 ("항상/절대"는 오답). 장황한 탐색은 **Explore 서브에이전트**로 격리.
- CI: `-p`(비대화형) + `--output-format json` + `--json-schema`. 코드 생성 세션보다 **독립 세션** 리뷰가 효과적.
