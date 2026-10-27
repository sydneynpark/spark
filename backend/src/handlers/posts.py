from flask import Blueprint, jsonify
from utils.response_util import handle_error

from utils.aws_util import S3Util

posts_bp = Blueprint('posts', __name__)
s3_util = S3Util()

@posts_bp.route('/posts', methods=['GET'])
def list_posts():
    try:
        posts = [{k: v for k, v in post.items() if k != 'content'} for post in s3_util.list_posts()]
        return jsonify({'posts': posts})
    except Exception as e:
        return handle_error(e)

@posts_bp.route('/posts/<slug>', methods=['GET'])
def get_post(slug):
    """Get a single post by its slug. Posts aren't indexed by slug, so this
    looks through all of them; if two share a slug, the newer one wins."""
    try:
        post = next((p for p in s3_util.list_posts() if p['slug'] == slug), None)
        if not post:
            return jsonify({'error': 'Post not found'}), 404
        return jsonify(post)
    except Exception as e:
        return handle_error(e)
