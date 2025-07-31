from flask import Blueprint, jsonify
from utils.response_util import handle_error

posts_bp = Blueprint('posts', __name__)

@posts_bp.route('/posts', methods=['GET'])
def list_posts():
    """Placeholder for blog posts - coming soon"""
    return jsonify({
        'message': 'Blog posts feature coming soon!',
        'posts': []
    })

@posts_bp.route('/posts/<post_id>', methods=['GET'])
def get_post(post_id):
    """Placeholder for individual blog post"""
    return jsonify({
        'message': 'Blog posts feature coming soon!',
        'post_id': post_id
    })