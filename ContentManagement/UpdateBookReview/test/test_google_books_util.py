import unittest
from unittest.mock import patch, MagicMock
import json
import os
import sys
import urllib.error
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from google_books_util import GoogleBooksUtil


def _rate_limited(retry_after=None):
    hdrs = {'Retry-After': retry_after} if retry_after else {}
    return urllib.error.HTTPError('url', 429, 'Too Many Requests', hdrs, None)


def _not_found():
    return urllib.error.HTTPError('url', 404, 'Not Found', {}, None)


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
    def test_includes_api_key_when_env_var_set(self, mock_urlopen):
        mock_urlopen.return_value = _response_with({'items': []})

        with patch.dict(os.environ, {'GOOGLE_BOOKS_API_KEY': 'test-key-123'}):
            self.util.find_cover_url('Project Hail Mary', 'Andy Weir')

        requested_url = mock_urlopen.call_args[0][0].full_url
        self.assertIn('key=test-key-123', requested_url)

    @patch('google_books_util.urllib.request.urlopen')
    def test_omits_api_key_when_env_var_unset(self, mock_urlopen):
        mock_urlopen.return_value = _response_with({'items': []})

        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop('GOOGLE_BOOKS_API_KEY', None)
            self.util.find_cover_url('Project Hail Mary', 'Andy Weir')

        requested_url = mock_urlopen.call_args[0][0].full_url
        self.assertNotIn('key=', requested_url)

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

    @patch('google_books_util.time.sleep')
    @patch('google_books_util.urllib.request.urlopen')
    def test_retries_on_429_then_succeeds(self, mock_urlopen, mock_sleep):
        mock_urlopen.side_effect = [
            _rate_limited(retry_after='1.5'),
            _response_with({'items': [{'volumeInfo': {'imageLinks': {
                'thumbnail': 'http://books.google.com/thumb.jpg',
            }}}]}),
        ]

        cover_url = self.util.find_cover_url('Project Hail Mary', 'Andy Weir')

        self.assertEqual(cover_url, 'https://books.google.com/thumb.jpg')
        self.assertEqual(mock_urlopen.call_count, 2)
        # Honors the server's Retry-After rather than a fixed backoff.
        mock_sleep.assert_called_once_with(1.5)

    @patch('google_books_util.time.sleep')
    @patch('google_books_util.urllib.request.urlopen')
    def test_gives_up_after_repeated_429s(self, mock_urlopen, mock_sleep):
        mock_urlopen.side_effect = [_rate_limited(), _rate_limited(), _rate_limited()]

        cover_url = self.util.find_cover_url('Project Hail Mary', 'Andy Weir')

        # A persistent rate limit is a failed lookup, not "this book has no
        # cover" -- either way it degrades to None so the review still saves.
        self.assertIsNone(cover_url)
        self.assertEqual(mock_urlopen.call_count, 3)

    @patch('google_books_util.time.sleep')
    @patch('google_books_util.urllib.request.urlopen')
    def test_non_429_http_error_is_not_retried(self, mock_urlopen, mock_sleep):
        mock_urlopen.side_effect = _not_found()

        cover_url = self.util.find_cover_url('Project Hail Mary', 'Andy Weir')

        self.assertIsNone(cover_url)
        self.assertEqual(mock_urlopen.call_count, 1)
        mock_sleep.assert_not_called()

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
