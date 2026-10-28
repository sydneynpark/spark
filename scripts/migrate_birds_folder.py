#!/usr/bin/env python3
"""
One-off: moves the bird photos in spark.wiki.photos from the bucket's root
into birds/, now that the bucket holds both birds/ and photos/ (photos that
aren't of birds). archive/ is left where it is.

    python scripts/migrate_birds_folder.py copy      # copy each into birds/
    python scripts/migrate_birds_folder.py cleanup   # then remove the old ones

Add --dry-run to either to see what it would do.

Run it as an administrator (your `aws login` session, or AWS_PROFILE): the
deploy role can't write content. Deploy the birds/ + photos/ code first, since
copy relies on it -- each copy fires the bucket's trigger, and
UpdatePhotoMetadata processes it as it would an upload, making its table items
and thumbnail. Once those are done (the Birds page shows every photo twice
until cleanup), cleanup deletes each old photo, along with its table items
and thumbnail -- but only those whose copy has its thumbnail, so nothing is
removed before its copy has been processed. What it skips, it lists. Both are
safe to re-run.

Credentials: boto3's default chain (see s3_lambda_refresh.py).
"""

import argparse
import sys

import boto3
from boto3.dynamodb.conditions import Key

PHOTOS_BUCKET = "spark.wiki.photos"
THUMBNAILS_BUCKET = "spark.wiki.thumbnails"
BIRDS_TABLE = "spark.wiki.photos"

BIRDS_PREFIX = "birds/"
# Everything else at the root that stays put: the other collection, and
# archived photos (which the site doesn't show).
KEEP_PREFIXES = ("birds/", "photos/", "archive/")


def list_keys(s3, bucket, prefix=""):
    keys = []
    for page in s3.get_paginator("list_objects_v2").paginate(Bucket=bucket, Prefix=prefix):
        keys.extend(obj["Key"] for obj in page.get("Contents", []))
    return keys


def old_keys(s3):
    """The bird photos (and folder placeholders) still at the root."""
    return [key for key in list_keys(s3, PHOTOS_BUCKET) if not key.startswith(KEEP_PREFIXES)]


def copy(s3, dry_run):
    already = set(list_keys(s3, PHOTOS_BUCKET, BIRDS_PREFIX))
    keys = old_keys(s3)
    copied = 0
    for key in keys:
        new_key = BIRDS_PREFIX + key
        if new_key in already:
            continue
        print(f"copy {key} -> {new_key}")
        if not dry_run:
            # One request, so one event: up to 5 GB, far more than any photo.
            s3.copy_object(
                Bucket=PHOTOS_BUCKET,
                Key=new_key,
                CopySource={"Bucket": PHOTOS_BUCKET, "Key": key},
            )
        copied += 1
    print(f"\n{len(keys)} at the root; {'would copy' if dry_run else 'copied'} {copied}, "
          f"{len(keys) - copied} already in {BIRDS_PREFIX}.")


def cleanup(s3, table, dry_run):
    copies = set(list_keys(s3, PHOTOS_BUCKET, BIRDS_PREFIX))
    thumbnails = set(list_keys(s3, THUMBNAILS_BUCKET, "thumbnail/" + BIRDS_PREFIX))
    removed, skipped = 0, []
    for key in old_keys(s3):
        new_key = BIRDS_PREFIX + key
        is_folder = key.endswith("/")
        if new_key not in copies:
            skipped.append((key, f"no copy at {new_key}"))
            continue
        if not is_folder and f"thumbnail/{new_key}" not in thumbnails:
            skipped.append((key, "its copy has no thumbnail yet (not processed, or failed to)"))
            continue

        print(f"remove {key}")
        if not is_folder:
            s3_uri = f"s3://{PHOTOS_BUCKET}/{key}"
            items = table.query(KeyConditionExpression=Key("s3_uri").eq(s3_uri))["Items"]
            for item in items:
                print(f"  table item: {item.get('species')}")
                if not dry_run:
                    table.delete_item(Key={"s3_uri": item["s3_uri"], "species": item["species"]})
            print(f"  thumbnail/{key}")
            if not dry_run:
                s3.delete_object(Bucket=THUMBNAILS_BUCKET, Key=f"thumbnail/{key}")
        # Last, so a failure part way leaves it to try again.
        if not dry_run:
            s3.delete_object(Bucket=PHOTOS_BUCKET, Key=key)
        removed += 1

    print(f"\n{'Would remove' if dry_run else 'Removed'} {removed}; skipped {len(skipped)}.")
    for key, reason in skipped:
        print(f"  skipped {key}: {reason}")
    return not skipped


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0].strip())
    parser.add_argument("step", choices=["copy", "cleanup"])
    parser.add_argument("--dry-run", action="store_true", help="Only print what it would do.")
    args = parser.parse_args()

    s3 = boto3.client("s3")
    if args.step == "copy":
        copy(s3, args.dry_run)
    elif not cleanup(s3, boto3.resource("dynamodb").Table(BIRDS_TABLE), args.dry_run):
        sys.exit(1)


if __name__ == "__main__":
    main()
