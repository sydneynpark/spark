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

## Admin photo uploads setup (one-time, AWS-side)

The admin page's photo uploader (`/admin/photos/folders` and
`/admin/photos/upload-url`, in `src/handlers/admin.py`) browses the
`spark.wiki.photos` bucket and creates `YYYY/MM/DD/` folders in it, but
photos themselves go from the browser straight to S3 through presigned PUT
URLs -- full-size photos are bigger than API Gateway and Lambda accept in a
request. `UpdatePhotoMetadata`'s existing S3 trigger processes each upload,
exactly as it would one made in the console. Neither the bucket nor
`ContentAPI`'s role is managed by Terraform yet, so:

1. Grant the `ContentAPI` lambda's execution role
   (`ContentAPI-role-rab0br82`) `s3:ListBucket` on
   `arn:aws:s3:::spark.wiki.photos`, and `s3:PutObject` on
   `arn:aws:s3:::spark.wiki.photos/*` -- creating folders is a `PutObject`
   too, and presigned URLs only carry the permissions of the role that
   signed them. (If the bucket's default encryption is SSE-KMS with your own
   key, the role also needs `kms:GenerateDataKey` on it.)
2. Allow the site to upload to the bucket cross-origin. `put-bucket-cors`
   replaces the bucket's whole CORS configuration, so first check it has
   none (`aws s3api get-bucket-cors --bucket spark.wiki.photos`), or merge
   this rule into what's there:

   ```json
   {
     "CORSRules": [
       {
         "AllowedOrigins": ["https://spark.wiki", "https://www.spark.wiki"],
         "AllowedMethods": ["PUT"],
         "AllowedHeaders": ["Content-Type"],
         "MaxAgeSeconds": 3000
       }
     ]
   }
   ```

   ```
   aws s3api put-bucket-cors --bucket spark.wiki.photos --cors-configuration file://cors.json
   ```

   Without it, every upload fails with "network or CORS error".
3. If `ContentAPI` is wired into API Gateway as explicit per-path resources
   rather than a `{proxy+}` catch-all, add `/admin/photos/folders` (`GET`,
   `POST`) and `/admin/photos/upload-url` (`POST`).

Locally, the uploader treats `sample-data/photos/originals` (at the repo
root) as the bucket, and uploads land there. Nothing processes them automatically: run
`ContentManagement/UpdatePhotoMetadata/run_local.py` (see its README) to add
them to the local gallery.
