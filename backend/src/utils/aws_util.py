import boto3
from boto3.dynamodb.conditions import Key, Attr
from botocore.config import Config
from itertools import groupby
from operator import itemgetter

def review_date(book):
    return book.get('date', 0)

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

    def get_taxonomy(self):
        """Build a class > order > family > species hierarchy with counts
        and up to 3 sample thumbnail URIs per species, so the frontend
        doesn't need to fetch every photo just to render the browse tree."""
        try:
            items = self._paginate(self.photos_table.scan)
            tree = {}

            for item in items:
                class_name = item.get('class') or 'Unknown Class'
                order = item.get('order') or 'Unknown Order'
                family = item.get('family') or 'Unknown Family'
                species = item.get('species') or 'Unknown Species'

                class_node = tree.setdefault(class_name, {'count': 0, 'orders': {}})
                order_node = class_node['orders'].setdefault(order, {'count': 0, 'families': {}})
                family_node = order_node['families'].setdefault(family, {'count': 0, 'species': {}})
                species_node = family_node['species'].setdefault(species, {'count': 0, 'thumbnails': []})

                class_node['count'] += 1
                order_node['count'] += 1
                family_node['count'] += 1
                species_node['count'] += 1
                if len(species_node['thumbnails']) < 3:
                    species_node['thumbnails'].append(item['s3_uri'])

            return tree

        except Exception as e:
            print(f'Error getting taxonomy: {str(e)}')
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
        """List all book reviews, most recently reviewed first. Like
        get_book_by_title, a title reviewed more than once is listed once,
        with its most recent review."""
        try:
            response = self.books_table.scan(Limit=limit)
            # The table's key is (title, date), so reprocessing a review whose
            # date_reviewed changed (or went missing, giving date 0) adds a
            # second item rather than replacing the first. The frontend keys
            # books by title, so duplicates break its list rendering.
            # groupby only groups adjacent items, hence sorting by title first.
            by_title = sorted(response.get('Items', []), key=itemgetter('title'))
            latest = [max(reviews, key=review_date) for _, reviews in groupby(by_title, key=itemgetter('title'))]
            return sorted(latest, key=review_date, reverse=True)

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


BOOKS_BUCKET = 'spark.wiki.books'


class BooksAdminUtil:
    """Publishes admin-authored reviews into the same S3 bucket (and same
    <title>.md key convention) that a manually-uploaded review would use, so
    the existing UpdateBookReview lambda's S3 trigger does the rest (cover
    art, genres, synopsis, and the actual DynamoDB write)."""

    def __init__(self):
        self.s3 = boto3.client('s3')

    def publish_book_review(self, title, markdown, payload):
        self.s3.put_object(
            Bucket=BOOKS_BUCKET,
            Key=f'{title}.md',
            Body=markdown.encode('utf-8'),
            ContentType='text/markdown; charset=utf-8',
        )


PHOTOS_BUCKET = 'spark.wiki.photos'
UPLOAD_URL_TTL_SECONDS = 15 * 60


class PhotosAdminUtil:
    """Browses spark.wiki.photos' folders and hands out presigned PUT URLs,
    so the admin page uploads photos straight to S3 -- full-size photos are
    bigger than API Gateway and Lambda will accept in a request. The
    existing UpdatePhotoMetadata lambda's S3 trigger takes it from there
    (taxonomy, date, thumbnail, and the DynamoDB write)."""

    def __init__(self):
        # SigV4 rather than boto3's legacy SigV2 default for presigned URLs.
        # The bucket's dotted name gets a path-style URL either way, since
        # virtual-hosted ones would fail TLS validation in the browser.
        self.s3 = boto3.client('s3', config=Config(signature_version='s3v4'))

    def list_folder(self, prefix):
        """The subfolder names and photos directly inside `prefix`."""
        folders, photos = [], []
        paginator = self.s3.get_paginator('list_objects_v2')
        for page in paginator.paginate(Bucket=PHOTOS_BUCKET, Prefix=prefix, Delimiter='/'):
            folders.extend(p['Prefix'][len(prefix):-1] for p in page.get('CommonPrefixes', []))
            for obj in page.get('Contents', []):
                # The folder's own placeholder object, if it has one.
                if obj['Key'] == prefix:
                    continue
                photos.append({
                    'name': obj['Key'][len(prefix):],
                    's3_uri': f's3://{PHOTOS_BUCKET}/{obj["Key"]}',
                    'size': obj['Size'],
                    'last_modified': obj['LastModified'].isoformat(),
                })
        return folders, photos

    def create_folder(self, prefix):
        """S3 has no real folders, just key prefixes; this makes the same
        empty placeholder object the S3 console's "Create folder" does, so
        the folder exists before anything is uploaded into it."""
        self.s3.put_object(Bucket=PHOTOS_BUCKET, Key=prefix, Body=b'')

    def presign_upload(self, key, content_type):
        """A URL the browser can PUT the photo to directly, sending
        `content_type` as its Content-Type header."""
        return self.s3.generate_presigned_url(
            'put_object',
            Params={'Bucket': PHOTOS_BUCKET, 'Key': key, 'ContentType': content_type},
            ExpiresIn=UPLOAD_URL_TTL_SECONDS,
        )

