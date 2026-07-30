# D3 — Claude Code Configuration & Workflows (20%)

> 이 도메인은 **Tier 2**(Claude Code CLI 설치)가 필요합니다. 지금 쓰는 Claude Code(on Bedrock)가 곧 실습 환경.

## 실습 목표
- CLAUDE.md 계층·`.claude/rules/` 조건부 규칙을 실제 프로젝트에 적용한다.
- 커스텀 슬래시 커맨드 / hook / Skill 을 만든다.
- CI/CD 비대화형 실행: `claude -p ... --output-format json`.

## 시드 (세션에서 함께 추가)
- `.claude/commands/` 예제 커맨드
- `ci-review.sh` — `-p` + JSON 출력 파이프라인

## 핵심 정리
- CLAUDE.md 우선순위: 서브디렉토리 > 프로젝트 > 사용자
- 팀 공유 커맨드 = `.claude/commands/` · 개인 = `~/.claude/commands/`
- Plan Mode = 대규모·다중파일·아키텍처 변경 (단일 파일 수정엔 불필요)
