import boto3
class AWSUtil:

    def __init__(self):
        self.s3 = boto3.client('s3')
        self.dynamodb = boto3.resource('dynamodb')
    
    def get_s3_object(self, bucket, key):
        return self.s3.get_object(Bucket=bucket, Key=key)
    
    def store_photo_metadata(self, s3_uri, taxonomies):
        # taxonomies is a list of dicts, each containing taxonomic classification
        # for a species found in the photo (class, order, family, genus, species)
        table = self.dynamodb.Table('spark.wiki.photos')
        
        # Store each species taxonomy as a separate item
        for taxonomy in taxonomies:
            item = {
                's3_uri': s3_uri,
                'species': taxonomy.get('species'),
                'class': taxonomy.get('class'),
                'order': taxonomy.get('order'),
                'family': taxonomy.get('family'),
            }
            
            # Only add scientific_name if it exists
            if taxonomy.get('scientific_name'):
                item['scientific_name'] = taxonomy.get('scientific_name')
                
            table.put_item(Item=item)