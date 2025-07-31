from flask import Flask
import serverless_wsgi
from handlers.photos import photos_bp
from handlers.posts import posts_bp

# Create Flask app
app = Flask(__name__)

# Register blueprints
app.register_blueprint(photos_bp, url_prefix='/api')
app.register_blueprint(posts_bp, url_prefix='/api')

@app.route('/health')
def health():
    return {'status': 'healthy', 'service': 'spark-wiki-api'}

def lambda_handler(event, context):
    return serverless_wsgi.handle_request(app, event, context)