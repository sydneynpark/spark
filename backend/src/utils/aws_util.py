import boto3
from boto3.dynamodb.conditions import Key, Attr

class DynamoUtil:
    def __init__(self):
        self.dynamodb = boto3.resource('dynamodb')
        self.photos_table = self.dynamodb.Table('spark.wiki.photos')
    
    def get_photos(self, species=None, family=None, order=None, limit=50):
        """Get photos with optional filtering by taxonomy"""
        try:
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

class S3Util:
    def __init__(self):
        self.s3 = boto3.client('s3')
    
    def get_post_content(self, s3_uri):
        """Get blog post content from S3 (placeholder for later)"""
        # Parse s3://bucket/key format
        parts = s3_uri.replace('s3://', '').split('/', 1)
        bucket = parts[0]
        key = parts[1]
        
        response = self.s3.get_object(Bucket=bucket, Key=key)
        return response['Body'].read().decode('utf-8')