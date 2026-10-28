from flask import Blueprint, jsonify, request
from utils.response_util import handle_error

from utils.aws_util import DynamoUtil

# The photos that aren't of birds (those are birds.py's), which only have
# dates, not taxonomy.
photos_bp = Blueprint('photos', __name__)
dynamo = DynamoUtil()

@photos_bp.route('/photos', methods=['GET'])
def list_photos():
    """List photos, optionally just those from a year (YYYY), month
    (YYYY-MM), or day (YYYY-MM-DD)"""
    try:
        limit_param = request.args.get('limit')
        photos = dynamo.get_photos(
            year=request.args.get('year'),
            month=request.args.get('month'),
            day=request.args.get('day'),
            limit=int(limit_param) if limit_param else None,
        )

        return jsonify({
            'photos': photos,
            'count': len(photos)
        })

    except Exception as e:
        return handle_error(e)
