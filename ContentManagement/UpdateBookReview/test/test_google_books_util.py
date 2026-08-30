import unittest
from unittest.mock import patch, MagicMock
import json
import os
import sys
import urllib.error
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
import google_books_util
from google_books_util import GoogleBooksUtil


def _response_with(payload):
    mock_response = MagicMock()
    mock_response.__enter__.return_value = mock_response
    mock_response.read.return_value = json.dumps(payload).encode('utf-8')
    return mock_response


class TestGoogleBooksUtil(unittest.TestCase):

    def setUp(self):
        self.util = GoogleBooksUtil('fake-api-key')

    @patch('google_books_util.urllib.request.urlopen')
    def test_returns_full_volume_info_from_the_first_matching_id(self, mock_urlopen):
        # The search endpoint's own volumeInfo is a trimmed summary (its
        # categories collapse to one broad label) -- find_volume_info does
        # a second GET-by-id fetch and returns *that* fuller volumeInfo.
        mock_urlopen.side_effect = [
            _response_with({
                'items': [
                    {'id': 'abc123', 'volumeInfo': {'title': 'Project Hail Mary', 'categories': ['Fiction']}},
                    {'id': 'zzz999', 'volumeInfo': {'title': 'Some Other Book', 'categories': ['Mystery']}},
                ]
            }),
            _response_with({
                'volumeInfo': {
                    'title': 'Project Hail Mary',
                    'categories': ['Fiction / Science Fiction / General', 'Fiction / Humorous'],
                },
            }),
        ]

        volume_info = self.util.find_volume_info('Project Hail Mary', 'Andy Weir')

        self.assertEqual(
            volume_info['categories'], ['Fiction / Science Fiction / General', 'Fiction / Humorous'])
        self.assertEqual(mock_urlopen.call_count, 2)
        detail_url = mock_urlopen.call_args_list[1][0][0].full_url
        self.assertIn('/volumes/abc123', detail_url)
        self.assertIn('key=fake-api-key', detail_url)

    @patch('google_books_util.urllib.request.urlopen')
    def test_falls_back_to_search_summary_when_detail_fetch_fails(self, mock_urlopen):
        mock_urlopen.side_effect = [
            _response_with({
                'items': [{'id': 'abc123', 'volumeInfo': {'title': 'Project Hail Mary', 'categories': ['Fiction']}}]
            }),
            Exception('network error'),
        ]

        volume_info = self.util.find_volume_info('Project Hail Mary', 'Andy Weir')

        self.assertEqual(volume_info['categories'], ['Fiction'])

    @patch('google_books_util.urllib.request.urlopen')
    def test_returns_search_summary_when_result_has_no_id(self, mock_urlopen):
        mock_urlopen.return_value = _response_with({
            'items': [{'volumeInfo': {'title': 'Project Hail Mary', 'categories': ['Science Fiction']}}]
        })

        volume_info = self.util.find_volume_info('Project Hail Mary', 'Andy Weir')

        self.assertEqual(volume_info['categories'], ['Science Fiction'])
        self.assertEqual(mock_urlopen.call_count, 1)

    @patch('google_books_util.urllib.request.urlopen')
    def test_no_results_returns_none(self, mock_urlopen):
        mock_urlopen.return_value = _response_with({'items': []})

        volume_info = self.util.find_volume_info('Some Unpublished Book', 'Nobody')

        self.assertIsNone(volume_info)

    @patch('google_books_util.urllib.request.urlopen')
    def test_request_failure_returns_none(self, mock_urlopen):
        mock_urlopen.side_effect = Exception('network error')

        volume_info = self.util.find_volume_info('Project Hail Mary', 'Andy Weir')

        self.assertIsNone(volume_info)

    @patch('google_books_util.urllib.request.urlopen')
    def test_request_includes_title_author_and_key(self, mock_urlopen):
        mock_urlopen.return_value = _response_with({'items': [{'volumeInfo': {}}]})

        self.util.find_volume_info('Project Hail Mary', 'Andy Weir')

        requested_url = mock_urlopen.call_args[0][0].full_url
        self.assertIn('intitle%3AProject+Hail+Mary', requested_url)
        self.assertIn('inauthor%3AAndy+Weir', requested_url)
        self.assertIn('key=fake-api-key', requested_url)

    @patch('google_books_util.urllib.request.urlopen')
    def test_request_restricts_search_to_english(self, mock_urlopen):
        # Without this, Google Books can match a foreign-language edition
        # (and its non-English description) over the English one.
        mock_urlopen.return_value = _response_with({'items': []})

        self.util.find_volume_info('Project Hail Mary', 'Andy Weir')

        requested_url = mock_urlopen.call_args[0][0].full_url
        self.assertIn('langRestrict=en', requested_url)

    @patch('google_books_util.urllib.request.urlopen')
    def test_search_request_sets_user_agent(self, mock_urlopen):
        # Google's front end has been observed shedding load from requests
        # carrying urllib's default User-Agent -- this is the header that
        # find_volume_info's underlying fetch must set to avoid that.
        mock_urlopen.return_value = _response_with({'items': []})

        self.util.find_volume_info('Project Hail Mary', 'Andy Weir')

        request = mock_urlopen.call_args[0][0]
        self.assertEqual(request.get_header('User-agent'), google_books_util.USER_AGENT)

    def test_extract_genres_drops_generic_top_level_and_dedupes(self):
        volume_info = {
            'categories': [
                'Fiction / Mystery & Detective / Cozy / Animals',
                'Fiction / Mystery & Detective / Women Sleuths',
                'Fiction / Mystery & Detective / Amateur Sleuth',
            ],
        }

        genres = self.util.extract_genres(volume_info)

        self.assertEqual(
            genres, ['Mystery & Detective', 'Cozy', 'Animals', 'Women Sleuths', 'Amateur Sleuth'])

    def test_extract_genres_keeps_specific_top_level_category(self):
        # "Cooking" (unlike "Fiction"/"Nonfiction") already carries genre
        # information, so it shouldn't be dropped just for being first.
        volume_info = {'categories': ['Cooking / Regional & Ethnic / Chinese']}

        genres = self.util.extract_genres(volume_info)

        self.assertEqual(genres, ['Cooking', 'Regional & Ethnic', 'Chinese'])

    def test_extract_genres_keeps_bare_generic_category(self):
        # A single-segment "Fiction" is all the info there is -- dropping
        # it would leave nothing.
        volume_info = {'categories': ['Fiction']}

        genres = self.util.extract_genres(volume_info)

        self.assertEqual(genres, ['Fiction'])

    def test_extract_genres_returns_empty_list_when_no_categories(self):
        genres = self.util.extract_genres({})

        self.assertEqual(genres, [])

    def test_find_cover_url_prefers_largest_available_size(self):
        volume_info = {
            'imageLinks': {
                'smallThumbnail': 'http://books.google.com/small-thumb.jpg',
                'thumbnail': 'http://books.google.com/thumb.jpg',
                'medium': 'http://books.google.com/medium.jpg',
            }
        }

        cover_url = self.util.find_cover_url(volume_info)

        self.assertEqual(cover_url, 'https://books.google.com/medium.jpg')

    def test_find_cover_url_upgrades_http_to_https(self):
        volume_info = {'imageLinks': {'thumbnail': 'http://books.google.com/thumb.jpg'}}

        cover_url = self.util.find_cover_url(volume_info)

        self.assertEqual(cover_url, 'https://books.google.com/thumb.jpg')

    def test_find_cover_url_returns_none_when_no_image_links(self):
        cover_url = self.util.find_cover_url({})

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

    @patch('google_books_util.time.sleep')
    @patch('google_books_util.urllib.request.urlopen')
    def test_retries_after_a_503_then_succeeds(self, mock_urlopen, mock_sleep):
        mock_urlopen.side_effect = [
            urllib.error.HTTPError('url', 503, 'Service Unavailable', {}, None),
            _response_with({'items': []}),
        ]

        volume_info = self.util.find_volume_info('Project Hail Mary', 'Andy Weir')

        self.assertIsNone(volume_info)
        self.assertEqual(mock_urlopen.call_count, 2)
        mock_sleep.assert_called_once()

    @patch('google_books_util.time.sleep')
    @patch('google_books_util.urllib.request.urlopen')
    def test_gives_up_after_max_attempts_of_persistent_503s(self, mock_urlopen, mock_sleep):
        mock_urlopen.side_effect = urllib.error.HTTPError('url', 503, 'Service Unavailable', {}, None)

        volume_info = self.util.find_volume_info('Project Hail Mary', 'Andy Weir')

        self.assertIsNone(volume_info)
        self.assertEqual(mock_urlopen.call_count, google_books_util.MAX_ATTEMPTS)

    @patch('google_books_util.time.sleep')
    @patch('google_books_util.urllib.request.urlopen')
    def test_does_not_retry_non_retryable_http_errors(self, mock_urlopen, mock_sleep):
        mock_urlopen.side_effect = urllib.error.HTTPError('url', 404, 'Not Found', {}, None)

        volume_info = self.util.find_volume_info('Project Hail Mary', 'Andy Weir')

        self.assertIsNone(volume_info)
        self.assertEqual(mock_urlopen.call_count, 1)
        mock_sleep.assert_not_called()


if __name__ == '__main__':
    unittest.main()
