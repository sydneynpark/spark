import boto3
from boto3.dynamodb.conditions import Key


class AWSUtil:
    def __init__(self):
        self.s3 = boto3.client('s3')
        self.dynamodb = boto3.resource('dynamodb')
        # Unlike s3/dynamodb, boto3.client('ssm') resolves its region
        # eagerly and raises NoRegionError immediately if none is
        # configured -- construct it lazily so AWSUtil() stays safe to
        # build in any environment (e.g. local dev, tests) that never
        # calls get_parameter().
        self._ssm = None

    @property
    def ssm(self):
        if self._ssm is None:
            self._ssm = boto3.client('ssm')
        return self._ssm

    def get_parameter(self, name):
        response = self.ssm.get_parameter(Name=name, WithDecryption=True)
        return response['Parameter']['Value']

    def get_s3_object(self, bucket, key):
        return self.s3.get_object(Bucket=bucket, Key=key)

    def put_s3_object(self, bucket, key, body, content_type='image/jpeg'):
        self.s3.put_object(Bucket=bucket, Key=key, Body=body, ContentType=content_type)

    def s3_object_exists(self, bucket, key):
        try:
            self.s3.head_object(Bucket=bucket, Key=key)
        except self.s3.exceptions.ClientError as e:
            if e.response['Error']['Code'] in ('404', 'NoSuchKey'):
                return False
            raise
        return True

    def delete_s3_object(self, bucket, key):
        self.s3.delete_object(Bucket=bucket, Key=key)

    def delete_s3_objects_under(self, bucket, prefix, keep=None):
        """Delete every object whose key starts with `prefix`, but `keep`."""
        paginator = self.s3.get_paginator('list_objects_v2')
        for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
            for obj in page.get('Contents', []):
                if obj['Key'] != keep:
                    self.s3.delete_object(Bucket=bucket, Key=obj['Key'])

    def store_book_review(self, s3_uri, book_review):
        table = self.dynamodb.Table('spark.wiki.books')
        item = book_review.to_item(s3_uri)
        table.put_item(Item=item)

        # The table's key is (title, date), but each title has just the one
        # <title>.md file. So a re-upload whose date_reviewed changed (e.g. an
        # edit from the admin page) would otherwise leave the old item behind
        # next to the new one -- and if the date moved earlier, the stale
        # item would win as the "latest" review.
        response = table.query(KeyConditionExpression=Key('title').eq(item['title']))
        for stale in response.get('Items', []):
            if stale['date'] != item['date']:
                table.delete_item(Key={'title': item['title'], 'date': stale['date']})

    def get_book_review(self, title):
        """The stored review for a title, or None. The most recent one, if
        there's somehow more than one."""
        table = self.dynamodb.Table('spark.wiki.books')
        response = table.query(
            KeyConditionExpression=Key('title').eq(title),
            ScanIndexForward=False,
            Limit=1,
        )
        items = response.get('Items', [])
        return items[0] if items else None

    def delete_book_review(self, title):
        # The table's primary key is (title, date). A delete event only
        # gives us the S3 key -- not the file contents -- so we can't
        # recover 'date' directly; query by partition key instead and
        # remove every item under that title (normally just one, but a book
        # could have been reviewed, and re-reviewed, more than once).
        table = self.dynamodb.Table('spark.wiki.books')
        response = table.query(KeyConditionExpression=Key('title').eq(title))
        for item in response.get('Items', []):
            table.delete_item(Key={'title': title, 'date': item['date']})
