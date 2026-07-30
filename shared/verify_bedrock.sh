#!/usr/bin/env bash
# Bedrock API 키 검증 스크립트 (키는 파일에 저장하지 않고 실행 시 입력받음)

export AWS_REGION="${AWS_REGION:-ap-northeast-2}"
# 서울(APAC) 교차 리전 추론 프로파일 — 가장 저렴/빠른 검증용
MODEL_ID="${BEDROCK_MODEL_ID:-apac.anthropic.claude-3-haiku-20240307-v1:0}"

# 이미 export 된 키가 있으면 그대로 사용, 없으면 입력받음
AWS_BEARER_TOKEN_BEDROCK="${AWS_BEARER_TOKEN_BEDROCK:-}"
if [ -z "${AWS_BEARER_TOKEN_BEDROCK}" ]; then
  read -rsp "Bedrock API 키 붙여넣기(화면에 안 보임): " AWS_BEARER_TOKEN_BEDROCK
  echo
fi
export AWS_BEARER_TOKEN_BEDROCK
echo "→ region=${AWS_REGION}, model=${MODEL_ID} 로 호출합니다..."
echo

curl -sS -X POST \
  "https://bedrock-runtime.${AWS_REGION}.amazonaws.com/model/${MODEL_ID}/converse" \
  -H "Authorization: Bearer ${AWS_BEARER_TOKEN_BEDROCK}" \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":[{"text":"CCA-F 스터디 실습 환경 검증. 한 문장으로 인사해줘."}]}],"inferenceConfig":{"maxTokens":80}}'
echo
