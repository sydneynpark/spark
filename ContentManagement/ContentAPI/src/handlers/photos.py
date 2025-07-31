from flask import Blueprint, jsonify, request
from utils.aws_util import DynamoUtil
from utils.response_util import handle_error

photos_bp = Blueprint('photos', __name__)
dynamo = DynamoUtil()

@photos_bp.route('/photos', methods=['GET'])
def list_photos():
    """List all photos with metadata and taxonomy"""
    try:
        # Get query parameters for filtering
        species = request.args.get('species')
        family = request.args.get('family')
        order = request.args.get('order')
        limit = int(request.args.get('limit', 50))
        
        photos = dynamo.get_photos(
            species=species,
            family=family, 
            order=order,
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