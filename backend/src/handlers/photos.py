from flask import Blueprint, jsonify, request, Response
from utils.aws_util import DynamoUtil, S3Util
from utils.response_util import handle_error, create_cors_response
import base64
import urllib.parse

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

@photos_bp.route('/photos/thumbnail/<path:s3_uri_encoded>', methods=['GET', 'OPTIONS'])
def get_photo_thumbnail(s3_uri_encoded):
    """Get photo thumbnail by proxying from S3"""
    # Handle preflight OPTIONS request
    if request.method == 'OPTIONS':
        response = Response()
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Requested-With'
        return response
    try:
        # Decode the base64-encoded S3 URI
        try:
            s3_uri = base64.b64decode(s3_uri_encoded.encode()).decode('utf-8')
            print(f'Decoded S3 URI: {s3_uri}')
        except Exception as decode_error:
            print(f'Base64 decode error: {decode_error}')
            return create_cors_response({'error': 'Invalid base64 encoding'}, 400)
        
        # Parse S3 URI
        if not s3_uri.startswith('s3://'):
            print(f'Invalid S3 URI format: {s3_uri}')
            return create_cors_response({'error': 'Invalid S3 URI format'}, 400)
            
        # Extract bucket and key from s3://bucket/key format
        s3_path = s3_uri[5:]  # Remove 's3://'
        if '/' not in s3_path:
            print(f'Invalid S3 path: {s3_path}')
            return create_cors_response({'error': 'Invalid S3 path'}, 400)
            
        bucket, key = s3_path.split('/', 1)
        print(f'Fetching from bucket: {bucket}, key: {key}')
        
        # Get image from S3
        image_data, content_type = s3_util.get_image(bucket, key)
        
        if not image_data:
            print('No image data returned from S3')
            return create_cors_response({'error': 'Image not found'}, 404)
            
        print(f'Image data length: {len(image_data)}, content type: {content_type}')
            
        # Return image as binary response with explicit CORS headers
        response = Response(
            image_data,
            mimetype=content_type or 'image/jpeg'
        )
        
        # Add CORS headers explicitly
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Requested-With'
        response.headers['Cache-Control'] = 'public, max-age=3600'
        response.headers['X-Image-Size'] = str(len(image_data))
        response.headers['X-Debug-Status'] = 'success'
        
        return response
        
    except Exception as e:
        print(f'Error serving thumbnail: {str(e)}')
        return handle_error(e)