import html
import json
import re
import urllib.parse
import urllib.request

SEARCH_URL = 'https://www.googleapis.com/books/v1/volumes'
USER_AGENT = 'spark.wiki backend (https://spark.wiki)'

# Google Books descriptions are HTML fragments (<p>, <br>, <b>, ...). We
# store/display plain text, so paragraph/line breaks become newlines (a
# blank line between paragraphs, a single one within) and every other tag
# is dropped rather than rendered.
PARAGRAPH_BREAK_PATTERN = re.compile(r'</p>', re.IGNORECASE)
LINE_BREAK_PATTERN = re.compile(r'<br\s*/?>', re.IGNORECASE)
TAG_PATTERN = re.compile(r'<[^>]+>')

EMPTY_METADATA = {'cover_url': None, 'description': None, 'genres': []}


class GoogleBooksUtil:
    def find_book_metadata(self, title, author):
        """Search Google Books by title/author and return the cover image
        URL, synopsis, and genre tags of the first result, or empty
        defaults if there isn't a match. Assumes the first result is
        correct -- no disambiguation."""
        params = {'q': f'intitle:{title} inauthor:{author}', 'maxResults': 1}
        url = f'{SEARCH_URL}?{urllib.parse.urlencode(params)}'
        request = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})

        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                data = json.load(response)
        except Exception as e:
            print(f'Google Books search failed for "{title}" by {author}: {e}')
            return dict(EMPTY_METADATA)

        items = data.get('items', [])
        if not items:
            return dict(EMPTY_METADATA)

        volume_info = items[0].get('volumeInfo', {})

        image_links = volume_info.get('imageLinks', {})
        thumbnail = image_links.get('thumbnail') or image_links.get('smallThumbnail')
        # Google serves cover thumbnails over http by default; upgrade to
        # https so we're not making a mixed-content request server-side.
        cover_url = thumbnail.replace('http://', 'https://', 1) if thumbnail else None

        return {
            'cover_url': cover_url,
            'description': self._clean_description(volume_info.get('description')),
            'genres': self._parse_genres(volume_info.get('categories', [])),
        }

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

    @staticmethod
    def _clean_description(description):
        if not description:
            return None
        text = PARAGRAPH_BREAK_PATTERN.sub('\n\n', description)
        text = LINE_BREAK_PATTERN.sub('\n', text)
        text = TAG_PATTERN.sub('', text)
        text = html.unescape(text)
        text = re.sub(r'\n{3,}', '\n\n', text).strip()
        return text or None

    @staticmethod
    def _parse_genres(categories):
        # Google Books categories are BISAC-style slash-delimited strings
        # (e.g. "Fiction / Thrillers / Suspense") rather than discrete tags,
        # so split each on '/' into individual genres, deduping while
        # preserving the order they were first seen in.
        genres = []
        for category in categories:
            for part in category.split('/'):
                part = part.strip()
                if part and part not in genres:
                    genres.append(part)
        return genres
