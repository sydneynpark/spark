import os
from flask import Blueprint, jsonify, request
from utils.response_util import handle_error, convert_decimals
from utils.rating_util import add_star_rating

if os.getenv('LOCAL_MODE') == 'true':
    from utils.local_util import LocalDynamoUtil as DynamoUtil
else:
    from utils.aws_util import DynamoUtil

books_bp = Blueprint('books', __name__)
dynamo = DynamoUtil()

@books_bp.route('/books', methods=['GET'])
def list_books():
    """List all book reviews, most recently reviewed first"""
    try:
        limit = int(request.args.get('limit', 50))
        books = [add_star_rating(book) for book in convert_decimals(dynamo.get_books(limit=limit))]
        return jsonify({
            'books': books,
            'count': len(books)
        })

    except Exception as e:
        return handle_error(e)

@books_bp.route('/books/<title>', methods=['GET'])
def get_book(title):
    """Get a single book review by title"""
    try:
        book = dynamo.get_book_by_title(title)

        if not book:
            return jsonify({'error': 'Book review not found'}), 404

        return jsonify(add_star_rating(convert_decimals(book)))

    except Exception as e:
        return handle_error(e)
