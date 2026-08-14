---
name: summarize
description: 긴 산출물(코드베이스 분석 등)을 요약한다. 조사·요약이 필요한 맥락에서 모델이 자동 호출
argument-hint: "[요약할 대상 경로]"
allowed-tools: Read, Grep, Glob
---

`$ARGUMENTS` 대상을 조사해 **핵심만 5줄 이내**로 요약하라.

## Command vs Skill — 진짜 구분 2가지 (Task 3.2)
1. **구조**: command = 단일 `.md`(`.claude/commands/review.md`) / skill = **폴더**(`.claude/skills/summarize/SKILL.md` + 부가 리소스·`scripts/`, 필요할 때 점진 로딩).
2. **호출**: command = 사용자가 `/name` 명시 / skill = **모델이 자동 호출**(이 `description`을 보고 task 맥락에서 트리거. `disable-model-invocation: true`로 끄기).

- `allowed-tools`(툴 제한)·`argument-hint`(인자 안내)·`model`/`effort`는 **command·skill 공통 옵션**.
- **skill**(on-demand 워크플로우) vs **CLAUDE.md**(항상 로드 표준) 중 선택하는 것도 3.2 포인트.
- 개인 변형은 다른 이름으로 `~/.claude/skills/`에(팀원 영향 회피).

<!--
  ⚠️ 교재(v0.1) 표 정정: 교재는 allowed-tools·argument-hint·context:fork 를 'Skill 전용 구분 기준'이라 하나,
     - allowed-tools·argument-hint → command·skill 공통 (아래 commands/review.md 에도 실제로 있음)
     - context: fork → 현행 Claude Code 네이티브 프론트매터 아님(공식 docs에 없음). 격리 실행은 subagent/Task.
       그래서 이 파일에선 context: fork 를 프론트매터에 넣지 않았다(넣어도 무시됨).
  시험 대비: 개념·범위(팀/개인, 용도)는 교재대로 OK / "옵션이 어느 쪽 전용"류는 맹신 금지 → 판단축 = 구조+호출.
  근거: code.claude.com/docs (skills · slash-commands · claude-directory).
-->
