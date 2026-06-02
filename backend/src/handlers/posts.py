import os
import base64
from flask import Blueprint, jsonify
from utils.response_util import handle_error, parse_post_metadata

if os.getenv('LOCAL_MODE') == 'true':
    from utils.local_util import LocalS3Util as S3Util
else:
    from utils.aws_util import S3Util

posts_bp = Blueprint('posts', __name__)
s3_util = S3Util()

@posts_bp.route('/posts', methods=['GET'])
def list_posts():
    try:
        posts = s3_util.list_posts()
        return jsonify({'posts': posts})
    except Exception as e:
        return handle_error(e)

@posts_bp.route('/posts/<post_id_encoded>', methods=['GET'])
def get_post(post_id_encoded):
    try:
        key = base64.b64decode(post_id_encoded).decode('utf-8')
        content = s3_util.get_post_content(key)
        meta = parse_post_metadata(key)
        return jsonify({
            'content': content,
            'title': meta['title'],
            'date': meta['date'],
            'key': key,
        })
    except Exception as e:
        return handle_error(e)
