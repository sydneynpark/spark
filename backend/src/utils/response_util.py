from flask import jsonify
from decimal import Decimal
import traceback
import re
import base64

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

def extract_preview(markdown_text, max_chars=160):
    """Return plain-text preview from markdown, skipping headings and markup."""
    parts = []
    for line in markdown_text.split('\n'):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        line = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', line)
        line = re.sub(r'[*_`~]+', '', line)
        line = line.strip()
        if line:
            parts.append(line)
    text = ' '.join(parts)
    if len(text) > max_chars:
        return text[:max_chars].rstrip() + '...'
    return text

def handle_error(error):
    """Handle exceptions and return proper JSON error response"""
    print(f'Error: {str(error)}')
    print(traceback.format_exc())
    
    return jsonify({
        'error': str(error),
        'message': 'Internal server error'
    }), 500

def parse_post_metadata(key):
    """Parse title, date, and base64 id from a post S3 key like '2024/01/15/my-post.md'"""
    parts = key.split('/')
    if len(parts) >= 4 and re.match(r'^\d{4}$', parts[0]) and re.match(r'^\d{2}$', parts[1]) and re.match(r'^\d{2}$', parts[2]):
        date = f"{parts[0]}-{parts[1]}-{parts[2]}"
        name = parts[3]
    else:
        date = None
        name = parts[-1]
    if name.endswith('.md'):
        name = name[:-3]
    title = name.replace('-', ' ').replace('_', ' ').title()
    return {
        'id': base64.b64encode(key.encode()).decode(),
        'title': title,
        'date': date,
    }

def create_cors_response(data, status_code=200):
    """Create response with CORS headers for frontend"""
    response = jsonify(data)
    response.status_code = status_code
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    return response