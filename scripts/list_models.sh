#!/usr/bin/env bash
# F0: hesapta erişilebilen Bedrock modelleri ve inference profile'lar (SCOPE §4.3).
set -euo pipefail
REGION="${AWS_REGION:-us-east-1}"
echo "== Foundation models (reasoning adayları: anthropic / amazon nova / meta / deepseek) [$REGION]"
aws bedrock list-foundation-models --region "$REGION" \
  --query 'modelSummaries[?contains(inferenceTypesSupported, `INFERENCE_PROFILE`) || contains(inferenceTypesSupported, `ON_DEMAND`)].[modelId,providerName,join(`,`,inferenceTypesSupported)]' \
  --output table
echo "== Inference profiles"
aws bedrock list-inference-profiles --region "$REGION" \
  --query 'inferenceProfileSummaries[].[inferenceProfileId,status]' --output table
if [[ -n "${BEDROCK_MODEL_ID:-}" ]]; then
  echo "== Deneme çağrısı: $BEDROCK_MODEL_ID"
  aws bedrock-runtime converse --region "$REGION" --model-id "$BEDROCK_MODEL_ID" \
    --messages '[{"role":"user","content":[{"text":"Sadece OK yaz."}]}]' \
    --query 'output.message.content[0].text' --output text
fi
