#!/usr/bin/env bash
# D3 실습 3.6 — Claude Code 를 CI/CD 파이프라인에서 헤드리스로 실행.
#
#   -p / --print        : 비대화형(headless). 대화형 입력 대기(hang) 방지 — CI 필수.
#   --output-format json: 기계 파싱 가능한 구조화 출력(→ 인라인 PR 코멘트 자동 게시).
#   --json-schema       : 출력 스키마 강제(findings 형태 고정).
#
# CLAUDE.md 역할: CI가 호출하는 Claude Code 에 리뷰 기준·fixture 규약·테스트 표준을
#                컨텍스트로 제공한다(저가치 출력 감소).
set -euo pipefail

claude -p "변경된 파일을 리뷰하고 지적사항을 findings 배열로 내라." \
  --output-format json \
  --json-schema ci/review-schema.json

# 팁(3.6 세션 격리):
#  - 코드를 '생성한' 바로 그 세션은 자기 변경 리뷰에 덜 효과적(자기 편향).
#    → 독립 리뷰 인스턴스가 더 낫다.
#  - 새 커밋 후 재리뷰 시, 이전 findings 를 컨텍스트에 넣어 '새/미해결'만 보고 → 중복 코멘트 방지.
