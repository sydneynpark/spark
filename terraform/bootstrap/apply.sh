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

# policy NAME FILE DESCRIPTION: makes the managed policy NAME's document FILE.
policy() {
  local arn="arn:aws:iam::$account:policy/$1"
  if aws iam get-policy --policy-arn "$arn" > /dev/null 2>&1; then
    # A policy keeps at most 5 versions: make room by deleting the oldest.
    local old
    old=$(aws iam list-policy-versions --policy-arn "$arn" \
            --query 'Versions[?!IsDefaultVersion].VersionId' --output text)
    if [ "$(wc -w <<< "$old")" -ge 4 ]; then
      aws iam delete-policy-version --policy-arn "$arn" --version-id "$(tr -s '\t ' '\n' <<< "$old" | tail -1)"
    fi
    aws iam create-policy-version --policy-arn "$arn" --policy-document "$(doc "$2")" --set-as-default > /dev/null
  else
    aws iam create-policy --policy-name "$1" --description "$3" --policy-document "$(doc "$2")" > /dev/null
  fi
}

# role_policies ROLE ARN...: makes exactly these managed policies ROLE's
# permissions, attaching them before removing anything else (inline policies
# included).
role_policies() {
  local role="$1"; shift
  local arn name
  for arn in "$@"; do
    aws iam attach-role-policy --role-name "$role" --policy-arn "$arn"
  done
  for name in $(aws iam list-role-policies --role-name "$role" --query 'PolicyNames' --output text); do
    aws iam delete-role-policy --role-name "$role" --policy-name "$name"
  done
  for arn in $(aws iam list-attached-role-policies --role-name "$role" --query 'AttachedPolicies[].PolicyArn' --output text); do
    [[ " $* " == *" $arn "* ]] || aws iam detach-role-policy --role-name "$role" --policy-arn "$arn"
  done
}

ours="arn:aws:iam::$account:policy"

echo "Permissions boundary for the roles Terraform manages"
policy SiteWorkloadBoundary workload-boundary.json "Caps the roles the site's Terraform configuration manages."

echo "Deploy role"
policy SiteDeployCore deploy-core.json "Deploy role: Terraform state, Lambda functions, and the roles they run as."
policy SiteDeployIAM deploy-iam.json "Deploy role: the workload roles and their policies, within the boundary."
policy SiteDeployStorage deploy-storage.json "Deploy role: buckets, frontend files, tables, and log groups."
policy SiteDeployEdge deploy-edge.json "Deploy role: API Gateway, CloudFront, WAF, certificates, and DNS."
policy SiteDeployGuardrails deploy-guardrails.json "Deploy role: what it can never do, whatever the others allow."
aws iam update-assume-role-policy --role-name GithubDeployProduction --policy-document "$(doc deploy-role-trust.json)"
role_policies GithubDeployProduction \
  "$ours/SiteDeployCore" "$ours/SiteDeployIAM" "$ours/SiteDeployStorage" "$ours/SiteDeployEdge" \
  "$ours/SiteDeployGuardrails"

echo "Plan role"
policy SitePlanDenySecrets plan-role-deny-secrets.json "Plan role: no reading parameter values or logs."
aws iam update-assume-role-policy --role-name GithubPlanProduction --policy-document "$(doc plan-role-trust.json)"
role_policies GithubPlanProduction \
  arn:aws:iam::aws:policy/ReadOnlyAccess "$ours/SitePlanDenySecrets"

echo "State bucket policy"
aws s3api put-bucket-policy --bucket spark-wiki-terraform-state --policy "$(doc state-bucket-policy.json)"

echo "Done."
