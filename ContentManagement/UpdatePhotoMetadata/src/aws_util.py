import boto3
class AWSUtil:

    def __init__(self):
        self.s3 = boto3.client('s3')
    
    def get_s3_object(self, bucket, key):
        return self.s3.get_object(Bucket=bucket, Key=key)