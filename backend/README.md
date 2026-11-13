# Backend



## Local development

To run the site, backend included, use `./dev up` from the repo root (see
the [README](../README.md)).

For an editor or a quick script outside that, a virtualenv with the locked
dependencies: from this directory, with [uv](https://docs.astral.sh/uv/)
(which installs Python 3.12, from `.python-version`, if needed),

```sh
uv sync    # creates .venv
```

## Running Tests

```sh
PYTHONPATH=src uv run python -m unittest discover test
```

## Dependencies

`pyproject.toml` lists the direct dependencies. `uv.lock` pins every package
(including transitive ones) to an exact version and hash; local installs and
the deployed Lambda both use it. `scripts/build_lambda.py` exports it to a
hashed requirements file when packaging the Lambda.

```sh
uv add <package>          # add a dependency (and lock it)
uv lock --upgrade         # move everything to the latest versions
uv lock --upgrade-package <package>
```

Commit `uv.lock` along with `pyproject.toml`: the build uses `--frozen`, so it
fails if they disagree rather than locking anew.

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
`ContentAPI`. Locally (see the [README](../README.md)), each is its own
container, and the stack's edge proxy routes between them the same way.

The admin page publishes a book review by uploading it to the
`spark.wiki.books` bucket as `<title>.md`, in the exact format a manual
upload would use, so `UpdateBookReview`'s S3 trigger enriches it and writes
it to DynamoDB. A custom cover for it is sent to the API first
(`POST /admin/book-reviews/<title>/cover`, a JPEG the browser has already
shrunk), which stores it under `covers/custom/` and returns its key for the
review's `cover_image` field. Photos go from the browser straight to `spark.wiki.photos`
(into `birds/` or `photos/`), through presigned PUT URLs (full-size photos
are bigger than API Gateway and Lambda accept in a request), and
`UpdatePhotoMetadata`'s S3 trigger processes each one, as it would one
uploaded in the console.

Locally, both go to the emulated buckets, whose triggers run the same
Lambdas, so they show up on the local site the same way.

### Admin login (one-time, AWS-side)

(Locally, the stack sets up its own: `admin` / `admin`.)

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
