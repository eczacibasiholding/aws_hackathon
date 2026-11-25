#!/usr/bin/env bash
# Deploys frontend/ to the S3 bucket behind CloudFront (mirror: files removed locally are removed from S3).
# Usage: ./scripts/deploy_frontend.sh
# Override defaults with env vars: BUCKET, REGION, SITE_URL (public HTTPS URL checked after the sync).
set -euo pipefail

REGION="${REGION:-us-east-1}"
ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"
BUCKET="${BUCKET:-nexus-ui-draft-${ACCOUNT_ID}}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC="${ROOT_DIR}/frontend"

# Fail fast if the page would depend on an external CDN again (venue networks block unpkg.com).
if grep -nE '<script[^>]+src="https?://|<link[^>]+href="https?://' "${SRC}"/*.html; then
  echo "ERROR: frontend HTML loads scripts/styles from an external URL. Put them under frontend/vendor/." >&2
  exit 1
fi

echo ">>> Syncing ${SRC} -> s3://${BUCKET}/"
# no-cache: browsers revalidate (ETag) on every visit and CloudFront keeps objects only for
# its minimum TTL (1 s), so a new deploy shows up immediately without a cache invalidation.
aws s3 sync "${SRC}/" "s3://${BUCKET}/" --region "${REGION}" --delete --cache-control "no-cache"

SITE_URL="${SITE_URL:-https://dhqlkgzaubwcj.cloudfront.net}"
sleep 2
echo ">>> Checking ${SITE_URL}"
curl -fsS -o /dev/null -w "HTTP %{http_code}\n" "${SITE_URL}/"
echo "Deployed: ${SITE_URL}"
