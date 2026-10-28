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

# The photos bucket's two collections: bird photos, and photos of anything
# else, which get the same treatment, less the taxonomy. Anything outside
# them (like archive/) is left alone.
BIRDS_PREFIX = 'birds/'
PHOTOS_PREFIX = 'photos/'
THUMBNAILS_BUCKET = 'spark.wiki.thumbnails'


def _date_from_key(key):
    # Fallback for photos with no usable EXIF date: photos are uploaded into
    # <collection>/YYYY/MM/DD/<filename>, so the path itself encodes the date.
    match = DATE_PATH_PATTERN.search(key)
    return f'{match.group(1)}-{match.group(2)}-{match.group(3)}' if match else None


def lambda_handler(event, context):

    bucket = event['Records'][0]['s3']['bucket']['name']
    key = urllib.parse.unquote_plus(event['Records'][0]['s3']['object']['key'], encoding='utf-8')
    event_type = event['Records'][0]['eventName']
    
    try:
        print(f'There was a {event_type} event for S3 object: {bucket}/{key}')

        # An empty "folder" placeholder, like the ones the admin page's (or
        # the S3 console's) "create folder" makes -- not a photo.
        if key.endswith('/'):
            print('Skipping folder placeholder')
            return []

        if not key.startswith((BIRDS_PREFIX, PHOTOS_PREFIX)):
            print(f'Skipping: not in {BIRDS_PREFIX} or {PHOTOS_PREFIX}')
            return []

        response = aws.get_s3_object(bucket, key)
        photo_bytes = response['Body'].read()
        date_captured = img.get_date_captured(io.BytesIO(photo_bytes)) or _date_from_key(key)
        s3_uri = f's3://{bucket}/{key}'

        if key.startswith(PHOTOS_PREFIX):
            # No species to read from its keywords (which it may not have).
            result = aws.store_photo_metadata(s3_uri, date_captured)
        else:
            photo_keywords = img.get_lightroom_keywords(io.BytesIO(photo_bytes))
            print('The image has keywords: ' + ', '.join(photo_keywords))

            # Parse taxonomic classifications from keywords
            result = taxonomy.parse_keywords_to_taxonomy(photo_keywords)
            print(f'Found {len(result)} species labeled in the photo.')

            aws.store_bird_metadata(s3_uri, result, date_captured)
        print(f'Stored metadata in DynamoDB')

        thumbnail = img.create_thumbnail(io.BytesIO(photo_bytes))
        thumbnail_key = f'thumbnail/{key}'
        aws.put_s3_object(THUMBNAILS_BUCKET, thumbnail_key, thumbnail)
        print(f'Saved thumbnail to {THUMBNAILS_BUCKET}/{thumbnail_key}')

        return result
    
    except Exception as e:
        print(e)
        raise e
