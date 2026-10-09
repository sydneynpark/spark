#!/usr/bin/env python3
"""
Shared helpers for the refresh*.py scripts: each one walks every object in an
S3 bucket (or a given path/prefix within it) and invokes a (private) Lambda
for each one, passing an S3-event-shaped payload where the object key is
swapped in for the real key.

Credentials:
    boto3's default credential chain: the deploy role's short-lived
    credentials in GitHub Actions, or locally, your `aws login` session (or
    whatever AWS_PROFILE points at).
"""

import json
import sys
from urllib.parse import quote

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

AWS_REGION = "us-east-1"


def make_session(region=AWS_REGION):
    return boto3.Session(region_name=region)


def build_event(bucket_name, bucket_arn, region, obj):
    """Build the S3-event payload for a single listed object.

    The object key is URL-encoded the same way as your sample (slashes -> %2F,
    spaces -> %20). size and eTag are populated from the listing so the event
    is accurate -- remove those two lines if you truly only want the key changed.
    """
    encoded_key = quote(obj["Key"], safe="")

    return {
        "Records": [
            {
                "eventVersion": "2.0",
                "eventSource": "aws:s3",
                "awsRegion": region,
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
                        "name": bucket_name,
                        "ownerIdentity": {"principalId": "EXAMPLE"},
                        "arn": bucket_arn,
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


def invoke(lambda_client, function_name, invocation_type, payload):
    resp = lambda_client.invoke(
        FunctionName=function_name,
        InvocationType=invocation_type,
        Payload=json.dumps(payload).encode("utf-8"),
    )

    if invocation_type == "Event":
        # Async: 202 Accepted, no body to read.
        return resp["StatusCode"] == 202, None

    function_error = resp.get("FunctionError")
    body = resp["Payload"].read().decode("utf-8")
    ok = resp["StatusCode"] == 200 and not function_error
    return ok, (function_error and body) or None


def parse_prefix(raw, bucket_name):
    """Normalize a user-supplied S3 path/prefix into a bucket-relative prefix.

    Accepts a bare prefix ("2024/vacation/") or a full s3:// URI
    ("s3://spark.wiki.photos/2024/vacation/"), and requires the URI's bucket
    (if given) to match bucket_name.
    """
    if raw is None:
        return ""

    if raw.startswith("s3://"):
        rest = raw[len("s3://"):]
        bucket, _, key = rest.partition("/")
        if bucket != bucket_name:
            sys.exit(f"Bucket in path ({bucket!r}) does not match bucket ({bucket_name!r}).")
        return key

    return raw.lstrip("/")


def refresh_bucket(session, *, bucket_name, bucket_arn, region, lambda_function_name,
                    invocation_type, prefix, should_process=lambda key, obj: True):
    """Paginate bucket_name (scoped to prefix), invoking lambda_function_name
    for every object should_process accepts, printing progress per object.

    Returns (total, succeeded, failed) counts.
    """
    s3 = session.client("s3")
    # Retries help when firing a lot of invocations in a row.
    lambda_client = session.client(
        "lambda", config=Config(retries={"max_attempts": 5, "mode": "standard"})
    )

    paginator = s3.get_paginator("list_objects_v2")

    total = succeeded = failed = 0

    if prefix:
        print(f"Restricting to prefix: {prefix!r}\n")

    for page in paginator.paginate(Bucket=bucket_name, Prefix=prefix):
        for obj in page.get("Contents", []):
            key = obj["Key"]

            # Skip "folder" placeholder keys if any exist.
            if key.endswith("/") and obj.get("Size", 0) == 0:
                continue

            if not should_process(key, obj):
                continue

            total += 1
            try:
                payload = build_event(bucket_name, bucket_arn, region, obj)
                ok, err = invoke(lambda_client, lambda_function_name, invocation_type, payload)
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

    return total, succeeded, failed
