// api/ 하위 파일. 이 파일을 편집하면 .claude/rules/api.md 가 조건부로 로드된다(3.3).
// (src/math.ts 를 열 때는 로드되지 않음 — 경로 스코프 대비 관찰)
export function getOrder(id: string) {
  return { id, status: "shipped" };
}
