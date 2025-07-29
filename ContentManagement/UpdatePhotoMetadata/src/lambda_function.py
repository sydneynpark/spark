import aws_util
import img_util
import taxonomy_util
import urllib.parse
import os


print('Loading function')
aws = aws_util.AWSUtil()
img = img_util.ImageUtil()
taxonomy_file_path = os.path.join(os.path.dirname(__file__), 'Bird keywords.txt')
taxonomy = taxonomy_util.TaxonomyUtil(taxonomy_file_path)


def lambda_handler(event, context):

    bucket = event['Records'][0]['s3']['bucket']['name']
    key = urllib.parse.unquote_plus(event['Records'][0]['s3']['object']['key'], encoding='utf-8')
    event_type = event['Records'][0]['eventName']
    
    try:
        print(f'There was a {event_type} event for S3 object: {bucket}/{key}')

        response = aws.get_s3_object(bucket, key)
        photo = response['Body']
        photo_keywords = img.get_lightroom_keywords(photo)
        print('The image has keywords: ' + ', '.join(photo_keywords))
        
        # Parse taxonomic classifications from keywords
        taxonomies = taxonomy.parse_keywords_to_taxonomy(photo_keywords)
        print(f'Found {len(taxonomies)} species labeled in the photo.')
        
        s3_uri = f's3://{bucket}/{key}'
        aws.store_photo_metadata(s3_uri, taxonomies)
        print(f'Stored metadata in DynamoDB')
        
        return taxonomies
    
    except Exception as e:
        print(e)
        raise e
