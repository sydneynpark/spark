import json

import boto3
from boto3.dynamodb.conditions import Key, Attr
from botocore.config import Config
from botocore.exceptions import ClientError
from itertools import groupby
from operator import itemgetter

from utils.draft_util import (
    DRAFTS_PREFIX, EDITING_FILENAME, build_markdown, draft_from_post, draft_id_from_key, draft_key, draft_photo,
    draft_prefix, editing_key, new_draft_id, parse_draft,
)
from utils.photo_upload_util import PHOTO_COLLECTIONS, PHOTO_CONTENT_TYPE

def review_date(book):
    return book.get('date', 0)

class DynamoUtil:
    def __init__(self):
        self.dynamodb = boto3.resource('dynamodb')
        # The tables are named for what they held first: spark.wiki.photos
        # has the bird photos, and spark.wiki.normal-photos the rest.
        self.birds_table = self.dynamodb.Table('spark.wiki.photos')
        self.photos_table = self.dynamodb.Table('spark.wiki.normal-photos')
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

    def get_birds(self, species=None, family=None, order=None, year=None, month=None, day=None, limit=50):
        """Get bird photos with optional filtering by taxonomy or date captured"""
        try:
            # date is stored as 'YYYY-MM-DD'; day/month/year are all just
            # increasingly specific prefixes of that same string.
            date_prefix = day or month or year

            if species:
                # Query the taxonomy-species GSI
                return self._paginate(
                    self.birds_table.query,
                    limit=limit,
                    IndexName='taxonomy-species',
                    KeyConditionExpression=Key('species').eq(species),
                )
            elif family:
                # Query the taxonomy-family GSI
                return self._paginate(
                    self.birds_table.query,
                    limit=limit,
                    IndexName='taxonomy-family',
                    KeyConditionExpression=Key('family').eq(family),
                )
            elif order:
                # Query the taxonomy-order GSI
                return self._paginate(
                    self.birds_table.query,
                    limit=limit,
                    IndexName='taxonomy-order',
                    KeyConditionExpression=Key('order').eq(order),
                )
            elif date_prefix:
                # Scan with date filter
                return self._paginate(
                    self.birds_table.scan,
                    limit=limit,
                    FilterExpression=Attr('date').begins_with(date_prefix),
                )
            else:
                # Get all photos
                return self._paginate(self.birds_table.scan, limit=limit)

        except Exception as e:
            print(f'Error getting photos: {str(e)}')
            raise e

    def get_bird_by_id(self, photo_id):
        """Get specific bird photo by S3 URI"""
        try:
            # photo_id should be the S3 URI (partition key)
            response = self.birds_table.get_item(
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
            items = self._paginate(self.birds_table.scan)
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
                self.birds_table.scan,
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

    def get_photos(self, year=None, month=None, day=None, limit=None):
        """Get the photos that aren't of birds, optionally just those captured
        in a year, month, or day, newest day first (and in filename order
        within a day). Each has its s3_uri, and its date, if it has one."""
        try:
            # 'YYYY', 'YYYY-MM', or 'YYYY-MM-DD', as in get_birds.
            date_prefix = day or month or year
            kwargs = {'FilterExpression': Attr('date').begins_with(date_prefix)} if date_prefix else {}
            photos = self._paginate(self.photos_table.scan, limit=limit, **kwargs)
            photos.sort(key=itemgetter('s3_uri'))
            photos.sort(key=lambda photo: photo.get('date', ''), reverse=True)
            return photos

        except Exception as e:
            print(f'Error getting photos: {str(e)}')
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
        """Parse every markdown blog post in S3, newest first. Each is read
        in full, since frontmatter and the first photo can be anywhere in
        it. Drafts (see utils/draft_util.py) aren't posts."""
        from utils.post_util import parse_post
        response = self.s3.list_objects_v2(Bucket=BLOG_BUCKET)
        posts = []
        for obj in response.get('Contents', []):
            key = obj['Key']
            if not key.endswith('.md') or key.startswith(DRAFTS_PREFIX):
                continue
            post_response = self.s3.get_object(Bucket=BLOG_BUCKET, Key=key)
            post = parse_post(key, post_response['Body'].read().decode('utf-8', errors='ignore'))
            post['last_modified'] = obj['LastModified'].isoformat()
            posts.append(post)
        posts.sort(key=lambda p: (p['date'] or ''), reverse=True)
        return posts


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
# Long enough to write a post with the editor open, which fetches them again
# when it's reopened.
DRAFT_PHOTO_VIEW_TTL_SECONDS = 4 * 60 * 60


class PhotosAdminUtil:
    """Browses a photo collection's folders and hands out presigned PUT
    URLs, so the admin page uploads photos straight to S3 -- full-size photos
    are bigger than API Gateway and Lambda will accept in a request. The
    existing UpdatePhotoMetadata lambda's S3 trigger takes it from there
    (taxonomy, for bird photos, date, thumbnail, and the DynamoDB write)."""

    def __init__(self):
        # SigV4 rather than boto3's legacy SigV2 default for presigned URLs.
        # The bucket's dotted name gets a path-style URL either way, since
        # virtual-hosted ones would fail TLS validation in the browser.
        self.s3 = boto3.client('s3', config=Config(signature_version='s3v4'))

    def list_folder(self, collection, prefix):
        """The subfolder names and photos directly inside `prefix`, a folder
        in `collection`'s folder."""
        folders, photos = [], []
        prefix = f'{PHOTO_COLLECTIONS[collection]}{prefix}'
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

    def create_folder(self, collection, prefix):
        """S3 has no real folders, just key prefixes; this makes the same
        empty placeholder object the S3 console's "Create folder" does, so
        the folder exists before anything is uploaded into it."""
        self.s3.put_object(Bucket=PHOTOS_BUCKET, Key=f'{PHOTO_COLLECTIONS[collection]}{prefix}', Body=b'')

    def presign_upload(self, key, content_type):
        """A URL the browser can PUT the photo to directly, at bucket key
        `key`, sending `content_type` as its Content-Type header."""
        return self.s3.generate_presigned_url(
            'put_object',
            Params={'Bucket': PHOTOS_BUCKET, 'Key': key, 'ContentType': content_type},
            ExpiresIn=UPLOAD_URL_TTL_SECONDS,
        )


class PublishConflict(Exception):
    """Publishing a draft would overwrite a post or photo that's already on
    the site -- its message is shown to the admin as-is."""


class DraftsAdminUtil:
    """Keeps blog post drafts, and the photos uploaded to them, in the blog
    bucket (laid out as utils/draft_util.py describes), and publishes them:
    the photos into the photos bucket, where UpdatePhotoMetadata processes
    them as it would any other upload, and the post into the blog bucket."""

    def __init__(self):
        # SigV4, as for PhotosAdminUtil's presigned URLs.
        self.s3 = boto3.client('s3', config=Config(signature_version='s3v4'))

    def _read(self, bucket, key):
        try:
            response = self.s3.get_object(Bucket=bucket, Key=key)
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                return None
            raise
        return response['Body'].read().decode('utf-8')

    def _etag(self, bucket, key):
        """The object's ETag, or None if there's none at `key`."""
        try:
            return self.s3.head_object(Bucket=bucket, Key=key)['ETag']
        except ClientError as e:
            if e.response['Error']['Code'] in ('404', 'NoSuchKey', 'NotFound'):
                return None
            raise

    def _keys(self, prefix):
        paginator = self.s3.get_paginator('list_objects_v2')
        for page in paginator.paginate(Bucket=BLOG_BUCKET, Prefix=prefix):
            for obj in page.get('Contents', []):
                yield obj

    def list_drafts(self):
        """Every draft's fields (less its body), and when it was last saved,
        most recently saved first."""
        drafts = []
        for obj in self._keys(DRAFTS_PREFIX):
            draft_id = draft_id_from_key(obj['Key'])
            if not draft_id:
                continue
            markdown = self._read(BLOG_BUCKET, obj['Key'])
            if markdown is None:
                continue
            fields = parse_draft(markdown)
            del fields['content']
            drafts.append({
                'id': draft_id,
                **fields,
                'editing': self.editing_summary(draft_id),
                'last_modified': obj['LastModified'].isoformat(),
            })
        drafts.sort(key=itemgetter('last_modified'), reverse=True)
        return drafts

    def get_draft(self, draft_id):
        """The draft's fields, or None if there's no such draft."""
        markdown = self._read(BLOG_BUCKET, draft_key(draft_id))
        return parse_draft(markdown) if markdown is not None else None

    def save_draft(self, draft_id, markdown):
        self.s3.put_object(
            Bucket=BLOG_BUCKET,
            Key=draft_key(draft_id),
            Body=markdown.encode('utf-8'),
            ContentType='text/markdown; charset=utf-8',
        )

    def list_photos(self, draft_id):
        """The photos uploaded to the draft, each with a URL to view it by
        for a while, as the photos CDN doesn't serve the blog bucket."""
        photos = []
        for obj in self._keys(draft_prefix(draft_id)):
            photo = draft_photo(draft_id, obj['Key'])
            if photo:
                photo['url'] = self.s3.generate_presigned_url(
                    'get_object',
                    Params={'Bucket': BLOG_BUCKET, 'Key': obj['Key']},
                    ExpiresIn=DRAFT_PHOTO_VIEW_TTL_SECONDS,
                )
                photos.append(photo)
        photos.sort(key=itemgetter('filename'))
        return photos

    def presign_photo_upload(self, key, content_type):
        """As PhotosAdminUtil.presign_upload, into the draft's folder."""
        return self.s3.generate_presigned_url(
            'put_object',
            Params={'Bucket': BLOG_BUCKET, 'Key': key, 'ContentType': content_type},
            ExpiresIn=UPLOAD_URL_TTL_SECONDS,
        )

    def delete_photo(self, key):
        self.s3.delete_object(Bucket=BLOG_BUCKET, Key=key)

    def get_editing(self, draft_id):
        """What the draft's editing.json keeps about the published post it's
        changes to, or None if it's a draft of a new post."""
        text = self._read(BLOG_BUCKET, editing_key(draft_id))
        return json.loads(text) if text is not None else None

    def editing_summary(self, draft_id):
        """The published post the draft is changes to, as the admin page
        shows it: its key and slug. None for a draft of a new post."""
        editing = self.get_editing(draft_id)
        return {'key': editing['key'], 'slug': editing['slug']} if editing else None

    def edit_post(self, key):
        """A draft of changes to the post at `key` -- the one already being
        made, if there is one, so a post has at most one -- as (draft ID,
        whether it was just made). None if there's no post at `key`."""
        for obj in self._keys(DRAFTS_PREFIX):
            if not obj['Key'].endswith(f'/{EDITING_FILENAME}'):
                continue
            draft_id = obj['Key'][len(DRAFTS_PREFIX):].split('/')[0]
            editing = self.get_editing(draft_id)
            if editing and editing['key'] == key and self.get_draft(draft_id) is not None:
                return draft_id, False

        try:
            response = self.s3.get_object(Bucket=BLOG_BUCKET, Key=key)
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                return None
            raise
        fields, editing = draft_from_post(key, response['Body'].read().decode('utf-8', errors='ignore'))
        editing['etag'] = response['ETag']

        draft_id = new_draft_id()
        # editing.json first: a draft.md without it would be taken for a new
        # post's, if this stopped between the two.
        self.s3.put_object(
            Bucket=BLOG_BUCKET,
            Key=editing_key(draft_id),
            # default=str: YAML can parse frontmatter it doesn't know as dates.
            Body=json.dumps(editing, default=str).encode('utf-8'),
            ContentType='application/json',
        )
        self.save_draft(draft_id, build_markdown(fields))
        return draft_id, True

    def delete_draft(self, draft_id):
        """The draft and the photos uploaded to it."""
        keys = [{'Key': obj['Key']} for obj in self._keys(draft_prefix(draft_id))]
        # At most 1000 keys per request.
        for start in range(0, len(keys), 1000):
            self.s3.delete_objects(Bucket=BLOG_BUCKET, Delete={'Objects': keys[start:start + 1000], 'Quiet': True})

    def publish(self, draft_id, plan, existing_posts, editing=None):
        """Publish the draft as `plan` (from utils/draft_util.plan_publish)
        lays out, then delete it. Raises PublishConflict, before writing
        anything, if that would overwrite a post, or a different photo than
        the draft's, or if a post on another day has its slug (the newer
        would hide the older). A photo already published as the draft's
        (if an earlier attempt stopped part way) isn't a conflict.

        A draft of changes to a post (`editing`, from get_editing) overwrites
        just that post, and only if it hasn't changed since the draft was
        made from it -- e.g. by a hand upload, which this would undo."""
        if editing:
            current = self._etag(BLOG_BUCKET, editing['key'])
            if current is not None and current != editing['etag']:
                raise PublishConflict(
                    'The published post has changed since these changes were started from it, so publishing them '
                    'would undo that. Discard them, and edit the post again.'
                )
            existing_posts = [post for post in existing_posts if post['key'] != editing['key']]
        if any(post['key'] == plan['key'] for post in existing_posts):
            raise PublishConflict(f'There\'s already a post at {plan["key"]}. Change the title or date.')
        same_slug = next((post for post in existing_posts if post['slug'] == plan['slug']), None)
        if same_slug:
            raise PublishConflict(
                f'"{same_slug["title"]}" ({same_slug["date"] or same_slug["key"]}) already has the URL '
                f'/blog/{plan["slug"]}. Change the title.'
            )

        etags = {staged: self._etag(BLOG_BUCKET, staged) for staged in plan['photos']}
        taken = []
        for staged, published in plan['photos'].items():
            existing = self._etag(PHOTOS_BUCKET, published)
            if existing is not None and existing != etags[staged]:
                taken.append(published)
        if taken:
            raise PublishConflict(
                'These photos would replace different ones already on the site: '
                + ', '.join(taken) + '. Rename them, or change the date.'
            )

        for staged, published in plan['photos'].items():
            self.s3.copy_object(
                Bucket=PHOTOS_BUCKET,
                Key=published,
                CopySource={'Bucket': BLOG_BUCKET, 'Key': staged},
                ContentType=PHOTO_CONTENT_TYPE,
                MetadataDirective='REPLACE',
            )
        self.s3.put_object(
            Bucket=BLOG_BUCKET,
            Key=plan['key'],
            Body=plan['markdown'].encode('utf-8'),
            ContentType='text/markdown; charset=utf-8',
        )
        self.delete_draft(draft_id)
