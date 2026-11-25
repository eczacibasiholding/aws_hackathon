#!/usr/bin/env bash
# GitHub Actions → AWS bağlantısı (OIDC) için deploy rolünü kurar ya da günceller. Tekrar çalıştırılabilir.
# .github/workflows/deploy-frontend.yml bu rolü üstlenir; rol yalnızca REPO'nun BRANCH dalına güvenir
# ve yalnızca frontend bucket'ına yazabilir.
#
# Repo başka bir hesaba/organizasyona taşınınca (ör. eczacibasiholding/aws_hackathon) GitHub'ın
# gönderdiği kimlik ("sub") değişir ve deploy "Not authorized to perform sts:AssumeRoleWithWebIdentity"
# hatasıyla düşer. Bu betiği yeni repo adıyla tekrar çalıştırmak yeterli.
#
# Kullanım (AWS CloudShell ya da IAM yetkili herhangi bir kabuk):
#   ./scripts/setup_github_oidc_role.sh
# Varsayılanları env ile değiştir: REPO, BRANCH, ROLE, BUCKET.
set -euo pipefail

REPO="${REPO:-eczacibasiholding/aws_hackathon}"
BRANCH="${BRANCH:-main}"
ROLE="${ROLE:-nexus-github-frontend-deploy}"
ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"
BUCKET="${BUCKET:-nexus-ui-draft-${ACCOUNT_ID}}"
OIDC_HOST="token.actions.githubusercontent.com"
PROVIDER_ARN="arn:aws:iam::${ACCOUNT_ID}:oidc-provider/${OIDC_HOST}"

echo ">>> Hesap: ${ACCOUNT_ID}  Rol: ${ROLE}  Güvenilen: repo:${REPO}:ref:refs/heads/${BRANCH}  Bucket: ${BUCKET}"

if aws iam get-open-id-connect-provider --open-id-connect-provider-arn "${PROVIDER_ARN}" >/dev/null 2>&1; then
  echo ">>> GitHub OIDC sağlayıcısı zaten var"
else
  echo ">>> GitHub OIDC sağlayıcısı oluşturuluyor"
  aws iam create-open-id-connect-provider --url "https://${OIDC_HOST}" --client-id-list sts.amazonaws.com >/dev/null
fi

TRUST=$(cat <<EOF
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": { "Federated": "${PROVIDER_ARN}" },
    "Action": "sts:AssumeRoleWithWebIdentity",
    "Condition": {
      "StringEquals": {
        "${OIDC_HOST}:aud": "sts.amazonaws.com",
        "${OIDC_HOST}:sub": "repo:${REPO}:ref:refs/heads/${BRANCH}"
      }
    }
  }]
}
EOF
)

if aws iam get-role --role-name "${ROLE}" >/dev/null 2>&1; then
  echo ">>> Rol var. Eski güven politikası:"
  aws iam get-role --role-name "${ROLE}" --query 'Role.AssumeRolePolicyDocument' --output json
  echo ">>> Güven politikası güncelleniyor"
  aws iam update-assume-role-policy --role-name "${ROLE}" --policy-document "${TRUST}"
else
  echo ">>> Rol oluşturuluyor"
  aws iam create-role --role-name "${ROLE}" --assume-role-policy-document "${TRUST}" \
    --description "GitHub Actions: ${REPO} ${BRANCH} -> s3://${BUCKET}" \
    --tags Key=project,Value=nexus >/dev/null
fi

# aws s3 sync --delete için gereken en az yetki: listele, yaz, sil (yalnız bu bucket).
PERMS=$(cat <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    { "Effect": "Allow", "Action": "s3:ListBucket", "Resource": "arn:aws:s3:::${BUCKET}" },
    { "Effect": "Allow", "Action": ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"], "Resource": "arn:aws:s3:::${BUCKET}/*" }
  ]
}
EOF
)
echo ">>> Bucket yazma yetkisi (satır içi politika: deploy-frontend-bucket)"
aws iam put-role-policy --role-name "${ROLE}" --policy-name deploy-frontend-bucket --policy-document "${PERMS}"

echo ""
echo "Tamam. Workflow'daki rol: arn:aws:iam::${ACCOUNT_ID}:role/${ROLE}"
