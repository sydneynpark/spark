"""
Sets up the AWS emulator as terraform/ sets up AWS -- the content buckets
and tables, the admin login's parameters, and the buckets' triggers -- then
uploads sample-data/ into the buckets, for the triggers to process as they
would content uploaded in production. Book reviews snapshotted from the live
site (./dev snapshot-books) are loaded as they are there instead, already
processed.

Runs on every ./dev up, but leaves the emulator alone once it's set up. It
keeps nothing once it stops, though, so restarting it (./dev reseed) starts
over from sample-data/.
"""

import json
import mimetypes
import os
import secrets
import sys
from decimal import Decimal
from pathlib import Path
from urllib.parse import urlparse

import boto3
from botocore.exceptions import ClientError

REPO = Path(__file__).resolve().parent.parent
SAMPLE_DATA = REPO / 'sample-data'

sys.path.insert(0, str(REPO / 'backend' / 'src'))
from utils.auth_util import hash_password  # noqa: E402

# terraform/content_storage.tf
BUCKETS = {
    'blog': 'spark.wiki.blog',
    'books': 'spark.wiki.books',
    'photos': 'spark.wiki.photos',
    'thumbnails': 'spark.wiki.thumbnails',
}

# The buckets CloudFront serves (terraform/site_cdn.tf). The edge proxy
# stands in for it, reading them anonymously.
CDN_BUCKETS = ['books', 'photos', 'thumbnails']

# The events each bucket triggers its Lambda on (content_triggers, in
# terraform/content_lambdas.tf). They go to a queue, rather than straight to
# the Lambda, for devstack/lambda_trigger.py to run it.
TRIGGER_EVENTS = {
    'blog': ['s3:ObjectCreated:*'],
    'books': ['s3:ObjectCreated:*', 's3:ObjectRemoved:*'],
    'photos': ['s3:ObjectCreated:*', 's3:ObjectRemoved:*'],
}
EVENTS_QUEUE = 'content-events'

# What sample-data/ stands in for (see its README.md).
SAMPLE_CONTENT = {
    'blog': SAMPLE_DATA / 'posts',
    'books': SAMPLE_DATA / 'books' / 'markdown',
    'photos': SAMPLE_DATA / 'photos' / 'originals',
}

# The live site's processed book reviews (see devstack/snapshot_live_books.py):
# their table items, and their covers, under the keys the items give them.
BOOKS_DIR = SAMPLE_DATA / 'books'
BOOKS_TABLE_DIR = BOOKS_DIR / 'table'
BOOKS_COVERS_DIR = BOOKS_DIR / 'covers'

# A login only this local stack accepts.
ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = 'admin'

s3 = boto3.client('s3')
dynamodb = boto3.client('dynamodb')
ssm = boto3.client('ssm')
sqs = boto3.client('sqs')


def already_seeded():
    try:
        s3.head_bucket(Bucket=BUCKETS['blog'])
        return True
    except ClientError:
        return False


def create_buckets():
    for name, bucket in BUCKETS.items():
        s3.create_bucket(Bucket=bucket)
        if name in CDN_BUCKETS:
            s3.put_bucket_policy(Bucket=bucket, Policy=json.dumps({
                'Version': '2012-10-17',
                'Statement': [{
                    'Effect': 'Allow',
                    'Principal': '*',
                    'Action': 's3:GetObject',
                    'Resource': f'arn:aws:s3:::{bucket}/*',
                }],
            }))


def create_tables():
    # terraform/content_storage.tf
    dynamodb.create_table(
        TableName='spark.wiki.books',
        BillingMode='PAY_PER_REQUEST',
        AttributeDefinitions=[
            {'AttributeName': 'title', 'AttributeType': 'S'},
            {'AttributeName': 'date', 'AttributeType': 'N'},
        ],
        KeySchema=[
            {'AttributeName': 'title', 'KeyType': 'HASH'},
            {'AttributeName': 'date', 'KeyType': 'RANGE'},
        ],
    )

    taxonomy_ranks = ['species', 'family', 'order']
    dynamodb.create_table(
        TableName='spark.wiki.photos',
        BillingMode='PAY_PER_REQUEST',
        AttributeDefinitions=[
            {'AttributeName': attribute, 'AttributeType': 'S'}
            for attribute in ['s3_uri', *taxonomy_ranks]
        ],
        KeySchema=[
            {'AttributeName': 's3_uri', 'KeyType': 'HASH'},
            {'AttributeName': 'species', 'KeyType': 'RANGE'},
        ],
        GlobalSecondaryIndexes=[
            {
                'IndexName': f'taxonomy-{rank}',
                'KeySchema': [
                    {'AttributeName': rank, 'KeyType': 'HASH'},
                    {'AttributeName': 's3_uri', 'KeyType': 'RANGE'},
                ],
                'Projection': {'ProjectionType': 'ALL'},
            }
            for rank in taxonomy_ranks
        ],
    )

    dynamodb.create_table(
        TableName='spark.wiki.normal-photos',
        BillingMode='PAY_PER_REQUEST',
        AttributeDefinitions=[{'AttributeName': 's3_uri', 'AttributeType': 'S'}],
        KeySchema=[{'AttributeName': 's3_uri', 'KeyType': 'HASH'}],
    )


def put_parameters():
    # Not managed by Terraform in AWS (see backend/README.md).
    parameters = {
        'AdminUsername': ADMIN_USERNAME,
        'AdminPasswordHash': hash_password(ADMIN_PASSWORD),
        'AdminTokenSecret': secrets.token_hex(32),
        'GoogleBooksAPIKey': os.getenv('GOOGLE_BOOKS_API_KEY'),
        'GeminiAPIKey': os.getenv('GEMINI_API_KEY'),
    }
    for name, value in parameters.items():
        # Without its API keys, UpdateBookReview skips enrichment, as it does
        # when a lookup fails.
        if value:
            ssm.put_parameter(Name=name, Value=value, Type='SecureString')


def create_triggers():
    queue_url = sqs.create_queue(
        QueueName=EVENTS_QUEUE,
        # Longer than any Lambda's timeout, so no event's handed out twice.
        Attributes={'VisibilityTimeout': '900'},
    )['QueueUrl']
    queue_arn = sqs.get_queue_attributes(QueueUrl=queue_url, AttributeNames=['QueueArn'])['Attributes']['QueueArn']
    for name, events in TRIGGER_EVENTS.items():
        s3.put_bucket_notification_configuration(
            Bucket=BUCKETS[name],
            NotificationConfiguration={'QueueConfigurations': [{'QueueArn': queue_arn, 'Events': events}]},
        )


def content_type(path):
    if path.suffix == '.md':
        return 'text/markdown; charset=utf-8'
    return mimetypes.guess_type(path.name)[0] or 'application/octet-stream'


def upload(bucket, path, key):
    # One PUT each, like a browser upload: upload_file's multipart uploads
    # make the emulator send two events per file.
    s3.put_object(Bucket=bucket, Key=key, Body=path.read_bytes(), ContentType=content_type(path))


def sample_files(directory):
    return sorted(p for p in directory.rglob('*') if p.is_file() and not p.name.startswith('.'))


def preload_books():
    """Loads the snapshotted book reviews: their table items, covers, and
    review files. This runs before the books bucket's trigger is set up, so
    UpdateBookReview doesn't process them again -- and, without the API keys,
    drop their covers, genres, and synopses. Returns the review files' keys."""
    table = boto3.resource('dynamodb').Table('spark.wiki.books')
    review_keys = set()
    items = sorted(BOOKS_TABLE_DIR.glob('*.json'))
    for path in items:
        # boto3 takes Decimals, not floats.
        item = json.loads(path.read_text(encoding='utf-8'), parse_float=Decimal)
        table.put_item(Item=item)
        key = urlparse(item['s3_uri']).path.lstrip('/')
        review = SAMPLE_CONTENT['books'] / key
        if review.exists():
            upload(BUCKETS['books'], review, key)
            review_keys.add(key)

    covers = sample_files(BOOKS_COVERS_DIR) if BOOKS_COVERS_DIR.exists() else []
    for path in covers:
        upload(BUCKETS['books'], path, path.relative_to(BOOKS_DIR).as_posix())

    print(f'Loaded {len(items)} processed book review(s), and {len(covers)} cover(s), from {BOOKS_DIR.relative_to(REPO)}')
    return review_keys


def upload_sample_content(preloaded_reviews):
    for name, directory in SAMPLE_CONTENT.items():
        files = [
            (path, path.relative_to(directory).as_posix())
            for path in sample_files(directory)
        ]
        if name == 'books':
            files = [(path, key) for path, key in files if key not in preloaded_reviews]
        for path, key in files:
            upload(BUCKETS[name], path, key)
        print(f'Uploaded {len(files)} file(s) from {directory.relative_to(REPO)} to {BUCKETS[name]}')


def main():
    if already_seeded():
        print('The emulator is already set up.')
        return

    create_buckets()
    create_tables()
    put_parameters()
    preloaded_reviews = preload_books()
    create_triggers()
    upload_sample_content(preloaded_reviews)
    print('The emulator is set up. The content Lambdas are processing the sample content now.')


if __name__ == '__main__':
    main()
