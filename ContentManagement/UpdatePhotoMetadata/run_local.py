"""
Run the lambda against the local stand-in for the photos bucket that
backend/run_local.py serves -- sample-data/photos/originals -- as if each
photo had just been uploaded there, so they show up in the locally-run
gallery.

Usage:
    python run_local.py                   # photos not in photos.json yet
    python run_local.py 2026/10/08/       # ...just in this folder (any key prefix)
    python run_local.py --all             # every photo, even ones already in it

Photos are skipped once they're in photos.json by default, since the sample
ones are committed, along with their thumbnails -- which come out
byte-for-byte different (if no different to look at) when regenerated.
"""

import argparse
import json
import os
import sys
import urllib.parse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# lambda_function makes its (real) AWS clients on import, and DynamoDB's
# needs a region -- they're swapped out below before anything calls them.
os.environ.setdefault('AWS_DEFAULT_REGION', 'us-east-1')

import aws_util
import lambda_function

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.join(THIS_DIR, '..', '..')
PHOTOS_DATA_DIR = os.path.join(REPO_ROOT, 'sample-data', 'photos')
PHOTOS_DIR = os.path.join(PHOTOS_DATA_DIR, 'originals')
THUMBNAILS_DIR = os.path.join(PHOTOS_DATA_DIR, 'thumbnails')
PHOTOS_TABLE = os.path.join(PHOTOS_DATA_DIR, 'photos.json')
BUCKET = 'spark.wiki.photos'
THUMBNAILS_BUCKET = 'spark.wiki.thumbnails'
THUMBNAIL_PREFIX = 'thumbnail/'

PHOTO_EXTENSIONS = ('.jpg', '.jpeg')
# Like scripts/refreshPhotoMetadata.py: archived photos aren't processed.
ARCHIVE_PREFIX = 'archive/'


class _BytesBody:
    """Just enough of botocore's StreamingBody interface for
    lambda_handler's response['Body'].read() call."""

    def __init__(self, data):
        self._data = data

    def read(self):
        return self._data


def _load_table():
    with open(PHOTOS_TABLE, encoding='utf-8') as f:
        return json.load(f)


def _save_table(items):
    # Written whole and then swapped in, so the backend (which re-reads this
    # on every request) never sees it half-written.
    tmp_path = f'{PHOTOS_TABLE}.tmp'
    with open(tmp_path, 'w', encoding='utf-8') as f:
        json.dump(items, f, indent=2)
        f.write('\n')
    os.replace(tmp_path, PHOTOS_TABLE)


class LocalAWSUtil:
    """Stands in for aws_util.AWSUtil during a local run, using the files
    backend/run_local.py serves in place of the photos and thumbnails
    buckets, and sample-data/photos/photos.json in place of the
    spark.wiki.photos table."""

    def get_s3_object(self, bucket, key):
        with open(os.path.join(PHOTOS_DIR, *key.split('/')), 'rb') as f:
            return {'Body': _BytesBody(f.read())}

    def put_s3_object(self, bucket, key, body, content_type='image/jpeg'):
        if bucket != THUMBNAILS_BUCKET or not key.startswith(THUMBNAIL_PREFIX):
            raise ValueError(f'No local stand-in for s3://{bucket}/{key}')
        path = os.path.join(THUMBNAILS_DIR, *key[len(THUMBNAIL_PREFIX):].split('/'))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'wb') as f:
            f.write(body.read())

    def store_photo_metadata(self, s3_uri, taxonomies, date_captured=None):
        items = aws_util.photo_items(s3_uri, taxonomies, date_captured)
        table = _load_table()
        # Replace this photo's entries where the first of them was, so
        # reprocessing a photo doesn't reorder the file.
        first = next((i for i, item in enumerate(table) if item['s3_uri'] == s3_uri), len(table))
        kept = [item for item in table if item['s3_uri'] != s3_uri]
        kept[first:first] = items
        _save_table(kept)


def _upload_event(key):
    return {
        'Records': [{
            'eventName': 'ObjectCreated:Put',
            's3': {
                'bucket': {'name': BUCKET},
                'object': {'key': urllib.parse.quote_plus(key)},
            },
        }]
    }


def _photo_keys(prefix):
    keys = []
    for dirpath, _, filenames in os.walk(PHOTOS_DIR):
        for filename in filenames:
            if not filename.lower().endswith(PHOTO_EXTENSIONS):
                continue
            key = os.path.relpath(os.path.join(dirpath, filename), PHOTOS_DIR).replace(os.sep, '/')
            if key.startswith(prefix) and not key.startswith(ARCHIVE_PREFIX):
                keys.append(key)
    return sorted(keys)


def main():
    parser = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    parser.add_argument(
        'prefix',
        nargs='?',
        default='',
        help="Only process photos whose key starts with this, e.g. '2026/10/08/'.",
    )
    parser.add_argument(
        '--all',
        action='store_true',
        help='Also reprocess photos already in photos.json, e.g. after changing their keywords.',
    )
    args = parser.parse_args()
    prefix = args.prefix.replace('\\', '/').lstrip('/')

    lambda_function.aws = LocalAWSUtil()

    keys = _photo_keys(prefix)
    if not args.all:
        stored = {item['s3_uri'] for item in _load_table()}
        keys = [key for key in keys if f's3://{BUCKET}/{key}' not in stored]
    print(f'Found {len(keys)} photo(s) to process in {os.path.normpath(PHOTOS_DIR)}\n')

    failed = 0
    for key in keys:
        print(f'=== {key} ===')
        try:
            result = lambda_function.lambda_handler(_upload_event(key), None)
            print(f'  -> {result}\n')
        except Exception as e:
            failed += 1
            print(f'  -> FAILED: {e}\n')

    print(f'Done. {len(keys)} photo(s) processed -- {len(keys) - failed} succeeded, {failed} failed.')
    if failed:
        sys.exit(1)


if __name__ == '__main__':
    main()
