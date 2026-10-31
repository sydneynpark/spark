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
python -m unittest discover -s test
```

Or, in the local stack (see the [README](../README.md)):
`./dev compose exec -w /repo/backend admin-api python -m unittest discover -s test`.

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
`ContentAPI`. Locally (see the [README](../README.md)), each is its own
container, and the stack's edge proxy routes between them the same way.

The admin page publishes a book review by uploading it to the
`spark.wiki.books` bucket as `<title>.md`, in the exact format a manual
upload would use, so `UpdateBookReview`'s S3 trigger enriches it and writes
it to DynamoDB. Photos go from the browser straight to `spark.wiki.photos`
(into `birds/` or `photos/`), through presigned PUT URLs (full-size photos
are bigger than API Gateway and Lambda accept in a request), and
`UpdatePhotoMetadata`'s S3 trigger processes each one, as it would one
uploaded in the console.

Locally, both go to the emulated buckets, whose triggers run the same
Lambdas, so they show up on the local site the same way.

### Blog post drafts

The admin page's blog editor saves drafts in the `spark.wiki.blog` bucket,
under `drafts/<id>/`, which the public API skips (and ContentAPI's role
can't read): the draft's markdown, `draft.md`, in the same frontmatter
format as a post, and the photos uploaded to it, as
`drafts/<id>/birds/<photo>.jpg` or `drafts/<id>/photos/<photo>.jpg`. They
go there, rather than to `spark.wiki.photos`, so that they don't appear on
the site before the post does (see `src/utils/draft_util.py`).

Publishing a draft copies its photos into `spark.wiki.photos`, at
`birds/` or `photos/` + the post's `YYYY/MM/DD/`, where
`UpdatePhotoMetadata` processes them as any other upload; writes the post
to `YYYY/MM/DD/<slug>.md` (its title, `date`, `written`, `tags`, `preview`,
and thumbnail `photo` in its frontmatter), with its embeds pointed at the
published photos; and deletes the draft. A post's `date` is the one it's
shown, foldered, and its photos filed under; `written`, optional, is when it
was written, for a post about something past, and is the same as `date` if
not set. The blog can be sorted by either. `tags` is a list (or a string of
them separated by commas), matched regardless of case; the blog can be
filtered by any number of them (showing the posts with all of them), and the
editor suggests those already in use. It refuses, before writing anything, to
overwrite a post or a different photo, or to give two posts the same URL.

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
