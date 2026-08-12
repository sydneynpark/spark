import json
import os
from datetime import datetime

LOCAL_DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'local_data')
REPO_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..')

BOOKS_DYNAMO_DIR = os.path.join(REPO_ROOT, 'sample-data', 'books', 'dynamo')


class LocalDynamoUtil:
    def __init__(self):
        data_file = os.path.join(LOCAL_DATA_DIR, 'photos.json')
        with open(data_file) as f:
            self._photos = json.load(f)

    def get_photos(self, species=None, family=None, order=None, year=None, month=None, day=None, limit=50):
        photos = self._photos
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
        for photo in self._photos:
            if photo.get('s3_uri') == photo_id:
                return photo
        return None

    def get_all_species(self):
        return sorted(set(p['species'] for p in self._photos if 'species' in p))

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
        posts_dir = os.path.join(LOCAL_DATA_DIR, 'posts')
        posts = []
        if os.path.exists(posts_dir):
            for dirpath, _, filenames in os.walk(posts_dir):
                for filename in filenames:
                    if not filename.endswith('.md'):
                        continue
                    filepath = os.path.join(dirpath, filename)
                    key = os.path.relpath(filepath, posts_dir).replace(os.sep, '/')
                    meta = parse_post_metadata(key)
                    meta['key'] = key
                    meta['last_modified'] = datetime.fromtimestamp(os.path.getmtime(filepath)).isoformat()
                    with open(filepath, encoding='utf-8') as f:
                        meta['preview'] = extract_preview(f.read(600))
                    posts.append(meta)
        posts.sort(key=lambda p: (p['date'] or ''), reverse=True)
        return posts

    def get_post_content(self, key):
        local_path = os.path.join(LOCAL_DATA_DIR, 'posts', *key.split('/'))
        with open(local_path) as f:
            return f.read()

