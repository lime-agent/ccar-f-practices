import { describe, it, expect } from "vitest";
import { add } from "./math";

// ⓘ 실습 확인(3.3): 이 *.test.ts 파일을 Claude Code로 열어 편집하면
//   .claude/rules/testing.md 가 조건부로 로드된다. src/math.ts 를 열 때와 비교해볼 것.
describe("add", () => {
  it("두 수를 더한다", () => {
    // Arrange–Act–Assert
    expect(add(1, 2)).toBe(3);
  });
});
