import unittest
from unittest.mock import patch, MagicMock
import json
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from open_library_util import OpenLibraryUtil


def _response_with(payload):
    mock_response = MagicMock()
    mock_response.__enter__.return_value = mock_response
    mock_response.read.return_value = json.dumps(payload).encode('utf-8')
    return mock_response


class TestOpenLibraryUtil(unittest.TestCase):

    def setUp(self):
        self.util = OpenLibraryUtil()

    @patch('open_library_util.urllib.request.urlopen')
    def test_returns_cover_id_of_first_result(self, mock_urlopen):
        mock_urlopen.return_value = _response_with({
            'docs': [
                {'title': 'Project Hail Mary', 'cover_i': 12345},
                {'title': 'Some Other Book', 'cover_i': 99999},
            ]
        })

        cover_id = self.util.find_cover_id('Project Hail Mary', 'Andy Weir')

        self.assertEqual(cover_id, 12345)

    @patch('open_library_util.urllib.request.urlopen')
    def test_no_results_returns_none(self, mock_urlopen):
        mock_urlopen.return_value = _response_with({'docs': []})

        cover_id = self.util.find_cover_id('Some Unpublished Book', 'Nobody')

        self.assertIsNone(cover_id)

    @patch('open_library_util.urllib.request.urlopen')
    def test_result_with_no_cover_returns_none(self, mock_urlopen):
        mock_urlopen.return_value = _response_with({'docs': [{'title': 'No Cover Book'}]})

        cover_id = self.util.find_cover_id('No Cover Book', 'Someone')

        self.assertIsNone(cover_id)

    @patch('open_library_util.urllib.request.urlopen')
    def test_request_failure_returns_none(self, mock_urlopen):
        mock_urlopen.side_effect = Exception('network error')

        cover_id = self.util.find_cover_id('Project Hail Mary', 'Andy Weir')

        self.assertIsNone(cover_id)

    @patch('open_library_util.urllib.request.urlopen')
    def test_fetch_cover_image_returns_bytes(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.__enter__.return_value = mock_response
        mock_response.read.return_value = b'fake-jpeg-bytes'
        mock_urlopen.return_value = mock_response

        image_bytes = self.util.fetch_cover_image(12345)

        self.assertEqual(image_bytes, b'fake-jpeg-bytes')
        requested_url = mock_urlopen.call_args[0][0].full_url
        self.assertEqual(requested_url, 'https://covers.openlibrary.org/b/id/12345-L.jpg')

    @patch('open_library_util.urllib.request.urlopen')
    def test_fetch_cover_image_failure_returns_none(self, mock_urlopen):
        mock_urlopen.side_effect = Exception('network error')

        image_bytes = self.util.fetch_cover_image(12345)

        self.assertIsNone(image_bytes)

if __name__ == '__main__':
    unittest.main()
