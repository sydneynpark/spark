from flask import jsonify
from decimal import Decimal
import traceback

def convert_decimals(value):
    """Recursively convert DynamoDB Decimals into plain int/float so the
    result can be passed to jsonify."""
    if isinstance(value, Decimal):
        return int(value) if value % 1 == 0 else float(value)
    if isinstance(value, list):
        return [convert_decimals(v) for v in value]
    if isinstance(value, dict):
        return {k: convert_decimals(v) for k, v in value.items()}
    return value

def handle_error(error):
    """Handle exceptions and return proper JSON error response"""
    print(f'Error: {str(error)}')
    print(traceback.format_exc())
    
    return jsonify({
        'error': str(error),
        'message': 'Internal server error'
    }), 500

def create_cors_response(data, status_code=200):
    """Create response with CORS headers for frontend"""
    response = jsonify(data)
    response.status_code = status_code
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    return response