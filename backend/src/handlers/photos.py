import os
from flask import Blueprint, jsonify, request
from utils.response_util import handle_error

if os.getenv('LOCAL_MODE') == 'true':
    from utils.local_util import LocalDynamoUtil as DynamoUtil, LocalS3Util as S3Util
else:
    from utils.aws_util import DynamoUtil, S3Util

photos_bp = Blueprint('photos', __name__)
dynamo = DynamoUtil()
s3_util = S3Util()

@photos_bp.route('/photos', methods=['GET'])
def list_photos():
    """List all photos with metadata and taxonomy"""
    try:
        # Get query parameters for filtering
        species = request.args.get('species')
        family = request.args.get('family')
        order = request.args.get('order')
        year = request.args.get('year')
        month = request.args.get('month')
        day = request.args.get('day')
        limit_param = request.args.get('limit')
        limit = int(limit_param) if limit_param else None

        photos = dynamo.get_photos(
            species=species,
            family=family,
            order=order,
            year=year,
            month=month,
            day=day,
            limit=limit
        )
        
        return jsonify({
            'photos': photos,
            'count': len(photos)
        })
        
    except Exception as e:
        return handle_error(e)

@photos_bp.route('/photos/<photo_id>', methods=['GET'])
def get_photo(photo_id):
    """Get specific photo details by S3 URI"""
    try:
        # photo_id will be the S3 URI (base64 encoded or similar)
        photo = dynamo.get_photo_by_id(photo_id)
        
        if not photo:
            return jsonify({'error': 'Photo not found'}), 404
            
        return jsonify(photo)
        
    except Exception as e:
        return handle_error(e)

@photos_bp.route('/photos/taxonomy', methods=['GET'])
def get_taxonomy():
    """Get the class > order > family > species browse tree, with counts
    and sample thumbnails per species"""
    try:
        taxonomy = dynamo.get_taxonomy()
        return jsonify({'taxonomy': taxonomy})

    except Exception as e:
        return handle_error(e)

@photos_bp.route('/photos/species', methods=['GET'])
def list_species():
    """Get list of all species found in photos"""
    try:
        species_list = dynamo.get_all_species()
        return jsonify({
            'species': species_list,
            'count': len(species_list)
        })
        
    except Exception as e:
        return handle_error(e)