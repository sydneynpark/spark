import boto3

from post_util import POSTS_TABLE


class AWSUtil:

    def __init__(self):
        self.s3 = boto3.client('s3')
        self.dynamodb = boto3.resource('dynamodb')

    def get_s3_object(self, bucket, key):
        return self.s3.get_object(Bucket=bucket, Key=key)

    def store_post(self, item):
        self.dynamodb.Table(POSTS_TABLE).put_item(Item=item)

    def delete_post(self, s3_uri):
        self.dynamodb.Table(POSTS_TABLE).delete_item(Key={'s3_uri': s3_uri})
