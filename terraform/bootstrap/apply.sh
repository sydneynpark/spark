#!/usr/bin/env bash
# Applies this directory's policies to the account: what gives CI its access,
# which the configuration CI applies can't safely manage itself. Run by hand,
# signed in as an administrator, from CloudShell or Git Bash:
#
#   bash terraform/bootstrap/apply.sh
#
# Safe to re-run: it makes the account match these files. (The state bucket
# and the GitHub OIDC provider are made once, by hand; see ../README.md.)

set -euo pipefail
export AWS_PAGER="" AWS_REGION=us-east-1
# Git Bash would otherwise rewrite IAM paths like /service-role/ as file paths.
export MSYS_NO_PATHCONV=1

cd "$(dirname "$0")"
account=$(aws sts get-caller-identity --query Account --output text)

# The files, with the account ID filled in. Relative, so that file:// works
# for both CloudShell's aws and Windows' aws.exe.
filled=$(mktemp -d ./.filled.XXXXXX)
trap 'rm -rf "$filled"' EXIT
for f in *.json; do
  sed "s/ACCOUNT_ID/$account/g" "$f" > "$filled/$f"
done
doc() { echo "file://$filled/$1"; }

echo "Permissions boundary for the roles Terraform manages"
boundary="arn:aws:iam::$account:policy/SiteWorkloadBoundary"
if aws iam get-policy --policy-arn "$boundary" > /dev/null 2>&1; then
  # A policy keeps at most 5 versions: make room by deleting the oldest.
  old=$(aws iam list-policy-versions --policy-arn "$boundary" \
          --query 'Versions[?!IsDefaultVersion].VersionId' --output text)
  if [ "$(wc -w <<< "$old")" -ge 4 ]; then
    aws iam delete-policy-version --policy-arn "$boundary" --version-id "$(tr -s '\t ' '\n' <<< "$old" | tail -1)"
  fi
  aws iam create-policy-version --policy-arn "$boundary" \
    --policy-document "$(doc workload-boundary.json)" --set-as-default > /dev/null
else
  aws iam create-policy --policy-name SiteWorkloadBoundary \
    --description "Caps the roles the site's Terraform configuration manages." \
    --policy-document "$(doc workload-boundary.json)" > /dev/null
fi

echo "Deploy role: exactly one inline policy, Deploy"
role=GithubDeployProduction
aws iam update-assume-role-policy --role-name "$role" --policy-document "$(doc deploy-role-trust.json)"
aws iam put-role-policy --role-name "$role" --policy-name Deploy --policy-document "$(doc deploy-role-policy.json)"
for name in $(aws iam list-role-policies --role-name "$role" --query 'PolicyNames' --output text); do
  [ "$name" = Deploy ] || aws iam delete-role-policy --role-name "$role" --policy-name "$name"
done
for arn in $(aws iam list-attached-role-policies --role-name "$role" --query 'AttachedPolicies[].PolicyArn' --output text); do
  aws iam detach-role-policy --role-name "$role" --policy-arn "$arn"
done

echo "Plan role: ReadOnlyAccess, except secrets and logs"
role=GithubPlanProduction
aws iam update-assume-role-policy --role-name "$role" --policy-document "$(doc plan-role-trust.json)"
aws iam attach-role-policy --role-name "$role" --policy-arn arn:aws:iam::aws:policy/ReadOnlyAccess
aws iam put-role-policy --role-name "$role" --policy-name DenyReadingSecrets --policy-document "$(doc plan-role-deny-secrets.json)"

echo "State bucket policy"
aws s3api put-bucket-policy --bucket spark-wiki-terraform-state --policy "$(doc state-bucket-policy.json)"

echo "Done."
