from flask import Flask
import serverless_wsgi
from handlers.photos import photos_bp
from handlers.posts import posts_bp

# Create Flask app
app = Flask(__name__)

# Add CORS headers to all responses
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization,X-Requested-With')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

# Handle preflight OPTIONS requests
@app.before_request
def before_request():
    from flask import request
    if request.method == 'OPTIONS':
        from flask import make_response
        response = make_response()
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization,X-Requested-With')
        response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
        return response

# Register blueprints
app.register_blueprint(photos_bp)
app.register_blueprint(posts_bp)

@app.route('/health')
def health():
    return {'status': 'healthy', 'service': 'spark-wiki-api'}

def lambda_handler(event, context):
    return serverless_wsgi.handle_request(app, event, context)