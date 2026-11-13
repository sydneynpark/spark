from handlers.birds import birds_bp
from handlers.photos import photos_bp
from handlers.posts import posts_bp
from handlers.books import books_bp
from utils.app_util import create_app, handle_lambda_event

# ContentAPI: the site's public, read-only API. /admin/* is AdminAPI
# (admin_lambda_function.py), the only one whose role can write content.
app = create_app(birds_bp, photos_bp, posts_bp, books_bp)

@app.route('/health')
def health():
    return {'status': 'healthy', 'service': 'spark-wiki-api'}

def lambda_handler(event, context):
    return handle_lambda_event(app, event, context)
