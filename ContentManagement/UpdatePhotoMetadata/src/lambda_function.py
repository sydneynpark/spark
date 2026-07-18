import aws_util
import img_util
import taxonomy_util
import urllib.parse
import io
import os
import re


print('Loading function')
aws = aws_util.AWSUtil()
img = img_util.ImageUtil()
taxonomy_file_path = os.path.join(os.path.dirname(__file__), 'Bird keywords.txt')
taxonomy = taxonomy_util.TaxonomyUtil(taxonomy_file_path)

DATE_PATH_PATTERN = re.compile(r'(\d{4})/(\d{2})/(\d{2})/')


def _date_from_key(key):
    # Fallback for photos with no usable EXIF date: photos are uploaded into
    # <bucket>/YYYY/MM/DD/<filename>, so the path itself encodes the date.
    match = DATE_PATH_PATTERN.search(key)
    return f'{match.group(1)}-{match.group(2)}-{match.group(3)}' if match else None


def lambda_handler(event, context):

    bucket = event['Records'][0]['s3']['bucket']['name']
    key = urllib.parse.unquote_plus(event['Records'][0]['s3']['object']['key'], encoding='utf-8')
    event_type = event['Records'][0]['eventName']
    
    try:
        print(f'There was a {event_type} event for S3 object: {bucket}/{key}')

        response = aws.get_s3_object(bucket, key)
        photo_bytes = response['Body'].read()
        photo_keywords = img.get_lightroom_keywords(io.BytesIO(photo_bytes))
        print('The image has keywords: ' + ', '.join(photo_keywords))
        
        # Parse taxonomic classifications from keywords
        taxonomies = taxonomy.parse_keywords_to_taxonomy(photo_keywords)
        print(f'Found {len(taxonomies)} species labeled in the photo.')

        date_captured = img.get_date_captured(io.BytesIO(photo_bytes)) or _date_from_key(key)

        s3_uri = f's3://{bucket}/{key}'
        aws.store_photo_metadata(s3_uri, taxonomies, date_captured)
        print(f'Stored metadata in DynamoDB')

        thumbnail = img.create_thumbnail(io.BytesIO(photo_bytes))
        aws.put_s3_object('spark.wiki.thumbnails', key, thumbnail)
        print(f'Saved thumbnail to spark.wiki.thumbnails/{key}')

        return taxonomies
    
    except Exception as e:
        print(e)
        raise e
