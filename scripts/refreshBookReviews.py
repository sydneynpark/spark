#!/usr/bin/env python3
"""
Iterate over every object in an S3 bucket and invoke a (private) Lambda for
each one, passing an S3-event-shaped payload where the object key is swapped in
for the real key.

Credentials:
    The AWS access key and secret access key are read from local files
    (.accesskey and .secretaccesskey) and used for all S3 and Lambda calls.

"Private" Lambda just means it's your own function — you invoke it through the
normal AWS API with credentials that have lambda:InvokeFunction permission.
"""

import json
import os
import sys
from urllib.parse import quote

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────

BUCKET_NAME = "spark.wiki.books"
BUCKET_ARN = "arn:aws:s3:::spark.wiki.books"

# Cover images the lambda itself writes back into this bucket -- reprocessing
# them would just have the lambda ignore them as non-markdown (see its
# key.endswith('.md') check), so skip them here instead of wasting invocations.
COVERS_PREFIX = "covers/"

AWS_REGION = "us-east-1"

# Lambda function name or full ARN
LAMBDA_FUNCTION_NAME = "UpdateBookReview"  # e.g. "process-photo" or the function's ARN

# Invocation type:
#   "RequestResponse" — synchronous; waits for the function and surfaces errors.
#   "Event"           — async fire-and-forget; faster for large buckets, no result.
INVOCATION_TYPE = "RequestResponse"

# Local files holding the AWS credentials.
ACCESS_KEY_FILE = ".accesskey"
SECRET_KEY_FILE = ".secretaccesskey"

# ─────────────────────────────────────────────────────────────────────────────


def read_secret(path):
    """Read a single-line secret/value from a local file."""
    if not os.path.exists(path):
        sys.exit(f"Required file not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        value = f.read().strip()  # drops trailing newline / surrounding whitespace
    if not value:
        sys.exit(f"File is empty: {path}")
    return value


def make_session():
    return boto3.Session(
        aws_access_key_id=read_secret(ACCESS_KEY_FILE),
        aws_secret_access_key=read_secret(SECRET_KEY_FILE),
        region_name=AWS_REGION,
    )


def build_event(obj):
    """Build the S3-event payload for a single listed object.

    The object key is URL-encoded the same way as your sample (slashes -> %2F,
    spaces -> %20). size and eTag are populated from the listing so the event
    is accurate — remove those two lines if you truly only want the key changed.
    """
    encoded_key = quote(obj["Key"], safe="")

    return {
        "Records": [
            {
                "eventVersion": "2.0",
                "eventSource": "aws:s3",
                "awsRegion": AWS_REGION,
                "eventTime": "1970-01-01T00:00:00.000Z",
                "eventName": "ObjectCreated:Put",
                "userIdentity": {"principalId": "EXAMPLE"},
                "requestParameters": {"sourceIPAddress": "127.0.0.1"},
                "responseElements": {
                    "x-amz-request-id": "EXAMPLE123456789",
                    "x-amz-id-2": "EXAMPLE123/5678abcdefghijklambdaisawesome/mnopqrstuvwxyzABCDEFGH",
                },
                "s3": {
                    "s3SchemaVersion": "1.0",
                    "configurationId": "testConfigRule",
                    "bucket": {
                        "name": BUCKET_NAME,
                        "ownerIdentity": {"principalId": "EXAMPLE"},
                        "arn": BUCKET_ARN,
                    },
                    "object": {
                        "key": encoded_key,
                        "size": obj.get("Size", 0),                       # from listing
                        "eTag": obj.get("ETag", "").strip('"'),           # from listing
                        "sequencer": "0A1B2C3D4E5F678901",
                    },
                },
            }
        ]
    }


def invoke(lambda_client, payload):
    resp = lambda_client.invoke(
        FunctionName=LAMBDA_FUNCTION_NAME,
        InvocationType=INVOCATION_TYPE,
        Payload=json.dumps(payload).encode("utf-8"),
    )

    if INVOCATION_TYPE == "Event":
        # Async: 202 Accepted, no body to read.
        return resp["StatusCode"] == 202, None

    function_error = resp.get("FunctionError")
    body = resp["Payload"].read().decode("utf-8")
    ok = resp["StatusCode"] == 200 and not function_error
    return ok, (function_error and body) or None


def main():
    if not LAMBDA_FUNCTION_NAME:
        sys.exit("Set LAMBDA_FUNCTION_NAME before running.")

    session = make_session()
    s3 = session.client("s3")
    # Retries help when firing a lot of invocations in a row.
    lambda_client = session.client(
        "lambda", config=Config(retries={"max_attempts": 5, "mode": "standard"})
    )

    paginator = s3.get_paginator("list_objects_v2")

    total = succeeded = failed = 0

    for page in paginator.paginate(Bucket=BUCKET_NAME):
        for obj in page.get("Contents", []):
            key = obj["Key"]

            # Skip "folder" placeholder keys if any exist.
            if key.endswith("/") and obj.get("Size", 0) == 0:
                continue

            # Skip cover images the lambda wrote back into the bucket.
            if key.startswith(COVERS_PREFIX):
                continue

            # Skip anything that isn't a review file (the lambda would just
            # ignore it, but there's no point paying for the invocation).
            if not key.endswith(".md"):
                continue

            total += 1
            try:
                ok, err = invoke(lambda_client, build_event(obj))
                if ok:
                    succeeded += 1
                    print(f"[ok]   {key}")
                else:
                    failed += 1
                    print(f"[FAIL] {key}  ->  {err}")
            except ClientError as e:
                failed += 1
                print(f"[FAIL] {key}  ->  {e}")

    print(
        f"\nDone. {total} object(s) processed — "
        f"{succeeded} succeeded, {failed} failed."
    )


if __name__ == "__main__":
    main()
