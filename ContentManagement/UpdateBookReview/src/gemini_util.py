import time

from google import genai
from google.genai import errors, types

MODEL = 'gemini-3.5-flash-lite'
MAX_RETRIES = 3
DEFAULT_RETRY_SECONDS = 20
MAX_RETRY_SECONDS = 60

SYSTEM_PROMPT = (
    'You paraphrase book synopses in your own words -- same plot points and '
    'tone, different sentence structure and phrasing than the source, so the '
    'result is not a copyright-infringing copy of the original. Always '
    'write the paraphrase in English, even if the source text is in '
    'another language. Before paraphrasing, strip out anything that is not '
    'the plot itself -- author bios and accolades, review-blurb praise, '
    'and marketing language about the book (e.g. "the #1 New York Times '
    'bestselling author", "a compelling, unputdownable narrative"). Keep '
    'only the plot synopsis, and keep it roughly the same length as the '
    'source\'s plot content (i.e. excluding whatever marketing language '
    'was dropped). Return only the paraphrased synopsis, no preamble or '
    'commentary.'
)


def _retry_delay_seconds(error):
    """Pull the server-suggested backoff (e.g. '40s') out of a 429's
    RetryInfo detail, if present, falling back to a fixed delay otherwise."""
    try:
        details = error.details.get('error', {}).get('details', [])
        for detail in details:
            if detail.get('@type', '').endswith('RetryInfo'):
                return min(float(detail['retryDelay'].rstrip('s')), MAX_RETRY_SECONDS)
    except (AttributeError, KeyError, ValueError):
        pass
    return DEFAULT_RETRY_SECONDS


class GeminiUtil:
    def __init__(self, api_key):
        self.client = genai.Client(api_key=api_key)

    def paraphrase_synopsis(self, synopsis):
        """Paraphrase a book synopsis with Gemini, or return None if the
        call fails -- a missing synopsis shouldn't block storing the rest
        of the review. Retries on rate limiting (429), honoring the
        server-suggested backoff when it's given."""
        for attempt in range(MAX_RETRIES):
            try:
                response = self.client.models.generate_content(
                    model=MODEL,
                    contents=synopsis,
                    config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT),
                )
                return response.text
            except errors.ClientError as e:
                if e.code == 429 and attempt < MAX_RETRIES - 1:
                    delay = _retry_delay_seconds(e)
                    print(f'Gemini rate limited, retrying in {delay:.0f}s ({attempt + 1}/{MAX_RETRIES})')
                    time.sleep(delay)
                    continue
                print(f'Gemini paraphrase failed: {e}')
                return None
            except Exception as e:
                print(f'Gemini paraphrase failed: {e}')
                return None
