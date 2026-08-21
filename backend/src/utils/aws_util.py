import boto3
from boto3.dynamodb.conditions import Key, Attr

class DynamoUtil:
    def __init__(self):
        self.dynamodb = boto3.resource('dynamodb')
        self.photos_table = self.dynamodb.Table('spark.wiki.photos')
        self.books_table = self.dynamodb.Table('spark.wiki.books')
    
    def _paginate(self, table_method, limit=None, **kwargs):
        """Call a boto3 scan/query method repeatedly, following
        LastEvaluatedKey, until either the table/index is exhausted or
        `limit` total items have been collected."""
        items = []
        while True:
            response = table_method(**kwargs)
            items.extend(response.get('Items', []))

            last_key = response.get('LastEvaluatedKey')
            if not last_key or (limit is not None and len(items) >= limit):
                break

            kwargs['ExclusiveStartKey'] = last_key

        return items[:limit] if limit is not None else items

    def get_photos(self, species=None, family=None, order=None, year=None, month=None, day=None, limit=50):
        """Get photos with optional filtering by taxonomy or date captured"""
        try:
            # date is stored as 'YYYY-MM-DD'; day/month/year are all just
            # increasingly specific prefixes of that same string.
            date_prefix = day or month or year

            if species:
                # Query the taxonomy-species GSI
                return self._paginate(
                    self.photos_table.query,
                    limit=limit,
                    IndexName='taxonomy-species',
                    KeyConditionExpression=Key('species').eq(species),
                )
            elif family:
                # Query the taxonomy-family GSI
                return self._paginate(
                    self.photos_table.query,
                    limit=limit,
                    IndexName='taxonomy-family',
                    KeyConditionExpression=Key('family').eq(family),
                )
            elif order:
                # Query the taxonomy-order GSI
                return self._paginate(
                    self.photos_table.query,
                    limit=limit,
                    IndexName='taxonomy-order',
                    KeyConditionExpression=Key('order').eq(order),
                )
            elif date_prefix:
                # Scan with date filter
                return self._paginate(
                    self.photos_table.scan,
                    limit=limit,
                    FilterExpression=Attr('date').begins_with(date_prefix),
                )
            else:
                # Get all photos
                return self._paginate(self.photos_table.scan, limit=limit)

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
            items = self._paginate(
                self.photos_table.scan,
                ProjectionExpression='species'
            )

            # Extract unique species names
            species_set = set()
            for item in items:
                if 'species' in item:
                    species_set.add(item['species'])

            return sorted(list(species_set))

        except Exception as e:
            print(f'Error getting species list: {str(e)}')
            raise e

    def get_books(self, limit=50):
        """List all book reviews, most recently reviewed first"""
        try:
            response = self.books_table.scan(Limit=limit)
            books = response.get('Items', [])
            books.sort(key=lambda b: b.get('date', 0), reverse=True)
            return books

        except Exception as e:
            print(f'Error getting books: {str(e)}')
            raise e

    def get_book_by_title(self, title):
        """Get a single book review by title (partition key). If a title has
        been reviewed more than once, the most recent review wins."""
        try:
            response = self.books_table.query(
                KeyConditionExpression=Key('title').eq(title),
                ScanIndexForward=False,
                Limit=1,
            )
            items = response.get('Items', [])
            return items[0] if items else None

        except Exception as e:
            print(f'Error getting book {title}: {str(e)}')
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

