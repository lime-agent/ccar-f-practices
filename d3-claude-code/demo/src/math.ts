// 일반 소스 파일. 이 파일을 편집해도 testing.md/api.md 규칙은 로드되지 않는다
// (경로/타입 글롭에 매칭되지 않음 → 조건부 로딩 대비 관찰용, Task 3.3).
export function add(a: number, b: number): number {
  return a + b;
}
