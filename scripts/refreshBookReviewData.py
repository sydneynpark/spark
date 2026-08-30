#!/usr/bin/env python3
"""
Iterate over every book review in the spark.wiki.books S3 bucket (or a given
path/prefix within it) and invoke the UpdateBookReview Lambda for each one,
passing an S3-event-shaped payload where the object key is swapped in for the
real key.

Usage:
    python refreshBookReviewData.py                                   # whole bucket
    python refreshBookReviewData.py "Project Hail Mary.md"             # just this review
    python refreshBookReviewData.py s3://spark.wiki.books/Pet.md       # full s3:// URI

Credentials:
    The AWS access key and secret access key are read from local files
    (.accesskey and .secretaccesskey) and used for all S3 and Lambda calls.

"Private" Lambda just means it's your own function — you invoke it through the
normal AWS API with credentials that have lambda:InvokeFunction permission.
"""

import argparse
import sys

from s3_lambda_refresh import AWS_REGION, make_session, parse_prefix, refresh_bucket

# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────

BUCKET_NAME = "spark.wiki.books"
BUCKET_ARN = "arn:aws:s3:::spark.wiki.books"

# Lambda function name or full ARN
LAMBDA_FUNCTION_NAME = "UpdateBookReview"

# Invocation type:
#   "RequestResponse" — synchronous; waits for the function and surfaces errors.
#   "Event"           — async fire-and-forget; faster for large buckets, no result.
INVOCATION_TYPE = "RequestResponse"

# ─────────────────────────────────────────────────────────────────────────────


def should_process(key, obj):
    # Review files are the only thing UpdateBookReview processes -- this
    # notably excludes the cover images it writes into covers/ within this
    # same bucket (see lambda_function.py's own key.endswith('.md') check).
    return key.endswith(".md")


def main():
    parser = argparse.ArgumentParser(
        description="Refresh book review data by re-invoking the Lambda for every "
        "review in the bucket, optionally scoped to an S3 path/prefix."
    )
    parser.add_argument(
        "path",
        nargs="?",
        default=None,
        help="S3 prefix (or exact key) to limit processing to, e.g. "
        f"'Project Hail Mary.md' or 's3://{BUCKET_NAME}/Project Hail Mary.md'. "
        "Omit to process every review in the bucket.",
    )
    args = parser.parse_args()
    prefix = parse_prefix(args.path, BUCKET_NAME)

    if not LAMBDA_FUNCTION_NAME:
        sys.exit("Set LAMBDA_FUNCTION_NAME before running.")

    session = make_session(region=AWS_REGION)

    refresh_bucket(
        session,
        bucket_name=BUCKET_NAME,
        bucket_arn=BUCKET_ARN,
        region=AWS_REGION,
        lambda_function_name=LAMBDA_FUNCTION_NAME,
        invocation_type=INVOCATION_TYPE,
        prefix=prefix,
        should_process=should_process,
    )


if __name__ == "__main__":
    main()
