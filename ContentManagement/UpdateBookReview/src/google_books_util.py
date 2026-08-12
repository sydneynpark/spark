import json
import urllib.parse
import urllib.request

BASE_URL = 'https://www.googleapis.com/books/v1/volumes'
USER_AGENT = 'spark.wiki backend (https://spark.wiki)'

# Not every book has every size -- imageLinks commonly only has
# smallThumbnail/thumbnail. Prefer the largest one actually present.
IMAGE_SIZE_PREFERENCE = ['extraLarge', 'large', 'medium', 'small', 'thumbnail', 'smallThumbnail']


class GoogleBooksUtil:
    def __init__(self, api_key):
        self.api_key = api_key

    def find_volume_info(self, title, author):
        """Search Google Books by title/author, then fetch and return the
        full volumeInfo for the first match by its volume ID. Assumes the
        first search result is correct -- no disambiguation.

        The search endpoint's volumeInfo is a trimmed summary: categories
        collapse to one broad label (often just "Fiction", regardless of
        how specifically the book is actually categorized) and imageLinks
        is limited to the smallest couple of sizes. GET /v1/volumes/{id}
        returns the full BISAC category list and the complete set of cover
        sizes, so that's what this returns whenever the detail fetch
        succeeds -- falling back to the search summary otherwise.
        """
        params = {
            'q': f'intitle:{title} inauthor:{author}',
            'key': self.api_key,
            'maxResults': 1,
        }
        url = f'{BASE_URL}?{urllib.parse.urlencode(params)}'

        try:
            with urllib.request.urlopen(url, timeout=10) as response:
                data = json.load(response)
        except Exception as e:
            print(f'Google Books search failed for "{title}" by {author}: {e}')
            return None

        items = data.get('items', [])
        if not items:
            return None

        summary_info = items[0].get('volumeInfo', {})
        volume_id = items[0].get('id')
        if not volume_id:
            return summary_info

        return self._fetch_full_volume_info(volume_id) or summary_info

    def _fetch_full_volume_info(self, volume_id):
        url = f'{BASE_URL}/{volume_id}?{urllib.parse.urlencode({"key": self.api_key})}'

        try:
            with urllib.request.urlopen(url, timeout=10) as response:
                data = json.load(response)
            return data.get('volumeInfo', {})
        except Exception as e:
            print(f'Google Books volume detail fetch failed for {volume_id}: {e}')
            return None

    def find_cover_url(self, volume_info):
        """Return the highest-resolution cover image URL available on a
        volumeInfo dict, or None if it has no imageLinks at all."""
        image_links = volume_info.get('imageLinks', {})
        for size in IMAGE_SIZE_PREFERENCE:
            if size in image_links:
                # Google Books returns these as http:// -- upgrade to https.
                return image_links[size].replace('http://', 'https://', 1)
        return None

    def fetch_cover_image(self, cover_url):
        """Download the cover image itself, once, so we can store our own
        copy instead of hotlinking Google Books on every page view."""
        request = urllib.request.Request(cover_url, headers={'User-Agent': USER_AGENT})

        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                return response.read()
        except Exception as e:
            print(f'Failed to download Google Books cover from {cover_url}: {e}')
            return None
