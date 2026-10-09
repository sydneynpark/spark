import os

from flask import Blueprint, jsonify, request

from utils.auth_util import verify_credentials, issue_token, require_admin_auth, TOKEN_TTL_SECONDS
from utils.book_review_builder import validate_review_payload, build_review_markdown
from utils.photo_upload_util import (
    PHOTO_CONTENT_TYPE, UploadPathError, accepts_uploads, child_folder_kind,
    new_folder_prefix, photo_key, validate_prefix,
)
from utils.response_util import handle_error

if os.getenv('LOCAL_MODE') == 'true':
    from utils.local_util import LocalBooksAdminUtil as BooksAdminUtil, LocalPhotosAdminUtil as PhotosAdminUtil
else:
    from utils.aws_util import BooksAdminUtil, PhotosAdminUtil

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')
books_admin = BooksAdminUtil()
photos_admin = PhotosAdminUtil()


@admin_bp.route('/login', methods=['POST'])
def login():
    """Exchange a username/password for a session token."""
    try:
        data = request.get_json(silent=True) or {}
        username = data.get('username', '')
        password = data.get('password', '')
        if not username or not password:
            return jsonify({'error': 'Username and password are required'}), 400
        if not verify_credentials(username, password):
            return jsonify({'error': 'Invalid username or password'}), 401
        return jsonify({'token': issue_token(username), 'expires_in': TOKEN_TTL_SECONDS})
    except Exception as e:
        return handle_error(e)


@admin_bp.route('/session', methods=['GET'])
@require_admin_auth
def session_check():
    """Lets the frontend confirm a stored token is still valid on load."""
    return jsonify({'authenticated': True})


@admin_bp.route('/book-reviews', methods=['POST'])
@require_admin_auth
def create_book_review():
    """Publish a new book review by uploading it as markdown to the same S3
    bucket a manual review upload would use -- the existing UpdateBookReview
    lambda's S3 trigger takes it from there (enrichment + DynamoDB write).
    That enrichment includes an LLM call, so this responds as soon as the
    upload succeeds rather than waiting for the review to land in DynamoDB."""
    try:
        payload = request.get_json(silent=True) or {}
        error = validate_review_payload(payload)
        if error:
            return jsonify({'error': error}), 400

        title = payload['title'].strip()
        markdown = build_review_markdown(payload)
        books_admin.publish_book_review(title, markdown, payload)

        return jsonify({
            'status': 'processing',
            'message': f'"{title}" was uploaded and is being processed. It should appear on the site shortly.',
        }), 202
    except Exception as e:
        return handle_error(e)


@admin_bp.route('/photos/folders', methods=['GET'])
@require_admin_auth
def list_photo_folder():
    """One folder of the photos bucket: its subfolders and photos, plus what
    the YYYY/MM/DD/ layout allows here -- which kind of folder can be
    created inside it, and whether photos can be uploaded into it."""
    try:
        prefix = request.args.get('prefix', '')
        error = validate_prefix(prefix)
        if error:
            return jsonify({'error': error}), 400

        folders, photos = photos_admin.list_folder(prefix)
        return jsonify({
            'prefix': prefix,
            'folders': folders,
            'photos': photos,
            'child_folder_kind': child_folder_kind(prefix),
            'accepts_uploads': accepts_uploads(prefix),
        })
    except Exception as e:
        return handle_error(e)


@admin_bp.route('/photos/folders', methods=['POST'])
@require_admin_auth
def create_photo_folder():
    """Create the next level of the date structure (a year, month, or day)
    inside `parent`. Creating one that already exists is harmless."""
    try:
        data = request.get_json(silent=True) or {}
        try:
            prefix = new_folder_prefix(data.get('parent', ''), data.get('name', ''))
        except UploadPathError as e:
            return jsonify({'error': str(e)}), 400

        photos_admin.create_folder(prefix)
        return jsonify({'prefix': prefix}), 201
    except Exception as e:
        return handle_error(e)


@admin_bp.route('/photos/upload-url', methods=['POST'])
@require_admin_auth
def create_photo_upload_url():
    """A short-lived URL to upload one photo straight to S3 with, requested
    per photo just before uploading it so a long batch can't outlive it."""
    try:
        data = request.get_json(silent=True) or {}
        try:
            key = photo_key(data.get('folder', ''), data.get('filename', ''))
        except UploadPathError as e:
            return jsonify({'error': str(e)}), 400

        return jsonify({
            'key': key,
            'url': photos_admin.presign_upload(key, PHOTO_CONTENT_TYPE),
            'headers': {'Content-Type': PHOTO_CONTENT_TYPE},
        })
    except Exception as e:
        return handle_error(e)

