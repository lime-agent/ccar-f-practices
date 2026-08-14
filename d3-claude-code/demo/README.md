# D3 데모 repo — Claude Code Configuration & Workflows (관찰 가이드)

이 폴더는 **완비된 `.claude/` 구조**를 담은 실습용 샘플이다. Claude Code로 열어 아래 순서로 **관찰·수정**한다.
(실행형은 3.1·3.2·3.3·3.6, 판단·기법형은 3.4·3.5 — `scenarios/` 참고)

## 준비
```bash
# Claude Code CLI (전원 필요) + Bedrock 라우팅
npm i -g @anthropic-ai/claude-code
export CLAUDE_CODE_USE_BEDROCK=1
export AWS_REGION=ap-northeast-2
export AWS_BEARER_TOKEN_BEDROCK=<지급 키>
# (선택) export ANTHROPIC_MODEL=<APAC 프로파일 ID>

cd practices/d3-claude-code/demo   # ← 반드시 이 폴더에서 claude 실행(계층 관찰의 기준점)
claude
```
> 설치 못 한 멤버는 스터디 시간의 **데모/캡쳐**로 따라온다(개념·문항은 동일하게 학습).

> ⚠️ **③④는 자연어 대신 슬래시 커맨드로 관찰할 것.** "코드 리뷰해줘" 같은 자연어는 개인 계정에 등록된 다른 스킬을 먼저 트리거해 이 데모의 rules/skill 관찰을 가릴 수 있다(개인 설정마다 결과 다름). `/review <file>` 처럼 명시적으로 부를 것.

## 관찰 순서
| 순서 | 태스크 | 무엇을 한다 | 확인할 내용 |
|---|---|---|---|
| ① | 3.1 계층 | `/memory` 실행 | 루트 `CLAUDE.md` + `@docs/style.md` 로드 확인. `backend/` 에서 열면 `backend/CLAUDE.md` 추가·우선 |
| ② | 3.2 command | `/review` 실행 | `argument-hint` 안내, `allowed-tools`로 쓰기 차단. 위치 `.claude/commands/`=팀 공유 |
| ③ | 3.2 skill | `summarize` skill(폴더+`SKILL.md`) 호출 | command vs skill 진짜 차이 = **구조**(파일 vs 폴더) + **호출**(사용자 `/name` vs 모델 자동). 옵션은 공통 |
| ④ | 3.3 rules | `src/math.test.ts` vs `src/math.ts` vs `api/orders.ts` 편집 | `*.test.ts`→`testing.md`, `api/**`→`api.md` 만 조건부 로드(글롭) |
| ⑤ | 3.4 plan | `scenarios/plan-mode.md` 풀기 | Plan vs Direct vs Explore 판단("항상/절대"는 오답) |
| ⑥ | 3.5 refine | `scenarios/iterative-refinement.md` 미니 실습 | 예시·TDD·interview가 산문보다 엣지케이스를 잘 잡음 |
| ⑦ | 3.6 CI/CD | `bash ci/review.sh` | `-p`(비대화형)+`--output-format json`+`--json-schema` 구조화 출력. 세션 격리 리뷰 |

## 구조
```
demo/
├── CLAUDE.md            루트(프로젝트, 팀 공유) + @import           [3.1]
├── docs/style.md        @import 되는 모듈 파일                      [3.1]
├── backend/CLAUDE.md    디렉토리 계층(우선순위 ↑)                    [3.1]
├── .claude/
│   ├── commands/review.md          팀 공유 slash command            [3.2]
│   ├── skills/summarize/SKILL.md   폴더형 skill(모델 자동 호출)        [3.2]
│   └── rules/{testing,api}.md      paths 글롭 조건부 규칙            [3.3]
├── src/{math.ts, math.test.ts}     rules 글롭 매칭 대비 관찰용
├── api/orders.ts                   api/** 글롭 매칭 관찰용
├── ci/{review.sh, review-schema.json}  헤드리스 CI 리뷰             [3.6]
└── scenarios/{plan-mode,iterative-refinement}.md   판단·기법 워크북 [3.4·3.5]
```

> ⚠️ **교재 표 정정(현행 Claude Code 기준)**: 교재 v0.1은 `allowed-tools`·`argument-hint`·`context: fork`를 'Skill 전용'이라 하나 —
> 앞 둘은 **command·skill 공통**, `context: fork`는 **네이티브 아님**(격리는 subagent/Task). command vs skill 진짜 구분 = **구조 + 호출**.
> `.claude/rules/` `paths:` 표기도 CLI 버전차 있을 수 있으니 **'시험에 나오는 개념'** 으로 학습할 것.
