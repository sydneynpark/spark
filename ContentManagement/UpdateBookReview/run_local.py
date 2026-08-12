import json
import os
import sys
import urllib.parse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

import gemini_util
import google_books_util
import lambda_function

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.join(THIS_DIR, '..', '..')
BOOKS_DIR = os.path.join(REPO_ROOT, 'sample-data', 'books')
MARKDOWN_DIR = os.path.join(BOOKS_DIR, 'markdown')
DYNAMO_DIR = os.path.join(BOOKS_DIR, 'dynamo')
BUCKET = 'spark.wiki.books'


def _read_key(filename):
    with open(os.path.join(THIS_DIR, '..', filename), encoding='utf-8') as f:
        return f.read().strip()


class _BytesBody:
    """Just enough of botocore's StreamingBody interface for
    lambda_handler's response['Body'].read().decode('utf-8') call."""

    def __init__(self, data):
        self._data = data

    def read(self):
        return self._data


class LocalAWSUtil:
    """Stands in for aws_util.AWSUtil during a local run. Redirects the S3
    reads/writes and the DynamoDB write the lambda would otherwise make
    against real AWS to files under sample-data/books instead, mirroring
    the LOCAL_MODE pattern already used in backend/."""

    def get_s3_object(self, bucket, key):
        with open(os.path.join(MARKDOWN_DIR, key), 'rb') as f:
            return {'Body': _BytesBody(f.read())}

    def put_s3_object(self, bucket, key, body, content_type='image/jpeg'):
        path = os.path.join(BOOKS_DIR, *key.split('/'))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'wb') as f:
            f.write(body)

    def store_book_review(self, s3_uri, book_review):
        os.makedirs(DYNAMO_DIR, exist_ok=True)
        item = book_review.to_item(s3_uri)
        out_path = os.path.join(DYNAMO_DIR, f'{book_review.title}.json')
        with open(out_path, 'w', encoding='utf-8') as f:
            # Decimal (from commentary 'point' values) isn't JSON-serializable
            # by default -- this is inspection/local-dev output, not a real
            # DynamoDB put_item call, so a plain float is the natural fit.
            json.dump(item, f, indent=2, ensure_ascii=False, default=float)


def _upload_event(filename):
    return {
        'Records': [{
            'eventName': 'ObjectCreated:Put',
            's3': {
                'bucket': {'name': BUCKET},
                'object': {'key': urllib.parse.quote_plus(filename)},
            },
        }]
    }


def main():
    # Real Open Library/Google Books/Gemini calls -- only AWS is stubbed out.
    lambda_function.aws = LocalAWSUtil()
    lambda_function.google_books = google_books_util.GoogleBooksUtil(_read_key('.googleBooksApiKey'))
    lambda_function.gemini = gemini_util.GeminiUtil(_read_key('.geminiApiKey'))

    filenames = sorted(f for f in os.listdir(MARKDOWN_DIR) if f.endswith('.md'))
    print(f'Found {len(filenames)} review(s) in {MARKDOWN_DIR}\n')

    for filename in filenames:
        print(f'=== {filename} ===')
        result = lambda_function.lambda_handler(_upload_event(filename), None)
        print(f'  -> {result}\n')

    print(f'Wrote {len(filenames)} item(s) to {DYNAMO_DIR}')


if __name__ == '__main__':
    main()
