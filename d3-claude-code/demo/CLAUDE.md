# Demo 프로젝트 표준 (프로젝트 계층 — 팀 공유)

이 파일은 프로젝트 루트의 `CLAUDE.md`다. 저장소에 커밋되어 **팀 전체에 공유**된다(버전관리).
대비: `~/.claude/CLAUDE.md`(user-level)는 **개인 전용** — 그 지시는 팀과 공유되지 않는다. (Task 3.1)

## 공통 코딩 표준
- 커밋 메시지: Conventional Commits (`feat:`, `fix:` …)
- 모든 함수 시그니처에 타입 명시
- 에러는 경계에서 명시적으로 처리

## 모듈화 — @import
아래 한 줄은 외부 파일을 이 CLAUDE.md 안으로 임포트한다(모놀리식 CLAUDE.md 방지, Task 3.1):

@docs/style.md

> **실습 확인(3.1)**: Claude Code에서 `/memory` 를 실행하면 로드된 메모리 파일이 보인다.
> - 루트에서 열면: 이 `CLAUDE.md` + 임포트된 `docs/style.md`
> - `backend/` 에서 작업하면: 위에 더해 `backend/CLAUDE.md` (더 가까운 파일이 우선)
