# Infrastructure and deploys

Everything in AWS that the site runs on is managed here, by Terraform, in
one configuration that only GitHub Actions applies -- except what gives
GitHub Actions its access, the [bootstrap](#bootstrap), which you apply by
hand.

- `site_frontend.tf`: https://spark.wiki -- the frontend's bucket, its files,
  and the CloudFront distribution serving them.
- `site_api.tf`: https://api.spark.wiki -- the `ContentAPI` Lambda (the
  backend), and the API Gateway REST API and custom domain in front of it.
- `site_cdn.tf`: https://photos.spark.wiki and https://books.spark.wiki --
  the CloudFront distributions serving photos, thumbnails, and book covers
  from their private buckets, and their WAF web ACLs.
- `site_dns.tf`: the `spark.wiki` Route 53 zone, and the TLS certificates.
- `content_storage.tf`: the content buckets (photos, thumbnails, book reviews
  and covers, blog posts) and DynamoDB tables.
- `content_lambdas.tf`: the Lambdas that process uploaded content, and the
  S3 triggers that invoke them.
- `modules/python_lambda`: one of this repo's Lambda projects, deployed as a
  function, with its log group and its execution role.
- `imports.tf`: adoption of what was made in the console.

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
- **A Lambda's permissions**: the `policy` in its `module` block. The module
  adds writing to its own log group, and removes any permission granted any
  other way (e.g. a policy attached in the console). Each role also carries
  the [permissions boundary](#bootstrap): a permission the boundary doesn't
  allow has no effect until it's added there too.
- **A Lambda's dependencies**: see its project's README.
- **A Lambda's Python version**: edit the project's `.python-version`; the
  build and the function's runtime both follow it. `UpdatePhotoMetadata`'s
  Pillow layer is built for Python 3.12, so it has to change along with it,
  as does the deploy role's `PillowLayer` statement.
- **A new frontend file type**: plans fail on extensions missing from
  `content_types` in [site_frontend.tf](site_frontend.tf); add it there.
- **A new Lambda**: create it in the console first, with an execution role
  (the deploy role can create neither). Add both to the
  [deploy role's policy](bootstrap/deploy-role-policy.json)
  (`ManageFunctions`, `PassLambdaRoles`, `ManageWorkloadRolePolicies`,
  `UpdateWorkloadRoles`, `ManageLogGroups`), and apply the bootstrap. Then
  add a `module` block; `import` blocks for the function, role, and log
  group; and a build step to [deploy.yml](../.github/workflows/deploy.yml).
- **Anything else new** (a bucket, a table, a parameter): add it to the deploy
  role's policy, and to the boundary if a Lambda will use it, and apply the
  bootstrap. Then add it here.
- **Secrets** (the SSM parameters): set them in the console, or with
  `aws ssm put-parameter`. They aren't managed here: Terraform would store
  their values in its state, which the plan role can read, as can anyone who
  can download a Deploy run's `tfplan` artifact. The Lambdas' policies grant
  access to them by name.

## Adopting what was made in the console

[imports.tf](imports.tf) imports every resource the console made. The
configuration matches each one's settings as they were, apart from the
deliberate changes below. To adopt them:

1. **Apply the bootstrap** (`bash terraform/bootstrap/apply.sh`, signed in
   as an administrator). The deploy role needs its new permissions before a
   deploy can manage anything new.

2. **Push**, and read the Deploy run's plan. Besides the imports, expect:
   - **API Gateway**: a new deployment, with the `LIVE` stage switched to it,
     and the stage's logging changed from `INFO` with full request and
     response bodies (`dataTraceEnabled`) to `ERROR` only. Those bodies
     include admin passwords and tokens.
   - **Log retention**: 3 days for `UpdateBookReview`'s logs and the API's
     execution logs, which never expired. (Their older logs get deleted.)
   - **IAM**: each Lambda's role, and API Gateway's logging role, gets the
     permissions boundary and a new inline policy granting what its code
     uses, and has its console-made policies detached. That drops access the
     functions had but didn't use: `UpdatePhotoMetadata` and
     `UpdateBlogPostMetadata` could read every bucket in the account,
     Terraform's state included. It also adds what was missing:
     `UpdateBlogPostMetadata` couldn't write its logs, and `UpdateBookReview`
     couldn't delete a deleted review's cover.
   - **Public access blocks** turned on for `spark.wiki.photos` and
     `spark.wiki.thumbnails`, which only CloudFront reads anyway.
   - Two IAM role descriptions, corrected.
   - Possibly, the content buckets' S3 triggers rewritten in place: the same
     triggers, with new IDs.
   - The frontend files and CloudFront invalidation, if the build changed.

   Anything else is a setting the configuration doesn't match yet: fix the
   configuration, and push again. Once the plan looks right, approve it.

3. **Once it's applied**, empty [imports.tf](imports.tf), keeping its header.

4. **Clean up** the leftovers in the console. Nothing uses them, and
   Terraform doesn't manage them:
   - **IAM policies**, by then detached from every role: `DeployBackend`,
     `DeployFrontend`, `DeployMetadataHandlers`, `ManageTerraformState`,
     `GetBlogPosts`, `GetBookReviews`, `GetPhotos`, `InvokeContentAPILambda`,
     `PutBookReviewDocuments`, `ReadAdminLogin`, `ReadGoogleDeveloperSecrets`,
     `ReadThumbnails`, `ReadWriteBookReviews`, `ReadWritePhotoDetails`,
     `SaveBookCovers`, `SaveThumbnails`, `UploadPhotosToS3`, and the
     `service-role/AWSLambda*ExecutionRole-*` ones. (The first three, and
     `ReadGoogleBooksAPIKey`, are also attached to the `deploy` user.)
   - **The `deploy` and `script` IAM users**, and their access keys, which
     the workflows replaced. Then delete the local copies:
     `scripts/.accessKey`, `scripts/.secretAccessKey`, `scripts/deploy.user/`,
     and `scripts/script.user/`.
   - **The `UpdateBlogPostMetadata-role-wpza4kb8` role**: an unused
     duplicate of `Lambda_UpdateBlogPostMetadata`.
   - **ContentAPI's stale invoke permissions**: its resource policy still
     allows an API Gateway API that no longer exists (`4vs4x6dse4`), and has
     redundant grants for this one. Terraform manages only the statement
     `d7be9d2e-a636-51e7-bb87-00c1c55fc32b`. Remove each of the rest with
     `aws lambda remove-permission --function-name ContentAPI --statement-id <id>`:
     `9b0032c3-05dd-5b6d-9659-1ef98d4e2340`,
     `31184592-0cb9-5691-8189-643a16c01f0f`,
     `43953cb5-42de-55e1-8c5c-c79b6eb916c2`, `APIGatewayCanInvoke`, and
     `0d507450-e3cf-5433-917e-9b5d254b600c`.
   - **Two unused certificates**, which can't renew, and expire in January
     and February 2027: `spark.wiki, photos.spark.wiki` (`a5b8b419-...`) and
     `spark.wiki, books.spark.wiki` (`713d4f16-...`). Then their validation
     records, `_b597e6bc...photos.spark.wiki` and
     `_de743a0e...books.spark.wiki`. (The wildcard certificate covers both
     subdomains.)
   - **The `/aws/apigateway/welcome` log group**, and the API's old
     deployments (the stage only uses its current one).
   - **Files from before Terraform managed the frontend bucket**, which
     aren't in its state, so it won't remove them: the ones without a
     `ManagedBy` tag.

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
ID and makes the account match the files, so it's safe to re-run:

- **[workload-boundary.json](bootstrap/workload-boundary.json)**: the
  permissions boundary, `SiteWorkloadBoundary`. Every role Terraform manages
  carries it, which caps what any of them can do at the site's buckets,
  tables, parameters, and logs. The deploy role can change a role's
  permissions only while the role carries the boundary, and it can't change
  the boundary itself. Without that, managing IAM would let a deploy grant
  itself anything.
- **[deploy-role-policy.json](bootstrap/deploy-role-policy.json)** and
  **[deploy-role-trust.json](bootstrap/deploy-role-trust.json)**: the
  deploy role, `GithubDeployProduction`, which Deploy's apply job and the
  Refresh workflows use. It can manage what this configuration manages, and
  nothing else. It can't create or delete buckets, tables, distributions, or
  functions, or change the CI roles. It trusts only jobs in the `production`
  environment. (The `sub` has to name the environment, not a branch: jobs
  that declare an environment get a token identifying the environment
  instead of their branch.) The script removes any other policy from it.
- **[plan-role-trust.json](bootstrap/plan-role-trust.json)** and
  **[plan-role-deny-secrets.json](bootstrap/plan-role-deny-secrets.json)**:
  the plan role, `GithubPlanProduction`, which Deploy's plan job uses. It has
  the AWS managed policy `ReadOnlyAccess`, so it can plan whatever this
  configuration grows to manage, minus reading parameter values and logs. It
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
