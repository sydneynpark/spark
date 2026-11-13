#!/usr/bin/env python3
"""
Invoke the UpdateBlogPostMetadata Lambda for every blog post in the
spark.wiki.blog S3 bucket (or a given path/prefix within it), passing an
S3-event-shaped payload where the object key is swapped in for the real key,
so it (re)writes each post's item in the spark.wiki.posts table -- e.g. to
fill the table the first time, or after changing what it stores.

Usage, from the repo root -- uv installs scripts/requirements.txt to run it
with, as the Refresh blog posts workflow does:
    uv run --no-project --with-requirements scripts/requirements.txt scripts/refreshBlogPosts.py [path]

    path:
    (none)                                 # every post
    2026/05/                               # just this prefix
    s3://spark.wiki.blog/2026/05/          # full s3:// URI

Credentials:
    See s3_lambda_refresh.py.
"""

import argparse
import sys

from s3_lambda_refresh import AWS_REGION, make_session, parse_prefix, refresh_bucket

BUCKET_NAME = "spark.wiki.blog"
BUCKET_ARN = "arn:aws:s3:::spark.wiki.blog"

# The admin page's drafts, which aren't posts (backend/src/utils/draft_util.py).
DRAFTS_PREFIX = "drafts/"

LAMBDA_FUNCTION_NAME = "UpdateBlogPostMetadata"

# Synchronous, so failures are reported.
INVOCATION_TYPE = "RequestResponse"


def should_process(key, obj):
    return key.endswith(".md") and not key.startswith(DRAFTS_PREFIX)


def main():
    parser = argparse.ArgumentParser(
        description="Refresh the posts table by re-invoking the Lambda for every "
        "post in the bucket, optionally scoped to an S3 path/prefix."
    )
    parser.add_argument(
        "path",
        nargs="?",
        default=None,
        help="S3 prefix to limit processing to, e.g. '2026/05/' or "
        f"'s3://{BUCKET_NAME}/2026/05/'. Omit to process every post.",
    )
    args = parser.parse_args()
    prefix = parse_prefix(args.path, BUCKET_NAME)

    session = make_session(region=AWS_REGION)

    _, _, failed = refresh_bucket(
        session,
        bucket_name=BUCKET_NAME,
        bucket_arn=BUCKET_ARN,
        region=AWS_REGION,
        lambda_function_name=LAMBDA_FUNCTION_NAME,
        invocation_type=INVOCATION_TYPE,
        prefix=prefix,
        should_process=should_process,
    )

    # Fails the workflow run that ran this (.github/workflows/refresh-*.yml),
    # so failures aren't missed.
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
