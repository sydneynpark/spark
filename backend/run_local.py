import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
os.environ['LOCAL_MODE'] = 'true'

from flask import abort, request, send_from_directory
from werkzeug.security import safe_join
from lambda_function import app
from utils.local_util import BOOKS_COVERS_DIR, LOCAL_UPLOAD_ROUTE, PHOTO_ORIGINALS_DIR, PHOTO_THUMBNAILS_DIR

# Stand-in for the photos.spark.wiki CDN, mirroring its URL structure
# (/<key> for full-size, /thumbnail/<key> for thumbnails) against local files.
@app.route('/cdn/thumbnail/<path:key>')
def local_thumbnail(key):
    return send_from_directory(PHOTO_THUMBNAILS_DIR, key)

@app.route('/cdn/<path:key>')
def local_photo(key):
    return send_from_directory(PHOTO_ORIGINALS_DIR, key)

# Stand-in for the presigned S3 PUT URLs the admin photo upload hands out
# (see LocalPhotosAdminUtil), writing into the sample-data/photos/originals
# served above.
@app.route(f'/{LOCAL_UPLOAD_ROUTE}/<path:key>', methods=['PUT'])
def local_photo_upload(key):
    path = safe_join(PHOTO_ORIGINALS_DIR, key)
    if path is None:
        abort(400)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'wb') as f:
        f.write(request.get_data())
    return '', 200

# Stand-in for the covers CDN in front of spark.wiki.books/covers, against
# the same sample-data/books/covers the UpdateBookReview lambda writes to
# S3 (see ContentManagement/UpdateBookReview/run_local.py).
@app.route('/cdn/books/covers/<path:filename>')
def local_book_cover(filename):
    return send_from_directory(BOOKS_COVERS_DIR, filename)

if __name__ == '__main__':
    print('Starting local API server at http://localhost:5000')
    app.run(debug=True, port=5000, host='0.0.0.0')
