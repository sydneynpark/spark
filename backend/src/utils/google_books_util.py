import json
import urllib.parse
import urllib.request

SEARCH_URL = 'https://www.googleapis.com/books/v1/volumes'
USER_AGENT = 'spark.wiki backend (https://spark.wiki)'


class GoogleBooksUtil:
    def find_cover_url(self, title, author):
        """Search Google Books by title/author and return the cover image
        URL of the first result, or None if there isn't one. Assumes the
        first result is correct -- no disambiguation."""
        params = {'q': f'intitle:{title} inauthor:{author}', 'maxResults': 1}
        url = f'{SEARCH_URL}?{urllib.parse.urlencode(params)}'
        request = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})

        try:
            with urllib.request.urlopen(request, timeout=10) as response:
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
            with urllib.request.urlopen(request, timeout=10) as response:
                return response.read()
        except Exception as e:
            print(f'Failed to download Google Books cover from {url}: {e}')
            return None
