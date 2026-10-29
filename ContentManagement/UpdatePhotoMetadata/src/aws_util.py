import boto3


def bird_items(s3_uri, taxonomies, date_captured=None):
    # taxonomies is a list of dicts, each containing taxonomic classification
    # for a species found in the photo (class, order, family, genus, species)
    items = []

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

        if date_captured:
            item['date'] = date_captured

        items.append(item)
    return items


def photo_item(s3_uri, date_captured=None):
    item = {'s3_uri': s3_uri}
    if date_captured:
        item['date'] = date_captured
    return item


class AWSUtil:

    def __init__(self):
        self.s3 = boto3.client('s3')
        self.dynamodb = boto3.resource('dynamodb')

    def get_s3_object(self, bucket, key):
        return self.s3.get_object(Bucket=bucket, Key=key)

    def store_bird_metadata(self, s3_uri, taxonomies, date_captured=None):
        table = self.dynamodb.Table('spark.wiki.photos')
        for item in bird_items(s3_uri, taxonomies, date_captured):
            table.put_item(Item=item)

    def store_photo_metadata(self, s3_uri, date_captured=None):
        item = photo_item(s3_uri, date_captured)
        self.dynamodb.Table('spark.wiki.normal-photos').put_item(Item=item)
        return item

    def put_s3_object(self, bucket, key, body, content_type='image/jpeg'):
        self.s3.put_object(Bucket=bucket, Key=key, Body=body, ContentType=content_type)