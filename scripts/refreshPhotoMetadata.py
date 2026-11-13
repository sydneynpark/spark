#!/usr/bin/env python3
"""
Iterate over every object in an S3 bucket (or a given path/prefix within it)
and invoke a (private) Lambda for each one, passing an S3-event-shaped payload
where the object key is swapped in for the real key.

Usage, from the repo root -- uv installs scripts/requirements.txt to run it
with, as the Refresh photo metadata workflow does:
    uv run --no-project --with-requirements scripts/requirements.txt scripts/refreshPhotoMetadata.py [path]

    path:
    (none)                                 # whole bucket
    photos/2019/                           # just this prefix
    s3://spark.wiki.photos/photos/2019/    # full s3:// URI

Credentials:
    See s3_lambda_refresh.py.

"Private" Lambda just means it's your own function — you invoke it through the
normal AWS API with credentials that have lambda:InvokeFunction permission.
"""

import argparse
import sys
import uuid
from urllib.parse import quote

from s3_lambda_refresh import AWS_REGION, make_session, parse_prefix, refresh_bucket

# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────

BUCKET_NAME = "spark.wiki.photos"
BUCKET_ARN = "arn:aws:s3:::spark.wiki.photos"

# Serves the bucket above, and under /thumbnail/, the thumbnails the Lambda
# makes of it.
PHOTOS_DISTRIBUTION_ID = "E36I1WVQPNH4HH"

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
        help="S3 prefix to limit processing to, e.g. 'photos/2019/' or "
        f"'s3://{BUCKET_NAME}/photos/2019/'. Omit to process the whole bucket.",
    )
    args = parser.parse_args()
    prefix = parse_prefix(args.path, BUCKET_NAME)

    if not LAMBDA_FUNCTION_NAME:
        sys.exit("Set LAMBDA_FUNCTION_NAME before running.")

    session = make_session(region=AWS_REGION)

    _, succeeded, failed = refresh_bucket(
        session,
        bucket_name=BUCKET_NAME,
        bucket_arn=BUCKET_ARN,
        region=AWS_REGION,
        lambda_function_name=LAMBDA_FUNCTION_NAME,
        invocation_type=INVOCATION_TYPE,
        prefix=prefix,
        should_process=should_process,
    )

    # Reprocessing rewrites thumbnails in place (thumbnail/<key>), so without
    # this CloudFront keeps serving the old ones until their TTL expires. Only
    # the thumbnails under the prefix changed: the photos themselves don't.
    # INVOCATION_TYPE is synchronous, so every thumbnail is rewritten by now.
    if succeeded:
        path = f"/thumbnail/{quote(prefix, safe='/')}*"
        print(f"\nCreating CloudFront invalidation for {path} on {PHOTOS_DISTRIBUTION_ID} ...")
        resp = session.client("cloudfront").create_invalidation(
            DistributionId=PHOTOS_DISTRIBUTION_ID,
            InvalidationBatch={
                "Paths": {"Quantity": 1, "Items": [path]},
                "CallerReference": str(uuid.uuid4()),
            },
        )
        print(f"  Invalidation {resp['Invalidation']['Id']} created.")

    # Fails the workflow run that ran this (.github/workflows/refresh-*.yml),
    # so failures aren't missed.
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
