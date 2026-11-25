#!/usr/bin/env bash
# One-time (idempotent) setup of the S3 static website that hosts frontend/.
# Usage: ./scripts/setup_frontend_infra.sh
# Override defaults with env vars: BUCKET, REGION.
set -euo pipefail

REGION="${REGION:-us-east-1}"
ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"
BUCKET="${BUCKET:-nexus-ui-draft-${ACCOUNT_ID}}"
INDEX_DOC="tedarik-zinciri.html"

echo ">>> Account: ${ACCOUNT_ID}  Region: ${REGION}  Bucket: ${BUCKET}"

if aws s3api head-bucket --bucket "${BUCKET}" 2>/dev/null; then
  echo ">>> Bucket already exists, skipping create"
else
  echo ">>> Creating bucket"
  aws s3api create-bucket --bucket "${BUCKET}" --region "${REGION}" >/dev/null
fi

aws s3api put-bucket-tagging --bucket "${BUCKET}" \
  --tagging 'TagSet=[{Key=project,Value=nexus}]'

echo ">>> Allowing public bucket policy (demo website)"
aws s3api put-public-access-block --bucket "${BUCKET}" \
  --public-access-block-configuration BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=false,RestrictPublicBuckets=false

echo ">>> Enabling static website hosting (index: ${INDEX_DOC})"
aws s3 website "s3://${BUCKET}/" --index-document "${INDEX_DOC}"

echo ">>> Applying public-read bucket policy"
POLICY=$(cat <<EOF
{
  "Version": "2012-10-17",
  "Statement": [{
    "Sid": "PublicReadGetObject",
    "Effect": "Allow",
    "Principal": "*",
    "Action": "s3:GetObject",
    "Resource": "arn:aws:s3:::${BUCKET}/*"
  }]
}
EOF
)
aws s3api put-bucket-policy --bucket "${BUCKET}" --policy "${POLICY}"

echo ""
echo "Website URL: http://${BUCKET}.s3-website-${REGION}.amazonaws.com"
