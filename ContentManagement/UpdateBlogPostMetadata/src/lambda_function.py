import aws_util
import urllib.parse

from post_util import post_item

print('Loading function')
aws = aws_util.AWSUtil()


def lambda_handler(event, context):
    """Keeps the posts table in step with the blog bucket: a post's item is
    written when it's uploaded, from its frontmatter and body (as
    post_util.post_item reads them), and deleted along with it. The API lists
    posts, and finds them by slug, from the table, rather than reading every
    post."""
    bucket = event['Records'][0]['s3']['bucket']['name']
    key = urllib.parse.unquote_plus(event['Records'][0]['s3']['object']['key'], encoding='utf-8')
    event_type = event['Records'][0]['eventName']
    s3_uri = f's3://{bucket}/{key}'

    try:
        print(f'There was a {event_type} event for S3 object: {bucket}/{key}')

        # The admin page keeps drafts, and the photos uploaded to them, under
        # drafts/ (see backend/src/utils/draft_util.py). They aren't posts.
        if not key.endswith('.md') or key.startswith('drafts/'):
            print('Skipping: not a post')
            return {'statusCode': 200, 'item': None}

        if event_type.startswith('ObjectRemoved'):
            aws.delete_post(s3_uri)
            print(f'Deleted {s3_uri} from the posts table')
            return {'statusCode': 200, 'deleted': s3_uri}

        response = aws.get_s3_object(bucket, key)
        markdown_content = response['Body'].read().decode('utf-8', errors='ignore')
        item = post_item(key, markdown_content, response['LastModified'].isoformat())
        aws.store_post(item)
        print(f'Stored "{item["title"]}" in the posts table')

        return {'statusCode': 200, 'item': item}

    except Exception as e:
        print(f'Error processing {key} from bucket {bucket}: {str(e)}')
        raise e
