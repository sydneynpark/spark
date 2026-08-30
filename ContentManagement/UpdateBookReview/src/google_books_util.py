import json
import urllib.parse
import urllib.request

BASE_URL = 'https://www.googleapis.com/books/v1/volumes'
USER_AGENT = 'spark.wiki backend (https://spark.wiki)'

# Not every book has every size -- imageLinks commonly only has
# smallThumbnail/thumbnail. Prefer the largest one actually present.
IMAGE_SIZE_PREFERENCE = ['extraLarge', 'large', 'medium', 'small', 'thumbnail', 'smallThumbnail']

# Google Books' `categories` field is raw BISAC subject headings (the book
# trade's standardized -- but publisher/shelving-oriented, not reader-facing
# -- classification), formatted as "TopLevel / Sub / Sub" paths. The leading
# segment is one of these two umbrella terms on nearly every novel, adding
# no genre information of its own, so it's dropped whenever a more specific
# segment follows it.
GENERIC_TOP_LEVEL_CATEGORIES = {'fiction', 'nonfiction', 'non-fiction'}


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

    def extract_genres(self, volume_info):
        """Turn the raw BISAC category paths on a volumeInfo dict (e.g.
        "Fiction / Mystery & Detective / Cozy / Animals") into a flat,
        deduped list of individual genre tags, e.g. "Mystery & Detective",
        "Cozy", "Animals". This is a heuristic, not a lookup -- Google
        Books' own website shows a further-simplified genre list, but that
        list is generated internally and isn't exposed anywhere in the API
        response, so splitting/deduping the BISAC paths we do get is the
        closest available approximation.
        """
        tags = []
        seen = set()
        for category in volume_info.get('categories', []):
            segments = [segment.strip() for segment in category.split(' / ') if segment.strip()]
            if len(segments) > 1 and segments[0].lower() in GENERIC_TOP_LEVEL_CATEGORIES:
                segments = segments[1:]
            for segment in segments:
                key = segment.lower()
                if key not in seen:
                    seen.add(key)
                    tags.append(segment)
        return tags

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
