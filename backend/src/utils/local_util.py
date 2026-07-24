import json
import os
from datetime import datetime

LOCAL_DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'local_data')
REPO_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..')


COVERS_DIR = os.path.join(LOCAL_DATA_DIR, 'covers')
COVER_MANIFEST_PATH = os.path.join(COVERS_DIR, '.manifest.json')


class LocalDynamoUtil:
    def __init__(self):
        data_file = os.path.join(LOCAL_DATA_DIR, 'photos.json')
        with open(data_file) as f:
            self._photos = json.load(f)
        self._cover_manifest = None

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
        from utils.book_review_parser import parse_book_review
        # Reads straight from sample-data/books at the repo root -- the same
        # files you'd upload to the spark.wiki.books S3 bucket -- rather than
        # a separate local copy, so local dev never drifts from what you're
        # actually about to publish.
        books_dir = os.path.join(REPO_ROOT, 'sample-data', 'books')
        books = []
        if os.path.exists(books_dir):
            for filename in os.listdir(books_dir):
                if not filename.endswith('.md'):
                    continue
                filepath = os.path.join(books_dir, filename)
                with open(filepath, encoding='utf-8') as f:
                    book = parse_book_review(f.read(), s3_uri=f's3://spark.wiki.books/{filename}')
                book['cover_key'] = self._get_cover_key(book['title'], book['author'])
                books.append(book)
        books.sort(key=lambda b: b.get('date', 0), reverse=True)
        return books[:limit]

    def _get_cover_key(self, title, author):
        # The UpdateBookReview lambda does this same lookup + download once
        # at upload time and stores the image in S3; local dev has no
        # lambda, so it does the same thing on first read instead, and
        # persists the result (success or failure) to disk in
        # local_data/covers so restarting the dev server never re-hits
        # Open Library for a book it's already resolved.
        manifest = self._load_cover_manifest()
        if title in manifest:
            return manifest[title]

        cover_key = None
        from utils.open_library_util import OpenLibraryUtil
        open_library = OpenLibraryUtil()
        cover_id = open_library.find_cover_id(title, author)
        if cover_id:
            image_bytes = open_library.fetch_cover_image(cover_id)
            if image_bytes:
                os.makedirs(COVERS_DIR, exist_ok=True)
                filename = f'{title}.jpg'
                with open(os.path.join(COVERS_DIR, filename), 'wb') as f:
                    f.write(image_bytes)
                cover_key = f'covers/{filename}'

        manifest[title] = cover_key
        self._save_cover_manifest(manifest)
        return cover_key

    def _load_cover_manifest(self):
        if self._cover_manifest is None:
            if os.path.exists(COVER_MANIFEST_PATH):
                with open(COVER_MANIFEST_PATH, encoding='utf-8') as f:
                    self._cover_manifest = json.load(f)
            else:
                self._cover_manifest = {}
        return self._cover_manifest

    def _save_cover_manifest(self, manifest):
        os.makedirs(COVERS_DIR, exist_ok=True)
        with open(COVER_MANIFEST_PATH, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, indent=2)

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

