import json
import os
from datetime import datetime

REPO_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..')

# Local stand-ins for the site's buckets and tables, all kept together at
# the repo root (see sample-data/README.md).
SAMPLE_DATA_DIR = os.path.join(REPO_ROOT, 'sample-data')
BOOKS_DYNAMO_DIR = os.path.join(SAMPLE_DATA_DIR, 'books', 'dynamo')
BOOKS_MARKDOWN_DIR = os.path.join(SAMPLE_DATA_DIR, 'books', 'markdown')
BOOKS_COVERS_DIR = os.path.join(SAMPLE_DATA_DIR, 'books', 'covers')
PHOTOS_TABLE_FILE = os.path.join(SAMPLE_DATA_DIR, 'photos', 'photos.json')
PHOTO_ORIGINALS_DIR = os.path.join(SAMPLE_DATA_DIR, 'photos', 'originals')
PHOTO_THUMBNAILS_DIR = os.path.join(SAMPLE_DATA_DIR, 'photos', 'thumbnails')
POSTS_DIR = os.path.join(SAMPLE_DATA_DIR, 'posts')


class LocalDynamoUtil:
    def _load_photos(self):
        # Re-read on every request, so photos that
        # ContentManagement/UpdatePhotoMetadata/run_local.py adds show up
        # without restarting the server.
        with open(PHOTOS_TABLE_FILE, encoding='utf-8') as f:
            return json.load(f)

    def get_photos(self, species=None, family=None, order=None, year=None, month=None, day=None, limit=50):
        photos = self._load_photos()
        date_prefix = day or month or year
        if species:
            photos = [p for p in photos if p.get('species') == species]
        elif family:
            photos = [p for p in photos if p.get('family') == family]
        elif order:
            photos = [p for p in photos if p.get('order') == order]
        elif date_prefix:
            photos = [p for p in photos if p.get('date', '').startswith(date_prefix)]
        return photos[:limit]

    def get_photo_by_id(self, photo_id):
        for photo in self._load_photos():
            if photo.get('s3_uri') == photo_id:
                return photo
        return None

    def get_all_species(self):
        return sorted(set(p['species'] for p in self._load_photos() if 'species' in p))

    def get_taxonomy(self):
        tree = {}
        for photo in self._load_photos():
            class_name = photo.get('class') or 'Unknown Class'
            order = photo.get('order') or 'Unknown Order'
            family = photo.get('family') or 'Unknown Family'
            species = photo.get('species') or 'Unknown Species'

            class_node = tree.setdefault(class_name, {'count': 0, 'orders': {}})
            order_node = class_node['orders'].setdefault(order, {'count': 0, 'families': {}})
            family_node = order_node['families'].setdefault(family, {'count': 0, 'species': {}})
            species_node = family_node['species'].setdefault(species, {'count': 0, 'thumbnails': []})

            class_node['count'] += 1
            order_node['count'] += 1
            family_node['count'] += 1
            species_node['count'] += 1
            if len(species_node['thumbnails']) < 3:
                species_node['thumbnails'].append(photo['s3_uri'])

        return tree

    def get_books(self, limit=50):
        # Reads straight from sample-data/books/dynamo at the repo root --
        # the same items the UpdateBookReview lambda writes to DynamoDB --
        # rather than re-deriving them from markdown, so local dev sees
        # exactly what production would store (cover, genres, synopsis
        # included) instead of a re-parsed approximation.
        books = []
        if os.path.exists(BOOKS_DYNAMO_DIR):
            for filename in os.listdir(BOOKS_DYNAMO_DIR):
                if not filename.endswith('.json'):
                    continue
                with open(os.path.join(BOOKS_DYNAMO_DIR, filename), encoding='utf-8') as f:
                    books.append(json.load(f))
        books.sort(key=lambda b: b.get('date', 0), reverse=True)
        return books[:limit]

    def get_book_by_title(self, title):
        for book in self.get_books(limit=10000):
            if book.get('title') == title:
                return book
        return None


class LocalS3Util:
    def list_posts(self):
        from utils.response_util import parse_post_metadata, extract_preview
        posts = []
        if os.path.exists(POSTS_DIR):
            for dirpath, _, filenames in os.walk(POSTS_DIR):
                for filename in filenames:
                    if not filename.endswith('.md'):
                        continue
                    filepath = os.path.join(dirpath, filename)
                    key = os.path.relpath(filepath, POSTS_DIR).replace(os.sep, '/')
                    meta = parse_post_metadata(key)
                    meta['key'] = key
                    meta['last_modified'] = datetime.fromtimestamp(os.path.getmtime(filepath)).isoformat()
                    with open(filepath, encoding='utf-8') as f:
                        meta['preview'] = extract_preview(f.read(600))
                    posts.append(meta)
        posts.sort(key=lambda p: (p['date'] or ''), reverse=True)
        return posts

    def get_post_content(self, key):
        local_path = os.path.join(POSTS_DIR, *key.split('/'))
        with open(local_path) as f:
            return f.read()


class LocalBooksAdminUtil:
    """Local stand-in for BooksAdminUtil. Writes the generated markdown into
    sample-data/books/markdown (same place a real S3 upload would land, per
    ContentManagement/UpdateBookReview/run_local.py's LOCAL_MODE convention),
    and also synthesizes the DynamoDB item directly -- there's no local
    equivalent of the S3-triggered UpdateBookReview lambda actually running,
    so without this the admin form would have nothing to show for a
    submission until someone manually re-runs that lambda's own run_local.py.
    Cover/genre/synopsis enrichment is skipped, matching how it's already
    best-effort/absent-on-failure in production."""

    def publish_book_review(self, title, markdown, payload):
        os.makedirs(BOOKS_MARKDOWN_DIR, exist_ok=True)
        with open(os.path.join(BOOKS_MARKDOWN_DIR, f'{title}.md'), 'w', encoding='utf-8') as f:
            f.write(markdown)

        os.makedirs(BOOKS_DYNAMO_DIR, exist_ok=True)
        item = _payload_to_local_item(title, payload)
        with open(os.path.join(BOOKS_DYNAMO_DIR, f'{title}.json'), 'w', encoding='utf-8') as f:
            json.dump(item, f, indent=2, ensure_ascii=False)


# Served by run_local.py, standing in for a presigned S3 PUT URL.
LOCAL_UPLOAD_ROUTE = 'local-s3/photos'


class LocalPhotosAdminUtil:
    """Local stand-in for PhotosAdminUtil, treating sample-data/photos/originals
    (what run_local.py's CDN stand-in serves) as the bucket. There's no local S3
    trigger, so uploads only show up in the gallery once
    ContentManagement/UpdatePhotoMetadata/run_local.py processes them."""

    def list_folder(self, prefix):
        folder_dir = os.path.join(PHOTO_ORIGINALS_DIR, *prefix.split('/'))
        if not os.path.isdir(folder_dir):
            return [], []

        folders, photos = [], []
        for name in sorted(os.listdir(folder_dir)):
            path = os.path.join(folder_dir, name)
            if os.path.isdir(path):
                folders.append(name)
            else:
                photos.append({
                    'name': name,
                    's3_uri': f's3://spark.wiki.photos/{prefix}{name}',
                    'size': os.path.getsize(path),
                    'last_modified': datetime.fromtimestamp(os.path.getmtime(path)).isoformat(),
                })
        return folders, photos

    def create_folder(self, prefix):
        os.makedirs(os.path.join(PHOTO_ORIGINALS_DIR, *prefix.split('/')), exist_ok=True)

    def presign_upload(self, key, content_type):
        from urllib.parse import quote
        from flask import request
        return f'{request.host_url}{LOCAL_UPLOAD_ROUTE}/{quote(key)}'


def _payload_to_local_item(title, payload):
    date_reviewed = payload.get('date_reviewed', '') or ''
    digits = date_reviewed.replace('-', '')
    date_number = int(digits) if digits.isdigit() else 0

    rating_elements = [
        {'name': el['name'], 'weight': el['weight'], 'rating': el['rating']}
        for el in payload['rating_elements']
    ]

    commentary = []
    overall_review = (payload.get('overall_review') or '').strip()
    if overall_review:
        commentary.append({'text': overall_review})
    for entry in sorted(payload.get('commentary') or [], key=lambda e: e['point']):
        commentary.append({'text': entry['text'].strip(), 'point': entry['point']})

    return {
        'title': title,
        'date': date_number,
        'date_reviewed': date_reviewed,
        'author': payload.get('author', ''),
        's3_uri': f's3://spark.wiki.books/{title}.md',
        'rating_elements': rating_elements,
        'commentary': commentary,
    }

