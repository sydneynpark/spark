
from flask import Blueprint, jsonify, request

from utils.auth_util import verify_credentials, issue_token, require_admin_auth, TOKEN_TTL_SECONDS
from utils.book_review_builder import validate_review_payload, build_review_markdown
from utils.draft_util import (
    DraftError, build_markdown, draft_fields, draft_photo, draft_photo_key, is_draft_id,
    new_draft_id, plan_publish,
)
from utils.photo_upload_util import (
    PHOTO_COLLECTIONS, PHOTO_CONTENT_TYPE, UploadPathError, accepts_uploads, child_folder_kind,
    new_folder_prefix, photo_key, validate_prefix,
)
from utils.response_util import handle_error

from utils.aws_util import BooksAdminUtil, DraftsAdminUtil, PhotosAdminUtil, PublishConflict, S3Util

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')
books_admin = BooksAdminUtil()
photos_admin = PhotosAdminUtil()
drafts_admin = DraftsAdminUtil()
posts = S3Util()


# The photo endpoints work in either photo collection's folder of the photos
# bucket, named by `collection`: 'birds' or 'photos'. Their folder paths are
# within it.
def unknown_collection(collection):
    return jsonify({'error': f'Unknown photo collection: {collection!r}'}), 400


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
    """One folder of a photo collection: its subfolders and photos, plus what
    the YYYY/MM/DD/ layout allows here -- which kind of folder can be
    created inside it, and whether photos can be uploaded into it."""
    try:
        collection = request.args.get('collection')
        if collection not in PHOTO_COLLECTIONS:
            return unknown_collection(collection)
        prefix = request.args.get('prefix', '')
        error = validate_prefix(prefix)
        if error:
            return jsonify({'error': error}), 400

        folders, photos = photos_admin.list_folder(collection, prefix)
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
        collection = data.get('collection')
        if collection not in PHOTO_COLLECTIONS:
            return unknown_collection(collection)
        try:
            prefix = new_folder_prefix(data.get('parent', ''), data.get('name', ''))
        except UploadPathError as e:
            return jsonify({'error': str(e)}), 400

        photos_admin.create_folder(collection, prefix)
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
        collection = data.get('collection')
        if collection not in PHOTO_COLLECTIONS:
            return unknown_collection(collection)
        try:
            key = PHOTO_COLLECTIONS[collection] + photo_key(data.get('folder', ''), data.get('filename', ''))
        except UploadPathError as e:
            return jsonify({'error': str(e)}), 400

        return jsonify({
            'key': key,
            'url': photos_admin.presign_upload(key, PHOTO_CONTENT_TYPE),
            'headers': {'Content-Type': PHOTO_CONTENT_TYPE},
        })
    except Exception as e:
        return handle_error(e)


# Blog post drafts (utils/draft_util.py), each named by its ID.
def draft_not_found():
    return jsonify({'error': 'No such draft. It may have been published or deleted.'}), 404


@admin_bp.route('/drafts', methods=['GET'])
@require_admin_auth
def list_drafts():
    try:
        return jsonify({'drafts': drafts_admin.list_drafts()})
    except Exception as e:
        return handle_error(e)


@admin_bp.route('/drafts', methods=['POST'])
@require_admin_auth
def create_draft():
    try:
        try:
            fields = draft_fields(request.get_json(silent=True) or {})
        except DraftError as e:
            return jsonify({'error': str(e)}), 400
        draft_id = new_draft_id()
        drafts_admin.save_draft(draft_id, build_markdown(fields))
        return jsonify({'id': draft_id, **fields}), 201
    except Exception as e:
        return handle_error(e)


@admin_bp.route('/drafts/<draft_id>', methods=['GET'])
@require_admin_auth
def get_draft(draft_id):
    try:
        fields = drafts_admin.get_draft(draft_id) if is_draft_id(draft_id) else None
        if fields is None:
            return draft_not_found()
        return jsonify({'id': draft_id, **fields})
    except Exception as e:
        return handle_error(e)


@admin_bp.route('/drafts/<draft_id>', methods=['PUT'])
@require_admin_auth
def save_draft(draft_id):
    try:
        if not is_draft_id(draft_id) or drafts_admin.get_draft(draft_id) is None:
            return draft_not_found()
        try:
            fields = draft_fields(request.get_json(silent=True) or {})
        except DraftError as e:
            return jsonify({'error': str(e)}), 400
        drafts_admin.save_draft(draft_id, build_markdown(fields))
        return jsonify({'id': draft_id, **fields})
    except Exception as e:
        return handle_error(e)


@admin_bp.route('/drafts/<draft_id>', methods=['DELETE'])
@require_admin_auth
def delete_draft(draft_id):
    """The draft, and the photos uploaded to it, none of which are on the
    site yet."""
    try:
        if not is_draft_id(draft_id):
            return draft_not_found()
        drafts_admin.delete_draft(draft_id)
        return '', 204
    except Exception as e:
        return handle_error(e)


@admin_bp.route('/drafts/<draft_id>/photos', methods=['GET'])
@require_admin_auth
def list_draft_photos(draft_id):
    try:
        if not is_draft_id(draft_id):
            return draft_not_found()
        return jsonify({'photos': drafts_admin.list_photos(draft_id)})
    except Exception as e:
        return handle_error(e)


@admin_bp.route('/drafts/<draft_id>/photos/upload-url', methods=['POST'])
@require_admin_auth
def create_draft_photo_upload_url(draft_id):
    """As /photos/upload-url, but into the draft, until it's published."""
    try:
        if not is_draft_id(draft_id) or drafts_admin.get_draft(draft_id) is None:
            return draft_not_found()
        data = request.get_json(silent=True) or {}
        collection = data.get('collection')
        if collection not in PHOTO_COLLECTIONS:
            return unknown_collection(collection)
        try:
            key = draft_photo_key(draft_id, collection, data.get('filename', ''))
        except UploadPathError as e:
            return jsonify({'error': str(e)}), 400

        return jsonify({
            **draft_photo(draft_id, key),
            'url': drafts_admin.presign_photo_upload(key, PHOTO_CONTENT_TYPE),
            'headers': {'Content-Type': PHOTO_CONTENT_TYPE},
        })
    except Exception as e:
        return handle_error(e)


@admin_bp.route('/drafts/<draft_id>/photos', methods=['DELETE'])
@require_admin_auth
def delete_draft_photo(draft_id):
    """One of the draft's photos, named by its `key`."""
    try:
        if not is_draft_id(draft_id):
            return draft_not_found()
        key = request.args.get('key', '')
        if not draft_photo(draft_id, key):
            return jsonify({'error': f'Not a photo in this draft: {key!r}'}), 400
        drafts_admin.delete_photo(key)
        return '', 204
    except Exception as e:
        return handle_error(e)


@admin_bp.route('/drafts/<draft_id>/publish', methods=['POST'])
@require_admin_auth
def publish_draft(draft_id):
    """Publish the draft as last saved: its photos to their collections, in
    the folder for the post's date, where UpdatePhotoMetadata processes them,
    and the post to the blog bucket, where the site reads it straight away.
    The draft is deleted once it's published."""
    try:
        fields = drafts_admin.get_draft(draft_id) if is_draft_id(draft_id) else None
        if fields is None:
            return draft_not_found()
        photos = drafts_admin.list_photos(draft_id)
        try:
            plan = plan_publish(draft_id, fields, [photo['key'] for photo in photos])
            drafts_admin.publish(draft_id, plan, posts.list_posts())
        except (DraftError, UploadPathError) as e:
            return jsonify({'error': str(e)}), 400
        except PublishConflict as e:
            return jsonify({'error': str(e)}), 409

        return jsonify({
            'key': plan['key'],
            'slug': plan['slug'],
            'photos': sorted(plan['photos'].values()),
        })
    except Exception as e:
        return handle_error(e)
