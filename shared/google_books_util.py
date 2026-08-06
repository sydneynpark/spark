import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request

SEARCH_URL = 'https://www.googleapis.com/books/v1/volumes'
USER_AGENT = 'spark.wiki UpdateBookReview lambda (https://spark.wiki)'

# Keyless requests to Google Books are bucketed into a shared anonymous
# quota that's effectively zero -- an API key (free, no billing required)
# is what actually grants a real per-project daily quota.
API_KEY_ENV_VAR = 'GOOGLE_BOOKS_API_KEY'

# Google Books throttles unauthenticated requests (no API key) much more
# aggressively than Open Library did -- looping over even a modest number of
# books back-to-back (e.g. refreshBookReviews.py, or local dev's cold-start
# cache fill) can trip a 429 well within normal use. Retry with backoff
# rather than treating a rate limit as "this book has no cover".
MAX_RETRIES = 3
RETRY_BACKOFF_SECONDS = 2


def _open_with_retry(request):
    for attempt in range(MAX_RETRIES):
        try:
            return urllib.request.urlopen(request, timeout=10)
        except urllib.error.HTTPError as e:
            if e.code != 429 or attempt == MAX_RETRIES - 1:
                raise
            retry_after = e.headers.get('Retry-After')
            delay = float(retry_after) if retry_after else RETRY_BACKOFF_SECONDS * (attempt + 1)
            time.sleep(delay)


class GoogleBooksUtil:
    def find_cover_url(self, title, author):
        """Search Google Books by title/author and return the cover image
        URL of the first result, or None if there isn't one. Assumes the
        first result is correct -- no disambiguation."""
        params = {'q': f'intitle:{title} inauthor:{author}', 'maxResults': 1}
        api_key = os.environ.get(API_KEY_ENV_VAR)
        if api_key:
            params['key'] = api_key
        url = f'{SEARCH_URL}?{urllib.parse.urlencode(params)}'
        request = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})

        try:
            with _open_with_retry(request) as response:
                data = json.load(response)
        except Exception as e:
            print(f'Google Books search failed for "{title}" by {author}: {e}')
            return None

        items = data.get('items', [])
        if not items:
            return None

        image_links = items[0].get('volumeInfo', {}).get('imageLinks', {})
        thumbnail = image_links.get('thumbnail') or image_links.get('smallThumbnail')
        if not thumbnail:
            return None

        # Google serves cover thumbnails over http by default; upgrade to
        # https so we're not making a mixed-content request server-side.
        return thumbnail.replace('http://', 'https://', 1)

    def fetch_cover_image(self, url):
        """Download the cover image itself, once, so we can store our own
        copy instead of hotlinking Google Books on every page view."""
        request = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})

        try:
            with _open_with_retry(request) as response:
                return response.read()
        except Exception as e:
            print(f'Failed to download Google Books cover from {url}: {e}')
            return None
