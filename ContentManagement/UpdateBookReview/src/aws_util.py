import boto3
from boto3.dynamodb.conditions import Key


class AWSUtil:
    def __init__(self):
        self.s3 = boto3.client('s3')
        self.dynamodb = boto3.resource('dynamodb')

    def get_s3_object(self, bucket, key):
        return self.s3.get_object(Bucket=bucket, Key=key)

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
