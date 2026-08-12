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

    def delete_s3_object(self, bucket, key):
        self.s3.delete_object(Bucket=bucket, Key=key)

    def store_book_review(self, s3_uri, book_review):
        table = self.dynamodb.Table('spark.wiki.books')
        table.put_item(Item=book_review.to_item(s3_uri))

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
