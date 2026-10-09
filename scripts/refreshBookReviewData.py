#!/usr/bin/env python3
"""
Iterate over every book review in the spark.wiki.books S3 bucket (or a given
path/prefix within it) and invoke the UpdateBookReview Lambda for each one,
passing an S3-event-shaped payload where the object key is swapped in for the
real key. Then invalidates the bucket's CloudFront distribution, so rewritten
covers are served right away.

Usage:
    python refreshBookReviewData.py                                   # whole bucket
    python refreshBookReviewData.py "Project Hail Mary.md"             # just this review
    python refreshBookReviewData.py s3://spark.wiki.books/Pet.md       # full s3:// URI
    python refreshBookReviewData.py --missing-only                    # only reviews missing a cover/synopsis

Credentials:
    See s3_lambda_refresh.py.

"Private" Lambda just means it's your own function — you invoke it through the
normal AWS API with credentials that have lambda:InvokeFunction permission.
"""

import argparse
import sys
import uuid

from s3_lambda_refresh import AWS_REGION, make_session, parse_prefix, refresh_bucket

# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────

BUCKET_NAME = "spark.wiki.books"
BUCKET_ARN = "arn:aws:s3:::spark.wiki.books"

# The DynamoDB table UpdateBookReview writes review metadata to -- happens to
# share its name with the S3 bucket above, but it's a separate resource.
TABLE_NAME = "spark.wiki.books"

# Serves the bucket above (reviews and covers/).
BOOKS_DISTRIBUTION_ID = "E2Y8FRIT378S9Y"

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


def find_keys_missing_data(session, table_name=TABLE_NAME):
    """Scan the DynamoDB table for reviews missing a cover and/or synopsis.

    cover_key/synopsis are only written when Google Books/Gemini enrichment
    succeeds (see book_review.py's to_item) -- a transient failure (e.g. a
    Google Books 503) leaves them off the item entirely, with no other
    record that enrichment was attempted. Returns the S3 keys to reprocess,
    read from each item's s3_uri (always set by to_item) rather than
    reconstructed from title + '.md' -- title comes from the review's own
    frontmatter and isn't guaranteed to match its actual filename.
    """
    table = session.resource("dynamodb").Table(table_name)
    uri_prefix = f"s3://{BUCKET_NAME}/"

    keys = set()
    scan_kwargs = {}
    while True:
        response = table.scan(**scan_kwargs)
        for item in response.get("Items", []):
            if "cover_key" in item and "synopsis" in item:
                continue
            keys.add(item["s3_uri"][len(uri_prefix):])

        if "LastEvaluatedKey" not in response:
            break
        scan_kwargs["ExclusiveStartKey"] = response["LastEvaluatedKey"]

    return keys


def main():
    parser = argparse.ArgumentParser(
        description="Refresh book review data by re-invoking the Lambda for every "
        "review in the bucket, optionally scoped to an S3 path/prefix."
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "path",
        nargs="?",
        default=None,
        help="S3 prefix (or exact key) to limit processing to, e.g. "
        f"'Project Hail Mary.md' or 's3://{BUCKET_NAME}/Project Hail Mary.md'. "
        "Omit to process every review in the bucket.",
    )
    group.add_argument(
        "--missing-only",
        action="store_true",
        help="Only reprocess reviews currently missing a cover and/or synopsis in "
        "DynamoDB, e.g. to retry ones that hit a flaky Google Books API on the "
        "last run.",
    )
    args = parser.parse_args()

    if not LAMBDA_FUNCTION_NAME:
        sys.exit("Set LAMBDA_FUNCTION_NAME before running.")

    session = make_session(region=AWS_REGION)

    if args.missing_only:
        missing_keys = find_keys_missing_data(session)
        if not missing_keys:
            print("No reviews are missing a cover or synopsis -- nothing to do.")
            return
        print(f"Found {len(missing_keys)} review(s) missing a cover and/or synopsis.\n")
        process = lambda key, obj: key in missing_keys
    else:
        process = should_process

    prefix = parse_prefix(args.path, BUCKET_NAME)

    _, succeeded, failed = refresh_bucket(
        session,
        bucket_name=BUCKET_NAME,
        bucket_arn=BUCKET_ARN,
        region=AWS_REGION,
        lambda_function_name=LAMBDA_FUNCTION_NAME,
        invocation_type=INVOCATION_TYPE,
        prefix=prefix,
        should_process=process,
    )

    # Reprocessing rewrites covers in place (covers/<title>.jpg), so without
    # this CloudFront keeps serving the old image until its TTL expires.
    # INVOCATION_TYPE is synchronous, so every cover has been rewritten by now.
    if succeeded:
        print(f"\nCreating CloudFront invalidation for /* on {BOOKS_DISTRIBUTION_ID} ...")
        resp = session.client("cloudfront").create_invalidation(
            DistributionId=BOOKS_DISTRIBUTION_ID,
            InvalidationBatch={
                "Paths": {"Quantity": 1, "Items": ["/*"]},
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
