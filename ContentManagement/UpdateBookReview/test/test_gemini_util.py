import unittest
from unittest.mock import patch, MagicMock
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from gemini_util import GeminiUtil
from google.genai import errors


def _rate_limit_error(retry_delay='0.01s'):
    return errors.ClientError(429, {
        'error': {
            'code': 429,
            'status': 'RESOURCE_EXHAUSTED',
            'message': 'quota exceeded',
            'details': [
                {'@type': 'type.googleapis.com/google.rpc.RetryInfo', 'retryDelay': retry_delay},
            ],
        }
    })


class TestGeminiUtil(unittest.TestCase):

    @patch('gemini_util.genai.Client')
    def test_paraphrase_synopsis_returns_response_text(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_response = MagicMock()
        mock_response.text = 'A paraphrased synopsis.'
        mock_client.models.generate_content.return_value = mock_response

        util = GeminiUtil('fake-api-key')
        result = util.paraphrase_synopsis('The original synopsis.')

        self.assertEqual(result, 'A paraphrased synopsis.')
        mock_client_cls.assert_called_once_with(api_key='fake-api-key')
        _, kwargs = mock_client.models.generate_content.call_args
        self.assertEqual(kwargs['contents'], 'The original synopsis.')

    @patch('gemini_util.genai.Client')
    def test_paraphrase_synopsis_returns_none_on_failure(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.models.generate_content.side_effect = Exception('api error')

        util = GeminiUtil('fake-api-key')
        result = util.paraphrase_synopsis('The original synopsis.')

        self.assertIsNone(result)

    @patch('gemini_util.time.sleep')
    @patch('gemini_util.genai.Client')
    def test_paraphrase_synopsis_retries_on_rate_limit_then_succeeds(self, mock_client_cls, mock_sleep):
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_response = MagicMock()
        mock_response.text = 'A paraphrased synopsis.'
        mock_client.models.generate_content.side_effect = [_rate_limit_error('12s'), mock_response]

        util = GeminiUtil('fake-api-key')
        result = util.paraphrase_synopsis('The original synopsis.')

        self.assertEqual(result, 'A paraphrased synopsis.')
        self.assertEqual(mock_client.models.generate_content.call_count, 2)
        mock_sleep.assert_called_once_with(12.0)

    @patch('gemini_util.time.sleep')
    @patch('gemini_util.genai.Client')
    def test_paraphrase_synopsis_gives_up_after_max_retries(self, mock_client_cls, mock_sleep):
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.models.generate_content.side_effect = _rate_limit_error()

        util = GeminiUtil('fake-api-key')
        result = util.paraphrase_synopsis('The original synopsis.')

        self.assertIsNone(result)
        self.assertEqual(mock_client.models.generate_content.call_count, 3)

    @patch('gemini_util.time.sleep')
    @patch('gemini_util.genai.Client')
    def test_paraphrase_synopsis_falls_back_to_default_delay_when_missing(self, mock_client_cls, mock_sleep):
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_response = MagicMock()
        mock_response.text = 'A paraphrased synopsis.'
        no_retry_info = errors.ClientError(429, {'error': {'code': 429, 'status': 'RESOURCE_EXHAUSTED'}})
        mock_client.models.generate_content.side_effect = [no_retry_info, mock_response]

        util = GeminiUtil('fake-api-key')
        result = util.paraphrase_synopsis('The original synopsis.')

        self.assertEqual(result, 'A paraphrased synopsis.')
        mock_sleep.assert_called_once_with(20)


if __name__ == '__main__':
    unittest.main()
