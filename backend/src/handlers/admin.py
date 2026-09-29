import os
import time

from flask import Blueprint, jsonify, request

from utils.auth_util import verify_credentials, issue_token, require_admin_auth, TOKEN_TTL_SECONDS
from utils.book_review_builder import validate_review_payload, build_review_markdown
from utils.response_util import handle_error, convert_decimals
from utils.rating_util import add_star_rating

if os.getenv('LOCAL_MODE') == 'true':
    from utils.local_util import LocalDynamoUtil as DynamoUtil
    from utils.local_util import LocalBooksAdminUtil as BooksAdminUtil
else:
    from utils.aws_util import DynamoUtil, BooksAdminUtil

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')
dynamo = DynamoUtil()
books_admin = BooksAdminUtil()


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
    lambda's S3 trigger takes it from there (enrichment + DynamoDB write)."""
    try:
        payload = request.get_json(silent=True) or {}
        error = validate_review_payload(payload)
        if error:
            return jsonify({'error': error}), 400

        title = payload['title'].strip()
        markdown = build_review_markdown(payload)
        books_admin.publish_book_review(title, markdown, payload)

        book = _await_book(title)
        if book:
            return jsonify({'status': 'published', 'book': add_star_rating(convert_decimals(book))}), 201
        return jsonify({
            'status': 'processing',
            'message': f'"{title}" was uploaded and is being processed. It should appear on the site shortly.',
        }), 202
    except Exception as e:
        return handle_error(e)


def _await_book(title, attempts=4, delay_seconds=1.5):
    """Give the S3-triggered UpdateBookReview lambda a few seconds to finish
    before responding, so the admin gets immediate confirmation instead of
    always seeing "processing" (the first attempt succeeds immediately in
    LOCAL_MODE, since LocalBooksAdminUtil writes the item synchronously)."""
    for attempt in range(attempts):
        book = dynamo.get_book_by_title(title)
        if book:
            return book
        if attempt < attempts - 1:
            time.sleep(delay_seconds)
    return None
