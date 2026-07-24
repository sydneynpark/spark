import json
import urllib.parse
import urllib.request

SEARCH_URL = 'https://openlibrary.org/search.json'
COVER_URL_TEMPLATE = 'https://covers.openlibrary.org/b/id/{cover_id}-{size}.jpg'
USER_AGENT = 'spark.wiki backend (https://spark.wiki)'


class OpenLibraryUtil:
    def find_cover_id(self, title, author):
        """Search Open Library by title/author and return the cover ID of
        the first result, or None if there isn't one. Assumes the first
        result is correct -- no disambiguation."""
        params = {'title': title, 'author': author, 'limit': 1}
        url = f'{SEARCH_URL}?{urllib.parse.urlencode(params)}'
        request = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})

        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                data = json.load(response)
        except Exception as e:
            print(f'Open Library search failed for "{title}" by {author}: {e}')
            return None

        docs = data.get('docs', [])
        if not docs:
            return None

        return docs[0].get('cover_i')

    def fetch_cover_image(self, cover_id, size='L'):
        """Download the cover image itself, once, so we can store our own
        copy instead of hotlinking Open Library on every page view."""
        url = COVER_URL_TEMPLATE.format(cover_id=cover_id, size=size)
        request = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})

        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                return response.read()
        except Exception as e:
            print(f'Failed to download Open Library cover {cover_id}: {e}')
            return None
