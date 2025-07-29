import aws_util
import img_util
import urllib.parse


print('Loading function')
aws = aws_util.AWSUtil()
img = img_util.ImageUtil()


def lambda_handler(event, context):

    bucket = event['Records'][0]['s3']['bucket']['name']
    key = urllib.parse.unquote_plus(event['Records'][0]['s3']['object']['key'], encoding='utf-8')
    event_type = event['Records'][0]['eventName']
    
    try:
        print(f'There was an event for S3 object: {bucket}/{key}')
        print(f'The event type is: {event_type}')
        response = aws.get_s3_object(bucket, key)

        photo = response['Body']
        photo_keywords = img.get_lightroom_keywords(photo)
        message = '\n - '.join(['The image has keywords:'] + photo_keywords)
        print(message)
        return photo_keywords
    
    except Exception as e:
        print(e)
        print(f'Error getting object {key} from bucket {bucket}. Make sure they exist and your bucket is in the same region as this function.')
        raise e
