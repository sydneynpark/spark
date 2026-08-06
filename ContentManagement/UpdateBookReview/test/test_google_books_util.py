import unittest
from unittest.mock import patch, MagicMock
import json
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from google_books_util import GoogleBooksUtil


def _response_with(payload):
    mock_response = MagicMock()
    mock_response.__enter__.return_value = mock_response
    mock_response.read.return_value = json.dumps(payload).encode('utf-8')
    return mock_response


class TestGoogleBooksUtil(unittest.TestCase):

    def setUp(self):
        self.util = GoogleBooksUtil()

    @patch('google_books_util.urllib.request.urlopen')
    def test_returns_metadata_of_first_result(self, mock_urlopen):
        mock_urlopen.return_value = _response_with({
            'items': [
                {'volumeInfo': {
                    'imageLinks': {
                        'smallThumbnail': 'http://books.google.com/small.jpg',
                        'thumbnail': 'http://books.google.com/thumb.jpg',
                    },
                    'description': 'A stranded astronaut must save humanity.',
                    'categories': ['Fiction / Science Fiction / General'],
                }},
                {'volumeInfo': {'imageLinks': {'thumbnail': 'http://books.google.com/other.jpg'}}},
            ]
        })

        metadata = self.util.find_book_metadata('Project Hail Mary', 'Andy Weir')

        self.assertEqual(metadata['cover_url'], 'https://books.google.com/thumb.jpg')
        self.assertEqual(metadata['description'], 'A stranded astronaut must save humanity.')
        self.assertEqual(metadata['genres'], ['Fiction', 'Science Fiction', 'General'])

    @patch('google_books_util.urllib.request.urlopen')
    def test_falls_back_to_small_thumbnail(self, mock_urlopen):
        mock_urlopen.return_value = _response_with({
            'items': [{'volumeInfo': {'imageLinks': {
                'smallThumbnail': 'http://books.google.com/small.jpg',
            }}}]
        })

        metadata = self.util.find_book_metadata('Project Hail Mary', 'Andy Weir')

        self.assertEqual(metadata['cover_url'], 'https://books.google.com/small.jpg')

    @patch('google_books_util.urllib.request.urlopen')
    def test_dedupes_genres_across_multiple_categories(self, mock_urlopen):
        mock_urlopen.return_value = _response_with({
            'items': [{'volumeInfo': {
                'categories': ['Fiction / Thrillers / Suspense', 'Fiction / Mystery'],
            }}]
        })

        metadata = self.util.find_book_metadata('Vicious', 'V. E. Schwab')

        self.assertEqual(metadata['genres'], ['Fiction', 'Thrillers', 'Suspense', 'Mystery'])

    @patch('google_books_util.urllib.request.urlopen')
    def test_strips_html_from_description(self, mock_urlopen):
        mock_urlopen.return_value = _response_with({
            'items': [{'volumeInfo': {
                'description': '<p>A <b>gripping</b> tale.</p><p>Book two.</p>',
            }}]
        })

        metadata = self.util.find_book_metadata('Vicious', 'V. E. Schwab')

        self.assertEqual(metadata['description'], 'A gripping tale.\n\nBook two.')

    @patch('google_books_util.urllib.request.urlopen')
    def test_no_results_returns_empty_metadata(self, mock_urlopen):
        mock_urlopen.return_value = _response_with({'items': []})

        metadata = self.util.find_book_metadata('Some Unpublished Book', 'Nobody')

        self.assertIsNone(metadata['cover_url'])
        self.assertIsNone(metadata['description'])
        self.assertEqual(metadata['genres'], [])

    @patch('google_books_util.urllib.request.urlopen')
    def test_result_with_no_fields_returns_empty_metadata(self, mock_urlopen):
        mock_urlopen.return_value = _response_with({'items': [{'volumeInfo': {}}]})

        metadata = self.util.find_book_metadata('No Cover Book', 'Someone')

        self.assertIsNone(metadata['cover_url'])
        self.assertIsNone(metadata['description'])
        self.assertEqual(metadata['genres'], [])

    @patch('google_books_util.urllib.request.urlopen')
    def test_request_failure_returns_empty_metadata(self, mock_urlopen):
        mock_urlopen.side_effect = Exception('network error')

        metadata = self.util.find_book_metadata('Project Hail Mary', 'Andy Weir')

        self.assertIsNone(metadata['cover_url'])
        self.assertIsNone(metadata['description'])
        self.assertEqual(metadata['genres'], [])

    @patch('google_books_util.urllib.request.urlopen')
    def test_fetch_cover_image_returns_bytes(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.__enter__.return_value = mock_response
        mock_response.read.return_value = b'fake-jpeg-bytes'
        mock_urlopen.return_value = mock_response

        image_bytes = self.util.fetch_cover_image('https://books.google.com/thumb.jpg')

        self.assertEqual(image_bytes, b'fake-jpeg-bytes')
        requested_url = mock_urlopen.call_args[0][0].full_url
        self.assertEqual(requested_url, 'https://books.google.com/thumb.jpg')

    @patch('google_books_util.urllib.request.urlopen')
    def test_fetch_cover_image_failure_returns_none(self, mock_urlopen):
        mock_urlopen.side_effect = Exception('network error')

        image_bytes = self.util.fetch_cover_image('https://books.google.com/thumb.jpg')

        self.assertIsNone(image_bytes)

if __name__ == '__main__':
    unittest.main()
