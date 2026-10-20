"""What this project's Lambdas share: a Flask app with the site's CORS
handling, and the Lambda entry point that runs one. ContentAPI
(lambda_function.py) and AdminAPI (admin_lambda_function.py) are deployed
from the same package, each serving its own app."""
from flask import Flask, make_response, request
import serverless_wsgi


def create_app(*blueprints):
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
        if request.method == 'OPTIONS':
            return make_response()

    for blueprint in blueprints:
        app.register_blueprint(blueprint)

    return app


def handle_lambda_event(app, event, context):
    response = serverless_wsgi.handle_request(app, event, context)
    content_type = response.get('headers', {}).get('Content-Type', '')
    if content_type.startswith('image/'):
        response['isBase64Encoded'] = True
    return response
