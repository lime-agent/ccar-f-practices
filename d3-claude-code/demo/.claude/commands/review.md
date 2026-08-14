---
description: 변경 코드를 리뷰하고 우선순위별 지적사항을 낸다
argument-hint: "[파일 경로 또는 비움(=최근 변경)]"
allowed-tools: Read, Grep, Glob
---

당신은 시니어 코드 리뷰어다. `$ARGUMENTS` 로 지정된 코드(없으면 최근 변경분)를 리뷰하라.

- CRITICAL / HIGH / MEDIUM / LOW 로 분류
- 각 지적에 `파일:라인` + 구체적 수정 제안
- 읽기 전용: 파일을 **수정하지 말 것** (allowed-tools 에 Write 없음 → 파괴적 행동 차단, Task 3.2)

<!--
  이 파일 위치 = .claude/commands/  → project 스코프(버전관리로 팀 공유). (Task 3.2)
  대비: ~/.claude/commands/  → user 스코프(개인 전용, 공유 안 됨).
  실습 확인: Claude Code에서  /review  실행 → argument-hint 가 인자 안내로 뜨는지,
             allowed-tools 로 쓰기가 막혀 있는지 관찰.

  ※ allowed-tools·argument-hint 는 command·skill '공통' 옵션이다(교재 v0.1이 Skill 전용이라 한 건 오기).
    command vs skill 진짜 구분 = ① 구조(단일 .md vs 폴더) ② 호출(사용자 /name vs 모델 자동). skills/summarize/SKILL.md 참고.
-->
