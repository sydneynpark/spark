import boto3
from boto3.dynamodb.conditions import Key, Attr

class DynamoUtil:
    def __init__(self):
        self.dynamodb = boto3.resource('dynamodb')
        self.photos_table = self.dynamodb.Table('spark.wiki.photos')
    
    def get_photos(self, species=None, family=None, order=None, year=None, month=None, day=None, limit=50):
        """Get photos with optional filtering by taxonomy or date captured"""
        try:
            # date is stored as 'YYYY-MM-DD'; day/month/year are all just
            # increasingly specific prefixes of that same string.
            date_prefix = day or month or year

            if species:
                # Scan with species filter
                response = self.photos_table.scan(
                    FilterExpression=Attr('species').eq(species),
                    Limit=limit
                )
            elif family:
                # Scan with family filter
                response = self.photos_table.scan(
                    FilterExpression=Attr('family').eq(family),
                    Limit=limit
                )
            elif order:
                # Scan with order filter
                response = self.photos_table.scan(
                    FilterExpression=Attr('order').eq(order),
                    Limit=limit
                )
            elif date_prefix:
                # Scan with date filter
                response = self.photos_table.scan(
                    FilterExpression=Attr('date').begins_with(date_prefix),
                    Limit=limit
                )
            else:
                # Get all photos
                response = self.photos_table.scan(Limit=limit)

            return response.get('Items', [])
            
        except Exception as e:
            print(f'Error getting photos: {str(e)}')
            raise e
    
    def get_photo_by_id(self, photo_id):
        """Get specific photo by S3 URI"""
        try:
            # photo_id should be the S3 URI (partition key)
            response = self.photos_table.get_item(
                Key={'s3_uri': photo_id}
            )
            return response.get('Item')
            
        except Exception as e:
            print(f'Error getting photo {photo_id}: {str(e)}')
            raise e
    
    def get_all_species(self):
        """Get list of all unique species"""
        try:
            response = self.photos_table.scan(
                ProjectionExpression='species'
            )
            
            # Extract unique species names
            species_set = set()
            for item in response.get('Items', []):
                if 'species' in item:
                    species_set.add(item['species'])
            
            return sorted(list(species_set))
            
        except Exception as e:
            print(f'Error getting species list: {str(e)}')
            raise e

BLOG_BUCKET = 'spark.wiki.blog'

class S3Util:
    def __init__(self):
        self.s3 = boto3.client('s3')

    def list_posts(self):
        """List all markdown blog posts from S3"""
        from utils.response_util import parse_post_metadata, extract_preview
        response = self.s3.list_objects_v2(Bucket=BLOG_BUCKET)
        posts = []
        for obj in response.get('Contents', []):
            key = obj['Key']
            if not key.endswith('.md'):
                continue
            meta = parse_post_metadata(key)
            meta['key'] = key
            meta['last_modified'] = obj['LastModified'].isoformat()
            try:
                preview_response = self.s3.get_object(Bucket=BLOG_BUCKET, Key=key, Range='bytes=0-599')
                preview_text = preview_response['Body'].read().decode('utf-8', errors='ignore')
                meta['preview'] = extract_preview(preview_text)
            except Exception:
                meta['preview'] = ''
            posts.append(meta)
        posts.sort(key=lambda p: (p['date'] or ''), reverse=True)
        return posts

    def get_post_content(self, key):
        """Get blog post markdown content from S3"""
        response = self.s3.get_object(Bucket=BLOG_BUCKET, Key=key)
        return response['Body'].read().decode('utf-8')

