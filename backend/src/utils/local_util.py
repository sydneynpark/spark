import json
import os
from datetime import datetime

LOCAL_DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'local_data')


class LocalDynamoUtil:
    def __init__(self):
        data_file = os.path.join(LOCAL_DATA_DIR, 'photos.json')
        with open(data_file) as f:
            self._photos = json.load(f)

    def get_photos(self, species=None, family=None, order=None, limit=50):
        photos = self._photos
        if species:
            photos = [p for p in photos if p.get('species') == species]
        elif family:
            photos = [p for p in photos if p.get('family') == family]
        elif order:
            photos = [p for p in photos if p.get('order') == order]
        return photos[:limit]

    def get_photo_by_id(self, photo_id):
        for photo in self._photos:
            if photo.get('s3_uri') == photo_id:
                return photo
        return None

    def get_all_species(self):
        return sorted(set(p['species'] for p in self._photos if 'species' in p))


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

    def get_image(self, bucket, key):
        local_path = os.path.join(LOCAL_DATA_DIR, 'thumbnails', key)
        if os.path.exists(local_path):
            with open(local_path, 'rb') as f:
                return f.read(), 'image/jpeg'
        # Return a gray SVG placeholder when no local file exists
        svg = (
            '<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200">'
            '<rect width="200" height="200" fill="#d0d0d0"/>'
            '<text x="50%" y="50%" text-anchor="middle" dy=".3em" '
            'font-family="sans-serif" font-size="14" fill="#888">No Image</text>'
            '</svg>'
        )
        return svg.encode(), 'image/svg+xml'

    def generate_presigned_url(self, bucket, key, expiration=3600):
        # No real S3 in local mode; signal caller to fall back to thumbnail proxy
        return None
