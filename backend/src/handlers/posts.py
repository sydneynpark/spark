from flask import Blueprint, jsonify
from utils.response_util import handle_error

from utils.aws_util import DynamoUtil, S3Util

posts_bp = Blueprint('posts', __name__)
dynamo = DynamoUtil()
s3_util = S3Util()

@posts_bp.route('/posts', methods=['GET'])
def list_posts():
    try:
        posts = dynamo.get_posts()
        return jsonify({'posts': posts})
    except Exception as e:
        return handle_error(e)

@posts_bp.route('/posts/<slug>', methods=['GET'])
def get_post(slug):
    """Get a single post by its slug, which the posts table finds it by (if
    two share a slug, the newer one wins). The post itself is read as it is
    now, rather than as the table last had it."""
    try:
        found = dynamo.get_post_by_slug(slug)
        post = s3_util.get_post(found['key']) if found else None
        if not post:
            return jsonify({'error': 'Post not found'}), 404
        return jsonify(post)
    except Exception as e:
        return handle_error(e)
