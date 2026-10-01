from flask import Flask
import serverless_wsgi
from handlers.photos import photos_bp
from handlers.posts import posts_bp
from handlers.books import books_bp
from handlers.admin import admin_bp

# Create Flask app
app = Flask(__name__)

# Add CORS headers to all responses
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization,X-Requested-With')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

# Handle preflight OPTIONS requests. Just short-circuit with an empty
# response here -- after_request still runs on it and adds the CORS headers,
# so adding them here too would double them up (e.g. "Access-Control-Allow-
# Origin: *, *"), which browsers reject as an invalid CORS response.
@app.before_request
def before_request():
    from flask import request
    if request.method == 'OPTIONS':
        from flask import make_response
        return make_response()

# Register blueprints
app.register_blueprint(photos_bp)
app.register_blueprint(posts_bp)
app.register_blueprint(books_bp)
app.register_blueprint(admin_bp)

@app.route('/health')
def health():
    return {'status': 'healthy', 'service': 'spark-wiki-api'}

def lambda_handler(event, context):
    response = serverless_wsgi.handle_request(app, event, context)
    content_type = response.get('headers', {}).get('Content-Type', '')
    if content_type.startswith('image/'):
        response['isBase64Encoded'] = True
    return response