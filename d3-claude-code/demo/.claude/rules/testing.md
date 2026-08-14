---
paths: ["**/*.test.ts", "**/*.test.tsx"]
---

# 테스트 파일 규약 (glob 조건부 로딩)

이 규칙은 **테스트 파일을 편집할 때만** 로드된다 — 디렉토리 위치와 무관하게 **타입별**로 적용된다.
(코드베이스 전반에 흩어진 `*.test.*` 파일에는 서브디렉토리 `CLAUDE.md`보다 이 방식이 유리, Task 3.3)

- AAA 패턴(Arrange–Act–Assert)
- 테스트명은 **동작을 서술**("returns empty array when no match")
- 외부 의존은 목(mock)으로 격리
