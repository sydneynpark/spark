import aws_util
import book_review_util
import os
import urllib.parse

print('Loading function')
aws = aws_util.AWSUtil()
reviews = book_review_util.BookReviewUtil()


def _title_from_key(key):
    # Review files are named after the book's title (see sample-data/books),
    # so a delete event -- which gives us only the S3 key, not the file's
    # contents -- can still recover the 'title' partition key.
    return os.path.splitext(os.path.basename(key))[0]


def lambda_handler(event, context):
    bucket = event['Records'][0]['s3']['bucket']['name']
    key = urllib.parse.unquote_plus(event['Records'][0]['s3']['object']['key'], encoding='utf-8')
    event_type = event['Records'][0]['eventName']
    s3_uri = f's3://{bucket}/{key}'

    try:
        print(f'There was a {event_type} event for S3 object: {bucket}/{key}')

        if event_type.startswith('ObjectRemoved'):
            title = _title_from_key(key)
            aws.delete_book_review(title)
            print(f'Deleted book review "{title}" from DynamoDB')
            return {
                'statusCode': 200,
                'deleted': title,
            }

        response = aws.get_s3_object(bucket, key)
        markdown_content = response['Body'].read().decode('utf-8')
        book_review = reviews.parse(markdown_content)

        aws.store_book_review(s3_uri, book_review)
        print(f'Stored book review metadata in DynamoDB for {s3_uri}')

        return {
            'statusCode': 200,
            'metadata': str(book_review),
        }

    except Exception as e:
        print(f'Error processing {key} from bucket {bucket}: {str(e)}')
        raise e
