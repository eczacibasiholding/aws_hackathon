#!/usr/bin/env bash
# NEXUS uçtan uca deploy (idempotent). Kiro terminalinde (AWS SSO oturumu açıkken) çalıştırılır.
#   BEDROCK_MODEL_ID=<model> ./scripts/deploy_all.sh            # hepsi
#   STEPS="lambdas ui" ./scripts/deploy_all.sh                    # yalnızca seçili adımlar
# Adımlar: bucket runtime lambdas ui   (varsayılan: hepsi)
# Gerekli: aws cli v2, python3.12+, pip, zip; agentcore CLI (pip install -r requirements-dev.txt)
set -euo pipefail

REGION="${AWS_REGION:-us-east-1}"; export AWS_REGION="$REGION" AWS_DEFAULT_REGION="$REGION"
ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"
BUCKET="${NEXUS_BUCKET:-nexus-${ACCOUNT_ID}-${REGION}}"
UI_BUCKET="${UI_BUCKET:-nexus-ui-${ACCOUNT_ID}-${REGION}}"
INPUT_URI="s3://${BUCKET}/input/nexus_agent_input.xlsx"
AGENT_NAME="${AGENT_NAME:-nexus_runtime}"
MODEL_ID="${BEDROCK_MODEL_ID:?BEDROCK_MODEL_ID gerekli (scripts/list_models.sh ile seçin)}"
STEPS="${STEPS:-bucket runtime lambdas ui}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"; cd "$ROOT"
BUILD="$ROOT/.build"; mkdir -p "$BUILD"
STATE="$ROOT/.build/deploy_state.env"; touch "$STATE"; source "$STATE"
API_KEY="${API_KEY:-$(python3 -c 'import secrets;print(secrets.token_urlsafe(24))')}"
has() { [[ " $STEPS " == *" $1 "* ]]; }
say() { echo -e "\n>>> $*"; }
save() { grep -v "^$1=" "$STATE" > "$STATE.tmp" || true; echo "$1='$2'" >> "$STATE.tmp"; mv "$STATE.tmp" "$STATE"; }
policy() { sed -e "s#__BUCKET__#${BUCKET}#g" -e "s#__RUNTIME_ARN__#${AGENT_RUNTIME_ARN:-arn:aws:bedrock-agentcore:${REGION}:${ACCOUNT_ID}:runtime/none}#g" "$1"; }
save API_KEY "$API_KEY"
echo "Hesap ${ACCOUNT_ID} · Bölge ${REGION} · Kova ${BUCKET} · Model ${MODEL_ID}"

# ---------------------------------------------------------------- 1. S3
if has bucket; then
  say "S3 kovası: ${BUCKET}"
  if ! aws s3api head-bucket --bucket "$BUCKET" 2>/dev/null; then
    if [[ "$REGION" == "us-east-1" ]]; then aws s3api create-bucket --bucket "$BUCKET" >/dev/null
    else aws s3api create-bucket --bucket "$BUCKET" --create-bucket-configuration LocationConstraint="$REGION" >/dev/null; fi
  fi
  aws s3api put-public-access-block --bucket "$BUCKET" --public-access-block-configuration \
    BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
  aws s3api put-bucket-encryption --bucket "$BUCKET" --server-side-encryption-configuration \
    '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}'
  aws s3api put-bucket-lifecycle-configuration --bucket "$BUCKET" --lifecycle-configuration \
    '{"Rules":[{"ID":"inbound-email-1gun","Status":"Enabled","Filter":{"Prefix":"inbound-email/"},"Expiration":{"Days":1}}]}'
  aws s3 cp data/nexus_agent_input.xlsx "s3://${BUCKET}/input/nexus_agent_input.xlsx"   # cevap anahtarı YÜKLENMEZ (KÇ6)
fi

# ---------------------------------------------------------------- 2. AgentCore Runtime
if has runtime; then
  say "AgentCore Runtime: configure + launch (${AGENT_NAME})"
  command -v agentcore >/dev/null || pip install -q -r requirements-dev.txt
  agentcore configure --entrypoint src/app.py --name "$AGENT_NAME" --region "$REGION" \
    --requirements-file requirements.txt --non-interactive
  agentcore launch --auto-update-on-conflict \
    --env BEDROCK_MODEL_ID="$MODEL_ID" --env NEXUS_BUCKET="$BUCKET" \
    --env NEXUS_INPUT_URI="$INPUT_URI" --env AWS_REGION="$REGION" \
    --env DEMO_CANLI_SINYALLER="${DEMO_CANLI_SINYALLER:-SG-2611-001,SG-2611-002}"
  read -r AGENT_RUNTIME_ARN EXEC_ROLE < <(python3 - "$AGENT_NAME" <<'PY'
import sys, yaml
c = yaml.safe_load(open(".bedrock_agentcore.yaml"))
a = c["agents"][sys.argv[1]]
print(a["bedrock_agentcore"]["agent_arn"], a["aws"]["execution_role"])
PY
)
  save AGENT_RUNTIME_ARN "$AGENT_RUNTIME_ARN"
  say "Runtime rolüne S3 + Bedrock izni: ${EXEC_ROLE##*/}"
  aws iam put-role-policy --role-name "${EXEC_ROLE##*/}" --policy-name nexus-s3-bedrock \
    --policy-document "$(policy infra/runtime_s3_policy.json)"
  echo "AGENT_RUNTIME_ARN=${AGENT_RUNTIME_ARN}  (Observability: CloudWatch > GenAI Observability)"
fi
: "${AGENT_RUNTIME_ARN:?AGENT_RUNTIME_ARN yok; önce STEPS=runtime çalıştırın}"

# ---------------------------------------------------------------- 3. Lambda'lar
ensure_role() {  # $1=rol adı $2=policy dosyası
  if ! aws iam get-role --role-name "$1" >/dev/null 2>&1; then
    aws iam create-role --role-name "$1" --assume-role-policy-document file://infra/lambda_trust.json >/dev/null
    sleep 10   # IAM yayılımı
  fi
  aws iam put-role-policy --role-name "$1" --policy-name "$1-inline" --policy-document "$(policy "$2")"
  aws iam get-role --role-name "$1" --query Role.Arn --output text
}
deploy_fn() {  # $1=ad $2=zip $3=rol arn $4=handler $5=env json $6=timeout
  if aws lambda get-function --function-name "$1" >/dev/null 2>&1; then
    aws lambda update-function-code --function-name "$1" --zip-file "fileb://$2" >/dev/null
    aws lambda wait function-updated --function-name "$1"
    aws lambda update-function-configuration --function-name "$1" --role "$3" --handler "$4" \
      --timeout "$6" --memory-size 512 --environment "$5" >/dev/null
  else
    for i in 1 2 3 4 5; do
      aws lambda create-function --function-name "$1" --runtime python3.12 --architectures arm64 \
        --role "$3" --handler "$4" --zip-file "fileb://$2" --timeout "$6" --memory-size 512 \
        --environment "$5" >/dev/null && break || { echo "rol yayılımı bekleniyor…"; sleep 8; }
    done
  fi
  aws lambda wait function-updated --function-name "$1"
}
if has lambdas; then
  say "email_trigger paketi (openpyxl dahil, pandas yok)"
  rm -rf "$BUILD/et" && mkdir -p "$BUILD/et"
  pip install -q --target "$BUILD/et" openpyxl==3.1.5
  cp src/triggers/email_trigger/handler.py "$BUILD/et/handler.py"
  cp config/email_kaynaklari.yaml "$BUILD/et/email_kaynaklari.yaml"
  (cd "$BUILD/et" && rm -f ../et.zip && zip -qr ../et.zip .)
  ROLE_ET="$(ensure_role nexus-email-trigger-role infra/email_trigger_policy.json)"
  ENV_ET="{\"Variables\":{\"NEXUS_BUCKET\":\"$BUCKET\",\"AGENT_RUNTIME_ARN\":\"$AGENT_RUNTIME_ARN\"}}"
  deploy_fn nexus-email-trigger "$BUILD/et.zip" "$ROLE_ET" handler.lambda_handler "$ENV_ET" 300
  ET_ARN="$(aws lambda get-function --function-name nexus-email-trigger --query Configuration.FunctionArn --output text)"
  aws lambda add-permission --function-name nexus-email-trigger --statement-id s3-invoke \
    --action lambda:InvokeFunction --principal s3.amazonaws.com --source-arn "arn:aws:s3:::${BUCKET}" \
    --source-account "$ACCOUNT_ID" >/dev/null 2>&1 || true
  say "S3 bildirimi: inbound-email/ → nexus-email-trigger"
  aws s3api put-bucket-notification-configuration --bucket "$BUCKET" --notification-configuration \
    "{\"LambdaFunctionConfigurations\":[{\"Id\":\"nexus-inbound-email\",\"LambdaFunctionArn\":\"$ET_ARN\",\"Events\":[\"s3:ObjectCreated:*\"],\"Filter\":{\"Key\":{\"FilterRules\":[{\"Name\":\"prefix\",\"Value\":\"inbound-email/\"}]}}}]}"

  say "api paketi"
  rm -rf "$BUILD/api" && mkdir -p "$BUILD/api" && cp src/api/handler.py "$BUILD/api/handler.py"
  (cd "$BUILD/api" && rm -f ../api.zip && zip -qr ../api.zip .)
  ROLE_API="$(ensure_role nexus-api-role infra/api_policy.json)"
  ENV_API="{\"Variables\":{\"NEXUS_BUCKET\":\"$BUCKET\",\"AGENT_RUNTIME_ARN\":\"$AGENT_RUNTIME_ARN\",\"API_KEY\":\"$API_KEY\"}}"
  deploy_fn nexus-api "$BUILD/api.zip" "$ROLE_API" handler.lambda_handler "$ENV_API" 900
  if ! aws lambda get-function-url-config --function-name nexus-api >/dev/null 2>&1; then
    aws lambda create-function-url-config --function-name nexus-api --auth-type NONE >/dev/null   # CORS Lambda içinde
    aws lambda add-permission --function-name nexus-api --statement-id fnurl-public \
      --action lambda:InvokeFunctionUrl --principal "*" --function-url-auth-type NONE >/dev/null
    # 2025 sonrası herkese açık Function URL ayrıca lambda:InvokeFunction ister; yoksa 403
    aws lambda add-permission --function-name nexus-api --statement-id fnurl-public-invoke \
      --action lambda:InvokeFunction --principal "*" --invoked-via-function-url >/dev/null 2>&1 || true
  fi
  API_URL="$(aws lambda get-function-url-config --function-name nexus-api --query FunctionUrl --output text)"
  save API_URL "$API_URL"
  echo "API_URL=${API_URL}"
fi

# ---------------------------------------------------------------- 4. UI (S3 statik web)
if has ui; then
  : "${API_URL:?API_URL yok; önce STEPS=lambdas}"
  say "UI kovası: ${UI_BUCKET}"
  if ! aws s3api head-bucket --bucket "$UI_BUCKET" 2>/dev/null; then
    if [[ "$REGION" == "us-east-1" ]]; then aws s3api create-bucket --bucket "$UI_BUCKET" >/dev/null
    else aws s3api create-bucket --bucket "$UI_BUCKET" --create-bucket-configuration LocationConstraint="$REGION" >/dev/null; fi
  fi
  aws s3api put-public-access-block --bucket "$UI_BUCKET" --public-access-block-configuration \
    BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=false,RestrictPublicBuckets=false
  aws s3 website "s3://${UI_BUCKET}/" --index-document index.html
  aws s3api put-bucket-policy --bucket "$UI_BUCKET" --policy \
    "{\"Version\":\"2012-10-17\",\"Statement\":[{\"Effect\":\"Allow\",\"Principal\":\"*\",\"Action\":\"s3:GetObject\",\"Resource\":\"arn:aws:s3:::${UI_BUCKET}/*\"}]}"
  rm -rf "$BUILD/ui" && cp -r ui "$BUILD/ui"
  cat > "$BUILD/ui/config.js" <<JS
window.NEXUS_CONFIG = { API_URL: "${API_URL%/}", API_KEY: "${API_KEY}", MAP_URL: "https://dhqlkgzaubwcj.cloudfront.net", REFRESH_MS: 10000 };
JS
  aws s3 sync "$BUILD/ui/" "s3://${UI_BUCKET}/" --delete --cache-control no-cache
  echo "UI: http://${UI_BUCKET}.s3-website-${REGION}.amazonaws.com"
fi

say "Bitti. Durum dosyası: .build/deploy_state.env (API_KEY burada; repoya eklemeyin)"
cat "$STATE" | sed 's/^API_KEY=.*/API_KEY=<gizli>/'
