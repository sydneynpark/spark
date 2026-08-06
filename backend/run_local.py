import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
os.environ['LOCAL_MODE'] = 'true'

# Keyless requests to Google Books get a shared anonymous quota of zero, so
# cover lookups need a real API key. Read it from the same gitignored local
# file deploy.py uses, rather than requiring it to be exported by hand.
GOOGLE_BOOKS_API_KEY_FILE = os.path.join(os.path.dirname(__file__), '..', 'scripts', '.googlebooksapikey')
if os.path.exists(GOOGLE_BOOKS_API_KEY_FILE):
    with open(GOOGLE_BOOKS_API_KEY_FILE, encoding='utf-8') as f:
        os.environ['GOOGLE_BOOKS_API_KEY'] = f.read().strip()
else:
    print(f'No Google Books API key found at {GOOGLE_BOOKS_API_KEY_FILE} -- book covers will not load.')

from flask import send_from_directory
from lambda_function import app

LOCAL_DATA_DIR = os.path.join(os.path.dirname(__file__), 'local_data')

# Stand-in for the photos.spark.wiki CDN, mirroring its URL structure
# (/<key> for full-size, /thumbnail/<key> for thumbnails) against local files.
@app.route('/cdn/thumbnail/<path:key>')
def local_thumbnail(key):
    return send_from_directory(os.path.join(LOCAL_DATA_DIR, 'thumbnails'), key)

@app.route('/cdn/<path:key>')
def local_photo(key):
    return send_from_directory(os.path.join(LOCAL_DATA_DIR, 'photos'), key)

# Stand-in for the covers CDN in front of spark.wiki.books/covers, against
# the disk-cached covers LocalDynamoUtil fetches from Open Library.
@app.route('/cdn/books/covers/<path:filename>')
def local_book_cover(filename):
    return send_from_directory(os.path.join(LOCAL_DATA_DIR, 'covers'), filename)

if __name__ == '__main__':
    print('Starting local API server at http://localhost:5000')
    app.run(debug=True, port=5000, host='0.0.0.0')
