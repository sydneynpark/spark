# Backend



## Local development

Requirements: 
* Python version 3.12

```ps
python -m venv .env
.env\Scripts\Activate.ps1
pip install -U pip wheel
pip install -r src/requirements.txt
```

## Running Tests

```ps
$env:PYTHONPATH = ".\src"
python -m unittest test\test_markdown_util.py
```

## Dependencies

`src/requirements.in` lists the direct dependencies. `src/requirements.txt` is
generated from it, pinning every package (including transitive ones) to an
exact version and hash; local installs and the deployed Lambda both use it.
After editing `requirements.in`, regenerate it from this directory:

```
uv pip compile src/requirements.in --universal --python-version 3.12 --generate-hashes -o src/requirements.txt
```

Add `--upgrade` to also move everything to the latest versions.

## Deploying

Every push builds this Lambda and plans deploying it, for you to approve -- see [terraform/README.md](../terraform/README.md).

## Two Lambdas: ContentAPI and AdminAPI

This project deploys as two Lambda functions, from the same package
(`terraform/site_api.tf`):

* `ContentAPI` (`src/lambda_function.py`): the public site's API. Its role
  can only read the site's content.
* `AdminAPI` (`src/admin_lambda_function.py`): the admin page's API,
  everything under `/admin/` (`src/handlers/admin.py`). Its role is the only
  one that can read the admin login parameters, or write content.

API Gateway sends `/admin/*` to `AdminAPI` and everything else to
`ContentAPI`. Locally, `run_local.py` serves both from one server.

The admin page publishes a book review by uploading it to the
`spark.wiki.books` bucket as `<title>.md`, in the exact format a manual
upload would use, so `UpdateBookReview`'s S3 trigger enriches it and writes
it to DynamoDB. Photos go from the browser straight to `spark.wiki.photos`,
through presigned PUT URLs (full-size photos are bigger than API Gateway and
Lambda accept in a request), and `UpdatePhotoMetadata`'s S3 trigger
processes each one, as it would one uploaded in the console.

Locally, the uploader treats `sample-data/photos/originals` (at the repo
root) as the bucket, and uploads land there. Nothing processes them automatically: run
`ContentManagement/UpdatePhotoMetadata/run_local.py` (see its README) to add
them to the local gallery.

### Admin login (one-time, AWS-side)

`AdminAPI` reads the admin credentials and token signing secret from SSM
Parameter Store, which Terraform doesn't manage (see
[terraform/README.md](../terraform/README.md)). Run
`python scripts/generate_admin_credentials.py` from the repo root (it
imports the same `hash_password` the backend verifies logins with, so the
hash format can't drift out of sync) and follow the printed
`aws ssm put-parameter` commands. They create three **SecureString**
parameters in `us-east-1`: `AdminUsername`, `AdminPasswordHash`, and
`AdminTokenSecret`.

To change the admin password later, re-run the generator script and update
just the `AdminPasswordHash` parameter.
