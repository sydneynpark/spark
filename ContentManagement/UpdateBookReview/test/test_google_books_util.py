import unittest
from unittest.mock import patch, MagicMock
import json
import os
import sys
import urllib.error
import urllib.parse
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
import google_books_util
from google_books_util import GoogleBooksUtil


def _response_with(payload):
    mock_response = MagicMock()
    mock_response.__enter__.return_value = mock_response
    mock_response.read.return_value = json.dumps(payload).encode('utf-8')
    return mock_response


def _item(title, *authors, subtitle=None, volume_id=None):
    info = {'title': title, 'authors': list(authors)}
    if subtitle:
        info['subtitle'] = subtitle
    item = {'volumeInfo': info}
    if volume_id:
        item['id'] = volume_id
    return item


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
                    {'id': 'abc123', 'volumeInfo': {'title': 'Project Hail Mary', 'authors': ['Andy Weir'], 'categories': ['Fiction']}},
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
                'items': [{'id': 'abc123', 'volumeInfo': {'title': 'Project Hail Mary', 'authors': ['Andy Weir'], 'categories': ['Fiction']}}]
            }),
            Exception('network error'),
        ]

        volume_info = self.util.find_volume_info('Project Hail Mary', 'Andy Weir')

        self.assertEqual(volume_info['categories'], ['Fiction'])

    @patch('google_books_util.urllib.request.urlopen')
    def test_returns_search_summary_when_result_has_no_id(self, mock_urlopen):
        mock_urlopen.return_value = _response_with({
            'items': [{'volumeInfo': {'title': 'Project Hail Mary', 'authors': ['Andy Weir'], 'categories': ['Science Fiction']}}]
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
        mock_urlopen.return_value = _response_with({'items': [_item('Project Hail Mary', 'Andy Weir')]})

        self.util.find_volume_info('Project Hail Mary', 'Andy Weir')

        requested_url = mock_urlopen.call_args_list[0][0][0].full_url
        self.assertIn('q=project+hail+mary+andy+weir', requested_url)
        self.assertIn('key=fake-api-key', requested_url)

    @patch('google_books_util.urllib.request.urlopen')
    def test_request_restricts_search_to_english(self, mock_urlopen):
        # Without this, Google Books can match a foreign-language edition
        # (and its non-English description) over the English one.
        mock_urlopen.return_value = _response_with({
            'items': [_item('Project Hail Mary', 'Andy Weir')]
        })

        self.util.find_volume_info('Project Hail Mary', 'Andy Weir')

        first_search_url = mock_urlopen.call_args_list[0][0][0].full_url
        self.assertIn('langRestrict=en', first_search_url)

    @patch('google_books_util.urllib.request.urlopen')
    def test_falls_back_to_unrestricted_search_when_no_english_match(self, mock_urlopen):
        # Obscure titles, or books translated *into* English, may have no
        # English-language edition on Google Books at all -- a match in
        # some language beats no cover/genres/synopsis whatsoever, since
        # Gemini is instructed to translate the synopsis to English anyway.
        mock_urlopen.side_effect = [
            _response_with({'items': []}),
            _response_with({'items': []}),
            _response_with({'items': []}),
            _response_with({'items': [_item('Some Translated Novel', 'An Author')]}),
        ]

        volume_info = self.util.find_volume_info('Some Translated Novel', 'An Author')

        self.assertEqual(volume_info, _item('Some Translated Novel', 'An Author')['volumeInfo'])
        self.assertEqual(mock_urlopen.call_count, 4)
        search_urls = [call[0][0].full_url for call in mock_urlopen.call_args_list]
        for url in search_urls[:3]:
            self.assertIn('langRestrict=en', url)
        self.assertNotIn('langRestrict', search_urls[3])

    @patch('google_books_util.urllib.request.urlopen')
    def test_returns_none_when_neither_english_nor_fallback_search_matches(self, mock_urlopen):
        mock_urlopen.return_value = _response_with({'items': []})

        volume_info = self.util.find_volume_info('Some Unpublished Book', 'Nobody')

        self.assertIsNone(volume_info)
        # All three keyword queries, in English and then unrestricted.
        self.assertEqual(mock_urlopen.call_count, 6)

    @patch('google_books_util.urllib.request.urlopen')
    def test_does_not_fall_back_when_english_search_request_errors(self, mock_urlopen):
        # A failed request is not the same as "no English match" -- retrying
        # in another language wouldn't fix a network error, so this should
        # fail fast rather than doubling up on a doomed request.
        mock_urlopen.side_effect = Exception('network error')

        volume_info = self.util.find_volume_info('Project Hail Mary', 'Andy Weir')

        self.assertIsNone(volume_info)
        self.assertEqual(mock_urlopen.call_count, 1)

    @patch('google_books_util.urllib.request.urlopen')
    def test_search_request_sets_user_agent(self, mock_urlopen):
        # Google's front end has been observed shedding load from requests
        # carrying urllib's default User-Agent -- this is the header that
        # find_volume_info's underlying fetch must set to avoid that.
        mock_urlopen.return_value = _response_with({'items': []})

        self.util.find_volume_info('Project Hail Mary', 'Andy Weir')

        request = mock_urlopen.call_args[0][0]
        self.assertEqual(request.get_header('User-agent'), google_books_util.USER_AGENT)

    def _search_queries(self, mock_urlopen):
        return [
            urllib.parse.parse_qs(urllib.parse.urlparse(call[0][0].full_url).query)['q'][0]
            for call in mock_urlopen.call_args_list
        ]

    @patch('google_books_util.urllib.request.urlopen')
    def test_queries_are_plain_keywords_without_field_operators(self, mock_urlopen):
        # Google Books returns zero results for many intitle:/inauthor:
        # queries that should match (e.g. "vicious inauthor:schwab"), so
        # matching is done by _pick_match instead. Punctuation is stripped
        # so a stray "word:" can't be read as an operator.
        mock_urlopen.return_value = _response_with({'items': []})

        self.util.find_volume_info('shut up 2: the sequel', 'V.E. Schwab')

        self.assertEqual(self._search_queries(mock_urlopen)[:3], [
            'shut up 2 the sequel v e schwab',
            '"shut up 2 the sequel" schwab',
            '"shut up 2 the sequel"',
        ])

    @patch('google_books_util.urllib.request.urlopen')
    def test_matches_author_with_initials_on_surname(self, mock_urlopen):
        # Google stores "V. E. Schwab"; ours is "V.E. Schwab".
        mock_urlopen.return_value = _response_with({'items': [_item('Vicious', 'V. E. Schwab')]})

        volume_info = self.util.find_volume_info('Vicious', 'V.E. Schwab')

        self.assertEqual(volume_info['title'], 'Vicious')

    @patch('google_books_util.urllib.request.urlopen')
    def test_skips_author_check_when_review_has_no_author(self, mock_urlopen):
        mock_urlopen.return_value = _response_with({'items': [_item('Holiday Ever After', 'Someone')]})

        volume_info = self.util.find_volume_info('Holiday Ever After', '')

        self.assertEqual(volume_info['title'], 'Holiday Ever After')
        self.assertEqual(self._search_queries(mock_urlopen), ['holiday ever after'])

    @patch('google_books_util.urllib.request.urlopen')
    def test_matches_title_with_appended_subtitle(self, mock_urlopen):
        mock_urlopen.return_value = _response_with({'items': [_item('Yellowface: A Novel', 'R. F. Kuang')]})

        volume_info = self.util.find_volume_info('Yellowface', 'R.F. Kuang')

        self.assertEqual(volume_info['title'], 'Yellowface: A Novel')

    @patch('google_books_util.urllib.request.urlopen')
    def test_matches_review_title_against_title_plus_subtitle_field(self, mock_urlopen):
        mock_urlopen.return_value = _response_with({
            'items': [_item('Sapiens', 'Yuval Noah Harari', subtitle='A Brief History of Humankind')]
        })

        volume_info = self.util.find_volume_info('Sapiens: A Brief History of Humankind', 'Yuval Noah Harari')

        self.assertEqual(volume_info['title'], 'Sapiens')

    @patch('google_books_util.urllib.request.urlopen')
    def test_ignores_leading_article_and_accents(self, mock_urlopen):
        mock_urlopen.return_value = _response_with({'items': [_item('Metamorphosis', 'Franz Káfka')]})

        volume_info = self.util.find_volume_info('The Metamorphosis', 'Franz Kafka')

        self.assertEqual(volume_info['title'], 'Metamorphosis')

    @patch('google_books_util.urllib.request.urlopen')
    def test_skips_results_that_are_not_the_book(self, mock_urlopen):
        # Study guides and summaries often rank above the book itself.
        mock_urlopen.return_value = _response_with({
            'items': [
                _item('Summary of The Secret History', 'Quick Reads'),
                _item('The Secret History', 'Someone Else'),
                _item('The Secret History', 'Donna Tartt', volume_id=None),
            ]
        })

        volume_info = self.util.find_volume_info('The Secret History', 'Donna Tartt')

        self.assertEqual(volume_info['authors'], ['Donna Tartt'])

    @patch('google_books_util.urllib.request.urlopen')
    def test_tries_next_query_when_first_has_no_match(self, mock_urlopen):
        mock_urlopen.side_effect = [
            _response_with({'items': [_item('Unrelated', 'Jenny Offill')]}),
            _response_with({'items': [_item('Dept. of Speculation', 'Jenny Offill')]}),
        ]

        volume_info = self.util.find_volume_info('Dept. of Speculation', 'Jenny Offill')

        self.assertEqual(volume_info['title'], 'Dept. of Speculation')
        self.assertEqual(
            self._search_queries(mock_urlopen),
            ['dept of speculation jenny offill', '"dept of speculation" offill'])

    @patch('google_books_util.urllib.request.urlopen')
    def test_prefers_retail_edition_over_library_scan(self, mock_urlopen):
        # Library scans have no ISBN, and their "cover" is a photo of an
        # interior page.
        scan = _item('The Metamorphosis', 'Franz Kafka')
        scan['volumeInfo']['imageLinks'] = {'thumbnail': 'http://books.google.com/scan.jpg'}
        retail = _item('The Metamorphosis', 'Franz Kafka')
        retail['volumeInfo']['industryIdentifiers'] = [{'type': 'ISBN_13', 'identifier': '9780000000000'}]
        retail['volumeInfo']['imageLinks'] = {'thumbnail': 'http://books.google.com/retail.jpg'}
        mock_urlopen.return_value = _response_with({'items': [scan, retail]})

        volume_info = self.util.find_volume_info('The Metamorphosis', 'Franz Kafka')

        self.assertEqual(volume_info['imageLinks']['thumbnail'], 'http://books.google.com/retail.jpg')

    @patch('google_books_util.urllib.request.urlopen')
    def test_prefers_edition_with_a_cover(self, mock_urlopen):
        coverless = _item('Pet', 'Catherine Chidgey')
        with_cover = _item('Pet', 'Catherine Chidgey')
        with_cover['volumeInfo']['imageLinks'] = {'thumbnail': 'http://books.google.com/pet.jpg'}
        mock_urlopen.return_value = _response_with({'items': [coverless, with_cover]})

        volume_info = self.util.find_volume_info('Pet', 'Catherine Chidgey')

        self.assertIn('imageLinks', volume_info)

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

    def test_find_cover_url_uses_thumbnail_resized_rather_than_larger_sizes(self):
        # The larger sizes are often an interior page, not the cover.
        volume_info = {
            'imageLinks': {
                'smallThumbnail': 'http://books.google.com/books/content?id=abc&printsec=frontcover&img=1&zoom=5',
                'thumbnail': 'http://books.google.com/books/content?id=abc&printsec=frontcover&img=1&zoom=1',
                'extraLarge': 'http://books.google.com/books/content?id=abc&printsec=frontcover&img=1&zoom=6',
            }
        }

        cover_url = self.util.find_cover_url(volume_info)

        self.assertEqual(
            cover_url,
            'https://books.google.com/books/content?id=abc&printsec=frontcover&img=1&zoom=1&fife=w800')

    def test_find_cover_url_strips_page_curl(self):
        volume_info = {'imageLinks': {
            'thumbnail': 'http://books.google.com/books/publisher/content?id=abc&zoom=1&edge=curl&source=gbs_api',
        }}

        cover_url = self.util.find_cover_url(volume_info)

        self.assertNotIn('edge', cover_url)
        self.assertIn('source=gbs_api', cover_url)

    def test_find_cover_url_falls_back_to_small_thumbnail(self):
        volume_info = {'imageLinks': {'smallThumbnail': 'http://books.google.com/thumb.jpg?id=abc&zoom=5'}}

        cover_url = self.util.find_cover_url(volume_info)

        self.assertEqual(cover_url, 'https://books.google.com/thumb.jpg?id=abc&zoom=1&fife=w800')

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
            _response_with({'items': [_item('Project Hail Mary', 'Andy Weir')]}),
        ]

        volume_info = self.util.find_volume_info('Project Hail Mary', 'Andy Weir')

        self.assertEqual(volume_info, _item('Project Hail Mary', 'Andy Weir')['volumeInfo'])
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
