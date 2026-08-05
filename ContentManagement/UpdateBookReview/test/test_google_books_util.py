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
    def test_returns_cover_url_of_first_result(self, mock_urlopen):
        mock_urlopen.return_value = _response_with({
            'items': [
                {'volumeInfo': {'imageLinks': {
                    'smallThumbnail': 'http://books.google.com/small.jpg',
                    'thumbnail': 'http://books.google.com/thumb.jpg',
                }}},
                {'volumeInfo': {'imageLinks': {'thumbnail': 'http://books.google.com/other.jpg'}}},
            ]
        })

        cover_url = self.util.find_cover_url('Project Hail Mary', 'Andy Weir')

        self.assertEqual(cover_url, 'https://books.google.com/thumb.jpg')

    @patch('google_books_util.urllib.request.urlopen')
    def test_falls_back_to_small_thumbnail(self, mock_urlopen):
        mock_urlopen.return_value = _response_with({
            'items': [{'volumeInfo': {'imageLinks': {
                'smallThumbnail': 'http://books.google.com/small.jpg',
            }}}]
        })

        cover_url = self.util.find_cover_url('Project Hail Mary', 'Andy Weir')

        self.assertEqual(cover_url, 'https://books.google.com/small.jpg')

    @patch('google_books_util.urllib.request.urlopen')
    def test_no_results_returns_none(self, mock_urlopen):
        mock_urlopen.return_value = _response_with({'items': []})

        cover_url = self.util.find_cover_url('Some Unpublished Book', 'Nobody')

        self.assertIsNone(cover_url)

    @patch('google_books_util.urllib.request.urlopen')
    def test_result_with_no_cover_returns_none(self, mock_urlopen):
        mock_urlopen.return_value = _response_with({'items': [{'volumeInfo': {}}]})

        cover_url = self.util.find_cover_url('No Cover Book', 'Someone')

        self.assertIsNone(cover_url)

    @patch('google_books_util.urllib.request.urlopen')
    def test_request_failure_returns_none(self, mock_urlopen):
        mock_urlopen.side_effect = Exception('network error')

        cover_url = self.util.find_cover_url('Project Hail Mary', 'Andy Weir')

        self.assertIsNone(cover_url)

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
