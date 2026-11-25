#!/usr/bin/env bash
# One-time (idempotent) setup of the frontend hosting:
#   private S3 bucket  <-- Origin Access Control --  CloudFront (HTTPS, *.cloudfront.net)
# The bucket is not public; only this CloudFront distribution can read it.
# The old S3 website endpoint (http) is kept only as a redirect to the HTTPS URL.
#
# Usage: ./scripts/setup_frontend_infra.sh
# Override defaults with env vars: BUCKET, REGION.
set -euo pipefail

REGION="${REGION:-us-east-1}"
ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"
BUCKET="${BUCKET:-nexus-ui-draft-${ACCOUNT_ID}}"
INDEX_DOC="tedarik-zinciri.html"
OAC_NAME="nexus-frontend-oac"
DIST_COMMENT="nexus-frontend ${BUCKET}"
CACHE_POLICY_ID="658327ea-f89d-4fab-a63d-7e88639e58f6"     # AWS managed: CachingOptimized
HEADERS_POLICY_ID="67f7725c-6f97-4210-82d7-5512b31e9d03"   # AWS managed: SecurityHeadersPolicy (HSTS, nosniff, ...)
TMP="$(mktemp -d)"
trap 'rm -rf "${TMP}"' EXIT

echo ">>> Account: ${ACCOUNT_ID}  Region: ${REGION}  Bucket: ${BUCKET}"

# 1. Bucket
if aws s3api head-bucket --bucket "${BUCKET}" >/dev/null 2>&1; then
  echo ">>> Bucket exists"
else
  echo ">>> Creating bucket"
  aws s3api create-bucket --bucket "${BUCKET}" --region "${REGION}" >/dev/null
fi
aws s3api put-bucket-tagging --bucket "${BUCKET}" --tagging 'TagSet=[{Key=project,Value=nexus}]'

# 2. Origin Access Control
OAC_ID="$(aws cloudfront list-origin-access-controls \
  --query "OriginAccessControlList.Items[?Name=='${OAC_NAME}'].Id | [0]" --output text)"
if [ "${OAC_ID}" = "None" ] || [ -z "${OAC_ID}" ]; then
  echo ">>> Creating Origin Access Control"
  OAC_ID="$(aws cloudfront create-origin-access-control --origin-access-control-config \
    "Name=${OAC_NAME},Description=NEXUS frontend S3 access,SigningProtocol=sigv4,SigningBehavior=always,OriginAccessControlOriginType=s3" \
    --query OriginAccessControl.Id --output text)"
fi
echo ">>> OAC: ${OAC_ID}"

# 3. CloudFront distribution (found again by its Comment on re-runs)
DIST_ID="$(aws cloudfront list-distributions \
  --query "DistributionList.Items[?Comment=='${DIST_COMMENT}'].Id | [0]" --output text)"
if [ "${DIST_ID}" = "None" ] || [ -z "${DIST_ID}" ]; then
  echo ">>> Creating CloudFront distribution"
  cat > "${TMP}/dist.json" <<EOF
{
  "DistributionConfig": {
    "CallerReference": "nexus-frontend-$(date +%s)",
    "Comment": "${DIST_COMMENT}",
    "Enabled": true,
    "DefaultRootObject": "${INDEX_DOC}",
    "HttpVersion": "http2and3",
    "IsIPV6Enabled": true,
    "PriceClass": "PriceClass_All",
    "Origins": {
      "Quantity": 1,
      "Items": [{
        "Id": "s3-frontend",
        "DomainName": "${BUCKET}.s3.${REGION}.amazonaws.com",
        "OriginAccessControlId": "${OAC_ID}",
        "S3OriginConfig": { "OriginAccessIdentity": "" }
      }]
    },
    "DefaultCacheBehavior": {
      "TargetOriginId": "s3-frontend",
      "ViewerProtocolPolicy": "redirect-to-https",
      "CachePolicyId": "${CACHE_POLICY_ID}",
      "ResponseHeadersPolicyId": "${HEADERS_POLICY_ID}",
      "Compress": true,
      "AllowedMethods": {
        "Quantity": 2, "Items": ["GET", "HEAD"],
        "CachedMethods": { "Quantity": 2, "Items": ["GET", "HEAD"] }
      }
    }
  },
  "Tags": { "Items": [{ "Key": "project", "Value": "nexus" }] }
}
EOF
  DIST_ID="$(aws cloudfront create-distribution-with-tags \
    --distribution-config-with-tags "file://${TMP}/dist.json" --query Distribution.Id --output text)"
fi
DIST_DOMAIN="$(aws cloudfront get-distribution --id "${DIST_ID}" --query Distribution.DomainName --output text)"
DIST_ARN="arn:aws:cloudfront::${ACCOUNT_ID}:distribution/${DIST_ID}"
echo ">>> Distribution: ${DIST_ID} (${DIST_DOMAIN})"

# 4. Bucket policy: only this distribution may read objects (replaces any older public policy)
cat > "${TMP}/policy.json" <<EOF
{
  "Version": "2012-10-17",
  "Statement": [{
    "Sid": "AllowCloudFrontRead",
    "Effect": "Allow",
    "Principal": { "Service": "cloudfront.amazonaws.com" },
    "Action": "s3:GetObject",
    "Resource": "arn:aws:s3:::${BUCKET}/*",
    "Condition": { "StringEquals": { "AWS:SourceArn": "${DIST_ARN}" } }
  }]
}
EOF
aws s3api put-bucket-policy --bucket "${BUCKET}" --policy "file://${TMP}/policy.json"

# 5. Block all public access
aws s3api put-public-access-block --bucket "${BUCKET}" \
  --public-access-block-configuration BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true

# 6. Old http S3 website endpoint -> redirect to HTTPS (keeps previously shared links working)
aws s3api put-bucket-website --bucket "${BUCKET}" --website-configuration \
  "{\"RedirectAllRequestsTo\":{\"HostName\":\"${DIST_DOMAIN}\",\"Protocol\":\"https\"}}"

echo ">>> Waiting for CloudFront to finish deploying (can take several minutes)..."
aws cloudfront wait distribution-deployed --id "${DIST_ID}"

echo ""
echo "Website URL: https://${DIST_DOMAIN}"
