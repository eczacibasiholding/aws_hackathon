#!/usr/bin/env bash
# Lets GitHub Actions in the given repo(s) deploy the frontend, by rewriting the trust policy of the
# AWS role used by .github/workflows/deploy-frontend.yml. The list REPLACES the current one:
# pass every repo that should keep deploying.
#
# Usage:  ./scripts/connect_github_repo.sh owner/repo [owner2/repo2 ...]
# Env:    BRANCH (default main), ROLE_NAME (default nexus-github-frontend-deploy),
#         GH_TOKEN (only needed to look up IDs of private repos)
#
# GitHub may put either "repo:owner/repo:..." or the ID form "repo:owner@<id>/repo@<id>:..." in the
# token's "sub" claim, so both forms are allowed for each repo.
set -euo pipefail

[ $# -ge 1 ] || { echo "Usage: $0 owner/repo [owner2/repo2 ...]" >&2; exit 1; }

BRANCH="${BRANCH:-main}"
ROLE_NAME="${ROLE_NAME:-nexus-github-frontend-deploy}"
ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"
AUTH=()
[ -n "${GH_TOKEN:-}" ] && AUTH=(-H "Authorization: Bearer ${GH_TOKEN}")

SUBS=()
for FULL in "$@"; do
  INFO="$(curl -fsS "${AUTH[@]}" "https://api.github.com/repos/${FULL}")" || {
    echo "ERROR: cannot read https://api.github.com/repos/${FULL} (private repo? set GH_TOKEN)" >&2; exit 1; }
  read -r OWNER OWNER_ID NAME REPO_ID < <(python3 -c '
import json, sys
d = json.load(sys.stdin)
print(d["owner"]["login"], d["owner"]["id"], d["name"], d["id"])' <<<"${INFO}")
  SUBS+=("repo:${OWNER}/${NAME}:ref:refs/heads/${BRANCH}")
  SUBS+=("repo:${OWNER}@${OWNER_ID}/${NAME}@${REPO_ID}:ref:refs/heads/${BRANCH}")
done

POLICY="$(python3 - "${ACCOUNT_ID}" "${SUBS[@]}" <<'EOF'
import json, sys
account, subs = sys.argv[1], sys.argv[2:]
print(json.dumps({
    "Version": "2012-10-17",
    "Statement": [{
        "Effect": "Allow",
        "Principal": {"Federated": f"arn:aws:iam::{account}:oidc-provider/token.actions.githubusercontent.com"},
        "Action": "sts:AssumeRoleWithWebIdentity",
        "Condition": {"StringEquals": {
            "token.actions.githubusercontent.com:aud": "sts.amazonaws.com",
            "token.actions.githubusercontent.com:sub": subs,
        }},
    }],
}))
EOF
)"

aws iam update-assume-role-policy --role-name "${ROLE_NAME}" --policy-document "${POLICY}"
echo ">>> ${ROLE_NAME} now trusts branch '${BRANCH}' of: $*"
aws iam get-role --role-name "${ROLE_NAME}" \
  --query 'Role.AssumeRolePolicyDocument.Statement[0].Condition.StringEquals."token.actions.githubusercontent.com:sub"' --output text | tr '\t' '\n'
