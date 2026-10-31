# Update Blog Post Metadata lambda

This lambda keeps the `spark.wiki.posts` DynamoDB table in step with the
`spark.wiki.blog` bucket: when a post (`YYYY/MM/DD/<post>.md`) is uploaded, it
writes the post's metadata -- title, slug, dates, tags, preview, thumbnail,
everything but its body -- as one item, keyed by its `s3_uri`; when a post is
deleted, it deletes the item. The API lists posts, and finds one by its slug
(the table's `slug-index`), from the table, rather than reading every post.
It's subscribed to the bucket's create and delete events, and skips the admin
page's drafts, under `drafts/`.

`src/post_util.py`, which reads a post's metadata, is a copy of
[backend/src/utils/post_util.py](../../backend/src/utils/post_util.py), which
the admin page publishes and previews posts with, so the table matches them.
Edit that one, then copy it here; a test fails while they differ.

To fill the table from the bucket -- the first time, or after changing what
it stores -- run the Refresh blog posts workflow, or
`scripts/refreshBlogPosts.py`.


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
python -m unittest test\test_lambda.py
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

Every push builds this Lambda and plans deploying it, for you to approve -- see [terraform/README.md](../../terraform/README.md).
