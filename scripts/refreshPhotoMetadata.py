#!/usr/bin/env python3
"""
Iterate over every object in an S3 bucket (or a given path/prefix within it)
and invoke a (private) Lambda for each one, passing an S3-event-shaped payload
where the object key is swapped in for the real key.

Usage:
    python refreshPhotoMetadata.py                              # whole bucket
    python refreshPhotoMetadata.py 2024/vacation/                # just this prefix
    python refreshPhotoMetadata.py s3://spark.wiki.photos/2024/  # full s3:// URI

Credentials:
    See s3_lambda_refresh.py.

"Private" Lambda just means it's your own function — you invoke it through the
normal AWS API with credentials that have lambda:InvokeFunction permission.
"""

import argparse
import sys

from s3_lambda_refresh import AWS_REGION, make_session, parse_prefix, refresh_bucket

# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────

BUCKET_NAME = "spark.wiki.photos"
BUCKET_ARN = "arn:aws:s3:::spark.wiki.photos"

# Objects under this prefix are archived and shouldn't be (re)processed.
ARCHIVE_PREFIX = "archive/"

# Lambda function name or full ARN
LAMBDA_FUNCTION_NAME = "UpdatePhotoMetadata"  # e.g. "process-photo" or the function's ARN

# Invocation type:
#   "RequestResponse" — synchronous; waits for the function and surfaces errors.
#   "Event"           — async fire-and-forget; faster for large buckets, no result.
INVOCATION_TYPE = "RequestResponse"

# ─────────────────────────────────────────────────────────────────────────────


def should_process(key, obj):
    # Skip archived photos.
    return not key.startswith(ARCHIVE_PREFIX)


def main():
    parser = argparse.ArgumentParser(
        description="Refresh photo metadata by re-invoking the Lambda for every "
        "object in the bucket, optionally scoped to an S3 path/prefix."
    )
    parser.add_argument(
        "path",
        nargs="?",
        default=None,
        help="S3 prefix to limit processing to, e.g. '2024/vacation/' or "
        f"'s3://{BUCKET_NAME}/2024/vacation/'. Omit to process the whole bucket.",
    )
    args = parser.parse_args()
    prefix = parse_prefix(args.path, BUCKET_NAME)

    if not LAMBDA_FUNCTION_NAME:
        sys.exit("Set LAMBDA_FUNCTION_NAME before running.")

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
