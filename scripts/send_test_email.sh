#!/usr/bin/env bash
# Yedek tetik (SCOPE §4.4, D3): SG-2611-001 metnini e-posta olarak inbound-email/ önekine yükler.
# Kullanım: ./scripts/send_test_email.sh [SINYAL_NO]   (varsayılan SG-2611-001; metin girdi Excel'inden okunur)
set -euo pipefail
REGION="${AWS_REGION:-us-east-1}"
ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"
BUCKET="${NEXUS_BUCKET:-nexus-${ACCOUNT_ID}-${REGION}}"
SINYAL="${1:-SG-2611-001}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
python3 - "$ROOT_DIR/data/nexus_agent_input.xlsx" "$SINYAL" > "$TMP/mail.eml" <<'PY'
import sys, openpyxl
from email.message import EmailMessage
from email.utils import format_datetime
from datetime import datetime, timezone
ws = openpyxl.load_workbook(sys.argv[1], read_only=True)["Risk_Sinyalleri"]
rows = ws.iter_rows(values_only=True); h = list(next(rows))
r = next(r for r in rows if r[0] == sys.argv[2])
m = EmailMessage()
m["From"] = "Advisory Desk <advisory@akhfeeder.example.com>"
m["To"] = "signals@nexus.example.com"
m["Subject"] = "Customer advisory"
m["Date"] = format_datetime(datetime.now(timezone.utc))
m.set_content(str(r[h.index("Ham Metin (LLM Girdisi)")]) + "\n\nBest regards\nAdvisory Desk\n+90 212 555 00 00\n")
sys.stdout.write(m.as_string())
PY
KEY="inbound-email/test-$(date -u +%Y%m%dT%H%M%S)-${SINYAL}.eml"
aws s3 cp "$TMP/mail.eml" "s3://${BUCKET}/${KEY}" --region "$REGION" --content-type message/rfc822
echo "Yüklendi: s3://${BUCKET}/${KEY}"
echo "Log: aws logs tail /aws/lambda/nexus-email-trigger --follow --region ${REGION}"
