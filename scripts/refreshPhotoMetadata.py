#!/usr/bin/env python3
"""
Iterate over every object in the photos buckets -- bird photos, and the
rest -- (or a given path/prefix within them) and invoke a (private) Lambda
for each one, passing an S3-event-shaped payload where the object key is
swapped in for the real key.

Usage:
    python refreshPhotoMetadata.py                              # both buckets
    python refreshPhotoMetadata.py 2024/vacation/                # this prefix, in both
    python refreshPhotoMetadata.py s3://spark.wiki.photos/2024/  # just this bucket's

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

# UpdatePhotoMetadata processes both.
BUCKET_NAMES = ["spark.wiki.photos", "spark.wiki.normal-photos"]

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
        help="S3 prefix to limit processing to, e.g. '2024/vacation/' (in every "
        f"bucket) or 's3://{BUCKET_NAMES[0]}/2024/vacation/' (in just that one). "
        "Omit to process every bucket.",
    )
    args = parser.parse_args()

    bucket_names = BUCKET_NAMES
    if args.path and args.path.startswith("s3://"):
        bucket = args.path[len("s3://"):].partition("/")[0]
        if bucket not in BUCKET_NAMES:
            sys.exit(f"Not a photos bucket: {bucket!r} (expected one of {BUCKET_NAMES}).")
        bucket_names = [bucket]

    if not LAMBDA_FUNCTION_NAME:
        sys.exit("Set LAMBDA_FUNCTION_NAME before running.")

    session = make_session(region=AWS_REGION)

    failed = 0
    for bucket_name in bucket_names:
        print(f"\n== {bucket_name} ==")
        _, _, bucket_failed = refresh_bucket(
            session,
            bucket_name=bucket_name,
            bucket_arn=f"arn:aws:s3:::{bucket_name}",
            region=AWS_REGION,
            lambda_function_name=LAMBDA_FUNCTION_NAME,
            invocation_type=INVOCATION_TYPE,
            prefix=parse_prefix(args.path, bucket_name),
            should_process=should_process,
        )
        failed += bucket_failed

    # Fails the workflow run that ran this (.github/workflows/refresh-*.yml),
    # so failures aren't missed.
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
