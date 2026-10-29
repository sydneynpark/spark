# Infrastructure and deploys

Everything in AWS that the site runs on is managed here, by Terraform, in
one configuration that only GitHub Actions applies -- except what gives
GitHub Actions its access, the [bootstrap](#bootstrap), which you apply by
hand.

- `site_frontend.tf`: https://spark.wiki -- the frontend's bucket, its files,
  and the CloudFront distribution serving them.
- `site_api.tf`: https://api.spark.wiki -- the backend's Lambdas,
  `ContentAPI` (the public, read-only API) and `AdminAPI` (`/admin/*`, the
  only one that can write), and the API Gateway REST API and custom domain
  in front of them.
- `site_cdn.tf`: https://photos.spark.wiki and https://books.spark.wiki --
  the CloudFront distributions serving photos, thumbnails, and book covers
  from their private buckets, and their WAF web ACLs.
- `site_dns.tf`: the `spark.wiki` Route 53 zone, and the TLS certificates.
- `content_storage.tf`: the content buckets (photos -- birds/ and photos/ --
  thumbnails, book reviews and covers, blog posts) and DynamoDB tables.
- `content_lambdas.tf`: the Lambdas that process uploaded content, and the
  S3 triggers that invoke them.
- `modules/python_lambda`: one of this repo's Lambda projects, deployed as a
  function, with its log group and its execution role.

## How changes reach AWS

One workflow, **[Deploy](../.github/workflows/deploy.yml)**, runs on every
push to any branch:

```
build frontend ┐
build lambdas  ┴→ plan → (waits for your approval) → apply
```

- **Build**: [scripts/build_lambda.py](../scripts/build_lambda.py) packages
  each Lambda project as `.build/lambda.zip` -- its `src/` plus the locked
  `src/requirements.txt`, installed for the project's `.python-version` on
  Lambda's platform -- and `npm run build` builds the frontend. Both are
  reproducible, so unchanged code is never redeployed.
- **Plan**: `terraform plan` with a read-only role, against the build -- what
  deploying this push would change. Read it in the job's log.
- **Apply**: the job declares the `production` environment, whose required
  reviewer is you, so the run stops here with a *Review deployments* button.
  Approving applies exactly the plan you read, using the same build. If
  anything else was deployed since that plan was made, Terraform refuses it
  as stale, so approving an old run can't roll production back.

Terraform uploads changed frontend files, deletes ones no longer in the
build, and if anything changed, invalidates CloudFront once they're all
uploaded ([site_frontend.tf](site_frontend.tf)).

So any branch can be tried out in production before it's merged. Production
is whatever was applied last: applying one branch undoes whatever another
branch applied that isn't on it, and if a branch was applied before it was
merged, `master`'s plan afterwards shows no changes. Runs you don't approve
just expire.

Two more workflows only run when you start them from the Actions tab (Run
workflow), and also wait for your approval:
**[Refresh photo metadata](../.github/workflows/refresh-photos.yml)** and
**[Refresh book review data](../.github/workflows/refresh-book-reviews.yml)**.
They reprocess every existing photo or review, as if each were uploaded
again -- e.g. after changing what metadata the Lambda stores.

The workflows authenticate to AWS through GitHub's OIDC provider, so there
are no AWS credentials stored anywhere. The plan role trusts pushes to any
of this repo's branches (which only people with write access can make), and
can read the configuration of everything, but not secrets or logs. The
deploy role trusts only jobs in the `production` environment, which can't
start without your approval.

To roll back, re-run `master`'s latest Deploy run (Re-run all jobs) and
approve it, or revert the change and push.

## Day to day

- **Reprocessing content**: run a Refresh workflow. To run the scripts
  locally instead (e.g. `refreshBookReviewData.py --missing-only`, or on just
  one prefix), `scripts/refresh*.py` use your `aws login` session (or
  `AWS_PROFILE`), and the packages in `scripts/requirements.txt`. If one
  can't find credentials, export the session into your shell (PowerShell):
  `aws configure export-credentials --format powershell | Invoke-Expression`.
- **After changing anything Terraform manages in the console**, copy the
  change into its configuration: the next deploy reverts whatever the
  configuration doesn't match.
- **A Lambda's permissions**: the `policy` in its `module` block, which
  becomes a managed policy named after the function, under the IAM path
  `/site-workload/`, attached to a role also named after the function, under
  the same path. The module adds writing to its own log group, and
  removes any permission granted any other way (e.g. a policy attached in
  the console). Each role also carries the
  [permissions boundary](#bootstrap): a permission the boundary doesn't
  allow has no effect until it's added there too.
- **No inline policies**, anywhere: every policy is a managed one, with a
  name.
- **A Lambda's dependencies**: see its project's README.
- **A Lambda's Python version**: edit the project's `.python-version`; the
  build and the function's runtime both follow it. `UpdatePhotoMetadata`'s
  Pillow layer is built for Python 3.12, so it has to change along with it.
- **A new frontend file type**: plans fail on extensions missing from
  `content_types` in [site_frontend.tf](site_frontend.tf); add it there.
- **A new Lambda**: add a `module` block, and a build step to
  [deploy.yml](../.github/workflows/deploy.yml). Terraform creates the
  function, its role, and its log group.
- **Anything else new**: just add it here, as long as the deploy role can
  manage it (see [Bootstrap](#bootstrap)): any Lambda function, API Gateway
  API, CloudFront distribution, WAF web ACL, certificate, or DNS record, and
  any bucket or table named `spark.wiki.*`. If a Lambda will use a new
  bucket, table, or parameter, add it to the
  [boundary](bootstrap/workload-boundary.json) too, and apply the bootstrap
  first. Anything else needs the deploy role's policies changed.
- **Secrets** (the SSM parameters): set them in the console, or with
  `aws ssm put-parameter`. They aren't managed here: Terraform would store
  their values in its state, which the plan role can read, as can anyone who
  can download a Deploy run's `tfplan` artifact. The Lambdas' policies grant
  access to them by name.

## Not managed here

- **The [bootstrap](#bootstrap)**: a configuration CI applies can't safely
  manage the roles CI applies it with.
- **SSM parameters**: see *Secrets*, above.
- **Defaults AWS makes in every account**: the default VPC (and its subnets,
  internet gateway, route table, network ACL, and security group -- nothing
  here runs in a VPC), service-linked roles, AWS managed KMS keys, and the
  default EventBridge bus, Athena workgroup, X-Ray sampling rule, and
  MemoryDB and ElastiCache users and parameter groups.
- **Account settings**: the budget, cost anomaly detection, Resource
  Explorer, and MFA devices.
- **The domain's registration**: `spark.wiki` is registered outside this
  account, and delegated to the zone's name servers.

## Bootstrap

What gives CI its access lives in [bootstrap/](bootstrap), and you apply it
by hand with [bootstrap/apply.sh](bootstrap/apply.sh), signed in as an
administrator, from CloudShell or Git Bash. The script fills in the account
ID and makes the account match the files, so it's safe to re-run. Every
policy is a managed one, and the script removes any other policy (inline
ones included) from the CI roles:

- **[workload-boundary.json](bootstrap/workload-boundary.json)**: the
  permissions boundary, `SiteWorkloadBoundary`. Every role Terraform manages
  carries it, which caps what any of them can do at the site's buckets,
  tables, parameters, and logs. Of the content, it can delete only what
  the Lambdas derive from the rest (book covers, and thumbnails), and the
  admin page's blog post drafts, which aren't on the site (under the blog
  bucket's `drafts/`), so no deployed code can delete a photo, review, or
  post -- though it could
  still overwrite one, since the buckets aren't versioned. Logs it allows
  everywhere: API Gateway refuses a logging role that can't use any log
  group. The deploy role
  can change a role's permissions only while the role carries the
  boundary, and it can't change
  the boundary itself. Without that, managing IAM would let a deploy grant
  itself anything.
- **[deploy-core.json](bootstrap/deploy-core.json),
  [deploy-iam.json](bootstrap/deploy-iam.json),
  [deploy-storage.json](bootstrap/deploy-storage.json),
  [deploy-edge.json](bootstrap/deploy-edge.json)**, and
  **[deploy-role-trust.json](bootstrap/deploy-role-trust.json)**: the
  deploy role, `GithubDeployProduction`, which Deploy's apply job and the
  Refresh workflows use, with the policies `SiteDeployCore`,
  `SiteDeployIAM`, `SiteDeployStorage`, `SiteDeployEdge`, and
  `SiteDeployGuardrails`. It trusts only jobs in the `production`
  environment. (The `sub` has to name the environment, not a branch: jobs
  that declare an environment get a token identifying the environment
  instead of their branch.) The account holds only the site, so what it can do is
  scoped by convention rather than resource by resource, and adding
  something rarely needs the bootstrap changed:
  - **Everything in the services the site uses**: Lambda, API Gateway,
    CloudFront, WAF, ACM, and Route 53, plus buckets and tables named
    `spark.wiki.*`, and the Lambdas' and API Gateway's log groups.
  - **Roles, only under `/site-workload/`**, and only carrying the
    boundary. Those are the only roles it can pass to Lambda or API Gateway,
    so nothing it deploys can run with more than the boundary allows. It can
    attach only policies under `/site-workload/` (which it can create) and
    API Gateway's AWS managed logging policy.
  - **Never** ([deploy-guardrails.json](bootstrap/deploy-guardrails.json),
    whose denies override every allow): change the CI roles, any policy
    outside `/site-workload/` (the boundary included), or any IAM user,
    group, access key, identity provider, or account setting; remove a
    role's boundary; change the Terraform state bucket, or delete old
    versions of the state; delete the content buckets, or write or delete
    anything in them; delete the tables or the hosted zone. These are what
    a mistaken deploy couldn't undo. (`prevent_destroy` guards some of
    them too, but a branch can delete that line; it can't change these.)
    Replacing one of them on purpose means lifting its deny for that
    deploy.

  The policies are split up because a managed policy can be at most 6,144
  characters.
- **[plan-role-trust.json](bootstrap/plan-role-trust.json)** and
  **[plan-role-deny-secrets.json](bootstrap/plan-role-deny-secrets.json)**:
  the plan role, `GithubPlanProduction`, which Deploy's plan job uses. It has
  the AWS managed policy `ReadOnlyAccess`, so it can plan whatever this
  configuration grows to manage, and `SitePlanDenySecrets`, which takes away
  reading parameter values and logs. It
  trusts pushes to any branch.
- **[state-bucket-policy.json](bootstrap/state-bucket-policy.json)**: the
  Terraform state bucket's policy.

Made once by hand, before the first run:

- **The Terraform state bucket**, `spark-wiki-terraform-state`, in
  `us-east-1` (the `backend "s3"` block in [main.tf](main.tf) expects
  exactly this): block all public access, versioning enabled, default SSE-S3
  encryption, and a lifecycle rule permanently deleting noncurrent versions
  after 5 days.
- **The GitHub OIDC provider**: an IAM identity provider of type OpenID
  Connect, with provider URL `https://token.actions.githubusercontent.com`
  and audience `sts.amazonaws.com`.
- **The two roles**, `GithubDeployProduction` and `GithubPlanProduction`,
  with any trust policy (the script replaces it). Then run the script, and
  in the repo's Settings on GitHub:
  - Environments > New environment `production`: check Required reviewers,
    and add yourself. Leave Deployment branches and tags at *No
    restriction*.
  - Secrets and variables > Actions > Variables: add two repository
    variables, `AWS_DEPLOY_ROLE_ARN` = the deploy role's ARN, and
    `AWS_PLAN_ROLE_ARN` = the plan role's ARN.
