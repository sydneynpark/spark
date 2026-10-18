from handlers.admin import admin_bp
from utils.app_util import create_app, handle_lambda_event

# AdminAPI: the admin page's API, everything under /admin/. API Gateway
# routes it here rather than to ContentAPI (lambda_function.py), so that only
# this function's role can sign in admins or write content.
app = create_app(admin_bp)

def lambda_handler(event, context):
    return handle_lambda_event(app, event, context)
