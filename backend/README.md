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

Pushing to `master` deploys this Lambda -- see [terraform/README.md](../terraform/README.md).

## Admin auth setup (one-time, AWS-side)

The admin area (`/admin/login`, `/admin/session`, `/admin/book-reviews`,
implemented in `src/handlers/admin.py` + `src/utils/auth_util.py`) reads its
credentials and signing secret from AWS Systems Manager Parameter Store --
the same mechanism `ContentManagement/UpdateBookReview` already uses for its
Google Books/Gemini API keys. There's no new Lambda, DynamoDB table, or CORS
change involved.

1. Run `python scripts/generate_admin_credentials.py` from the repo root (it
   imports the same `hash_password` the backend verifies logins with, so the
   hash format can't drift out of sync) and follow the printed
   `aws ssm put-parameter` commands to create three **SecureString**
   parameters in the same region as the `ContentAPI` lambda:
   * `AdminUsername`
   * `AdminPasswordHash`
   * `AdminTokenSecret`
2. Grant the `ContentAPI` lambda's execution role `ssm:GetParameter` +
   `kms:Decrypt` on those three parameter ARNs (mirroring the permissions
   already granted to `UpdateBookReview`'s role for its two parameters).
3. Grant that same role `s3:PutObject` on the `spark.wiki.books` bucket --
   `ContentAPI` currently only reads that bucket's DynamoDB table, it has no
   S3 write access there yet. Uploading a review through the admin form
   writes a `<title>.md` object to this bucket in the exact format a manual
   upload would, so `UpdateBookReview`'s existing S3 trigger picks it up,
   enriches it (cover/genres/synopsis), and writes it to DynamoDB -- no
   changes needed to `UpdateBookReview` itself.
4. If `ContentAPI` is wired into API Gateway as a catch-all proxy integration
   (`{proxy+}` + `ANY`, the usual `serverless-wsgi` setup), the new `/admin/*`
   routes need no API Gateway changes. If it's wired as explicit per-path
   resources instead, add resources for `/admin/login`, `/admin/session`, and
   `/admin/book-reviews`.

To change the admin password later, re-run the generator script and update
just the `AdminPasswordHash` parameter.
