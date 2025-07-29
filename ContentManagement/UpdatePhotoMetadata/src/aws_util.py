import boto3
class AWSUtil:

    def __init__(self):
        self.s3 = boto3.client('s3')
        self.dynamodb = boto3.resource('dynamodb')
    
    def get_s3_object(self, bucket, key):
        return self.s3.get_object(Bucket=bucket, Key=key)
    
    def store_photo_metadata(self, s3_uri, keywords):
        table = self.dynamodb.Table('spark.wiki.photos')
        table.put_item(
            Item={
                's3_uri': s3_uri,
                'keywords': keywords
            }
        )