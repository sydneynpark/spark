# Infrastructure and deploys

Everything in AWS is on its way to being managed here, by Terraform, in one
configuration that only GitHub Actions applies. Today that's the four Lambda
functions and the frontend's files; the rest was made by hand in the console,
and is being brought in incrementally ([below](#bringing-the-rest-under-terraform)).

Files prefixed `site_` are the site (the frontend, and the API behind it),
`content_` the content-management pipeline (the Lambdas that process uploaded
photos, posts, and reviews). `modules/python_lambda` deploys one of this
repo's Lambda projects.

## How changes reach AWS

Pull requests are planned, and merges to `master` are applied:

- **[Plan](../.github/workflows/plan.yml)**, on every pull request: builds
  everything, then runs `terraform plan` with a read-only role -- what
  merging would change.
- **[Deploy](../.github/workflows/deploy.yml)**, on every push to `master`:
  builds everything, then runs `terraform apply`, which changes only what
  differs from what's deployed.

Both build with [Build](../.github/workflows/build.yml):

- **Lambdas**: [scripts/build_lambda.py](../scripts/build_lambda.py)
  packages a project as `.build/lambda.zip` -- its `src/` plus the locked
  `src/requirements.txt`, installed for the project's `.python-version` on
  Lambda's platform. The zip is reproducible, so a function is only
  redeployed when something in it changed.
- **Frontend**: `npm run build`. Terraform uploads changed files, deletes ones
  no longer in the build, and if anything changed, invalidates CloudFront
  once they're all uploaded ([site_frontend.tf](site_frontend.tf)).

When `UpdatePhotoMetadata`'s or `UpdateBookReview`'s source changes,
Deploy also reprocesses every existing photo or review with the new code
([content_reprocess.tf](content_reprocess.tf)).

The workflows authenticate to AWS through GitHub's OIDC provider, so there
are no AWS credentials stored anywhere. The deploy role trusts only jobs in
this repo's `production` environment, which only `master` can deploy to; the
plan role, only pull requests from this repo's own branches (GitHub doesn't
give pull requests from forks a token).

To roll back, revert the commit and merge. To redeploy without a change, run
Deploy from the Actions tab.

## One-time setup

1. **Create the bootstrap resources** in the console -- the state bucket,
   OIDC provider, deploy role, and plan role -- as described
   [below](#bootstrap-resources).

2. **Configure the repo** in GitHub's Settings:
   - Environments > New environment `production`: under Deployment branches
     and tags, *Selected branches and tags*, add `master`. Add the variable
     `AWS_DEPLOY_ROLE_ARN` = the deploy role's ARN. (Optionally, add yourself
     as a Required reviewer, to approve each deploy before it starts.)
   - Secrets and variables > Actions > Variables: add the repository
     variable `AWS_PLAN_ROLE_ARN` = the plan role's ARN.

3. **Open the pull request** that adds all this, and read its Plan job's
   output. The functions were created in the console, so this first deploy
   imports them ([imports.tf](imports.tf)). Expect:
   - per function: an import, a code update, and a new `ManagedBy` tag
   - every frontend file uploaded, and one CloudFront invalidation
   - both reprocessing steps created -- they'll reprocess every photo and
     review, since Terraform hasn't seen this code before

   Anything else is a console setting the configuration doesn't match yet.
   Add it to the function's `module` block, and push again.

4. **Merge**, and watch Deploy in the Actions tab.

5. **Delete the previous build's leftovers** from `spark.wiki.frontend`, if
   you like: files from before Terraform managed the bucket aren't in its
   state, so it won't remove them. They're the ones without a `ManagedBy`
   tag (old `static/` files with different hashes in their names).

6. **Retire the old access keys**: in IAM, delete the access keys of the
   `deploy` user and of the user the refresh scripts used (and the users
   themselves, if nothing else uses them). Then delete the local copies:
   `scripts/.accessKey`, `scripts/.secretAccessKey`, `scripts/deploy.user/`,
   and `scripts/script.user/`.

## Day to day

- **Reprocessing content by hand**, e.g. without a code change: the
  `scripts/refresh*.py` scripts use your `aws login` session (or
  `AWS_PROFILE`), and the packages in `scripts/requirements.txt`. If one
  can't find credentials, export the session into your shell (PowerShell):
  `aws configure export-credentials --format powershell | Invoke-Expression`.
- **After changing anything Terraform manages in the console**, copy the
  change into its configuration: the next deploy reverts whatever the
  configuration doesn't match.
- **A Lambda's dependencies**: see its project's README.
- **A Lambda's Python version**: edit the project's `.python-version`; the
  build and the function's runtime both follow it. `UpdatePhotoMetadata`'s
  Pillow layer is built for Python 3.12, so it has to change along with it,
  as does the deploy role's `PillowLayer` statement.
- **A new frontend file type**: plans fail on extensions missing from
  `content_types` in [site_frontend.tf](site_frontend.tf); add it there.
- **A new Lambda**: create it in the console first (the deploy role can't
  create functions), with its execution role. Add both to the deploy role's
  policy (`ManageFunctions`, `PassExecutionRoles`), and update the copy
  below. Then add a `module` block and an `import` block for it, and a
  build step to [build.yml](../.github/workflows/build.yml).

## Bringing the rest under Terraform

One area per pull request:

1. Add its configuration, and an `import` block for each existing resource
   to [imports.tf](imports.tf). Write the configuration from the resource's
   current settings (e.g. the output of the AWS CLI's `get`/`describe`
   commands for it), so that importing it changes nothing.
2. Open the pull request. Its plan should show each resource imported,
   with no changes. Any change means the configuration doesn't match what
   exists yet, and merging would apply that change to the live resource.
3. Extend the deploy role's policy to manage the new resources (the plan
   role can already read everything). Then merge.
4. Replace the hardcoded names and IDs that now have resources with
   references to them (e.g. the distribution ID in
   [site_frontend.tf](site_frontend.tf)).

A suggested order, least risky first:

- **DynamoDB tables**, with `lifecycle { prevent_destroy = true }`.
- **S3 buckets** and their settings, also with `prevent_destroy`; then the
  content triggers (each bucket's notification configuration, and the
  permission it has to invoke its Lambda).
- **CloudFront** distributions, their ACM certificates, and DNS (Route 53).
- **API Gateway**.
- **SSM parameters**: their names and types only. Their values stay out of
  Terraform, whose state stores everything in plain text.
- **IAM**: the Lambdas' execution roles. First, give the deploy role IAM
  access limited by a permissions boundary: a policy you write by hand,
  capping what any role it manages can do (e.g. only this site's buckets,
  tables, logs, and parameters). Let the deploy role create or change roles
  only if they carry that boundary, and never change the boundary or its own
  role. Without that, managing IAM would let a deploy grant itself anything.

What stays out of this configuration is the bootstrap: the resources that
give CI its access ([below](#bootstrap-resources), plus the permissions
boundary, once there is one). A configuration CI applies can't safely manage
the role CI applies it with. They can become a separate Terraform
configuration later, applied by hand -- e.g. from AWS CloudShell, which needs
no local setup.

## Bootstrap resources

Made by hand in the console. `ACCOUNT_ID` below stands for the AWS account's
ID.

### Terraform state bucket

`spark-wiki-terraform-state`, in `us-east-1` (the `backend "s3"` block in
[main.tf](main.tf) expects exactly this). Block all public access, versioning
enabled, default SSE-S3 encryption, and optionally a lifecycle rule
permanently deleting noncurrent versions after 90 days. Bucket policy:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "DenyInsecureTransport",
      "Effect": "Deny",
      "Principal": "*",
      "Action": "s3:*",
      "Resource": [
        "arn:aws:s3:::spark-wiki-terraform-state",
        "arn:aws:s3:::spark-wiki-terraform-state/*"
      ],
      "Condition": {
        "Bool": {
          "aws:SecureTransport": "false"
        }
      }
    }
  ]
}
```

### GitHub OIDC provider

An IAM identity provider of type OpenID Connect, with provider URL
`https://token.actions.githubusercontent.com` and audience
`sts.amazonaws.com`.

### Deploy role

Used by Deploy. Trust policy -- the `sub` condition has to name the
environment, not a branch: jobs that declare `environment: production` get a
token identifying that environment instead of their branch.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::ACCOUNT_ID:oidc-provider/token.actions.githubusercontent.com"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "token.actions.githubusercontent.com:aud": "sts.amazonaws.com",
          "token.actions.githubusercontent.com:sub": "repo:sydneynpark/spark:environment:production"
        }
      }
    }
  ]
}
```

Permissions, as a single inline policy (and nothing else attached):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "TerraformStateList",
      "Effect": "Allow",
      "Action": "s3:ListBucket",
      "Resource": "arn:aws:s3:::spark-wiki-terraform-state"
    },
    {
      "Sid": "TerraformStateObjects",
      "Effect": "Allow",
      "Action": ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"],
      "Resource": "arn:aws:s3:::spark-wiki-terraform-state/terraform.tfstate*"
    },
    {
      "Sid": "ManageFunctions",
      "Effect": "Allow",
      "Action": [
        "lambda:Get*",
        "lambda:List*",
        "lambda:UpdateFunctionCode",
        "lambda:UpdateFunctionConfiguration",
        "lambda:TagResource",
        "lambda:UntagResource"
      ],
      "Resource": [
        "arn:aws:lambda:us-east-1:ACCOUNT_ID:function:ContentAPI",
        "arn:aws:lambda:us-east-1:ACCOUNT_ID:function:ContentAPI:*",
        "arn:aws:lambda:us-east-1:ACCOUNT_ID:function:UpdatePhotoMetadata",
        "arn:aws:lambda:us-east-1:ACCOUNT_ID:function:UpdatePhotoMetadata:*",
        "arn:aws:lambda:us-east-1:ACCOUNT_ID:function:UpdateBlogPostMetadata",
        "arn:aws:lambda:us-east-1:ACCOUNT_ID:function:UpdateBlogPostMetadata:*",
        "arn:aws:lambda:us-east-1:ACCOUNT_ID:function:UpdateBookReview",
        "arn:aws:lambda:us-east-1:ACCOUNT_ID:function:UpdateBookReview:*"
      ]
    },
    {
      "Sid": "PassExecutionRoles",
      "Effect": "Allow",
      "Action": "iam:PassRole",
      "Resource": [
        "arn:aws:iam::ACCOUNT_ID:role/service-role/ContentAPI-role-rab0br82",
        "arn:aws:iam::ACCOUNT_ID:role/service-role/Lambda_UpdatePhotoMetadata",
        "arn:aws:iam::ACCOUNT_ID:role/Lambda_UpdateBlogPostMetadata",
        "arn:aws:iam::ACCOUNT_ID:role/service-role/UpdateBookReview-role-qcl2ltqh"
      ],
      "Condition": {
        "StringEquals": { "iam:PassedToService": "lambda.amazonaws.com" }
      }
    },
    {
      "Sid": "PillowLayer",
      "Effect": "Allow",
      "Action": "lambda:GetLayerVersion",
      "Resource": "arn:aws:lambda:us-east-1:770693421928:layer:Klayers-p312-pillow:*"
    },
    {
      "Sid": "FrontendList",
      "Effect": "Allow",
      "Action": ["s3:ListBucket", "s3:ListBucketVersions"],
      "Resource": "arn:aws:s3:::spark.wiki.frontend"
    },
    {
      "Sid": "FrontendObjects",
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:GetObjectTagging",
        "s3:PutObject",
        "s3:PutObjectTagging",
        "s3:DeleteObject",
        "s3:DeleteObjectVersion"
      ],
      "Resource": "arn:aws:s3:::spark.wiki.frontend/*"
    },
    {
      "Sid": "FrontendInvalidation",
      "Effect": "Allow",
      "Action": [
        "cloudfront:GetDistribution",
        "cloudfront:CreateInvalidation",
        "cloudfront:GetInvalidation"
      ],
      "Resource": "arn:aws:cloudfront::ACCOUNT_ID:distribution/E2JO5BSJ5WRP9P"
    },
    {
      "Sid": "BooksInvalidation",
      "Effect": "Allow",
      "Action": "cloudfront:CreateInvalidation",
      "Resource": "arn:aws:cloudfront::ACCOUNT_ID:distribution/E2Y8FRIT378S9Y"
    },
    {
      "Sid": "ContentRefreshList",
      "Effect": "Allow",
      "Action": "s3:ListBucket",
      "Resource": ["arn:aws:s3:::spark.wiki.photos", "arn:aws:s3:::spark.wiki.books"]
    },
    {
      "Sid": "ContentRefreshInvoke",
      "Effect": "Allow",
      "Action": "lambda:InvokeFunction",
      "Resource": [
        "arn:aws:lambda:us-east-1:ACCOUNT_ID:function:UpdatePhotoMetadata",
        "arn:aws:lambda:us-east-1:ACCOUNT_ID:function:UpdateBookReview"
      ]
    }
  ]
}
```

`E2JO5BSJ5WRP9P` serves the frontend, and `E2Y8FRIT378S9Y` the
`spark.wiki.books` bucket (reviews and covers).

### Plan role

Used by Plan. Trust policy:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::ACCOUNT_ID:oidc-provider/token.actions.githubusercontent.com"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "token.actions.githubusercontent.com:aud": "sts.amazonaws.com",
          "token.actions.githubusercontent.com:sub": "repo:sydneynpark/spark:pull_request"
        }
      }
    }
  ]
}
```

Permissions: the AWS managed policy `ReadOnlyAccess`, so it can plan
whatever this configuration grows to manage. (That includes reading data,
like S3 objects and DynamoDB items, but not decrypting SecureString
parameters.)
