import aws_util
import urllib.parse
from blog_metadata import BlogPostContent

print('Loading function')
aws = aws_util.AWSUtil()

def lambda_handler(event, context):
    bucket = event['Records'][0]['s3']['bucket']['name']
    key = urllib.parse.unquote_plus(event['Records'][0]['s3']['object']['key'], encoding='utf-8')
    event_type = event['Records'][0]['eventName']
    
    try:
        print(f'There was a {event_type} event for S3 object: {bucket}/{key}')
        
        # Get the markdown content from S3
        blog_metadata = BlogPostContent.from_s3_key(key)

        return {
            'statusCode': 200,
            'metadata': str(blog_metadata),
        }
        
    except Exception as e:
        print(f'Error processing {key} from bucket {bucket}: {str(e)}')
        raise e