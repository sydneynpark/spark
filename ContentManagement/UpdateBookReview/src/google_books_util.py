import json
import re
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request

BASE_URL = 'https://www.googleapis.com/books/v1/volumes'
USER_AGENT = 'spark.wiki backend (https://spark.wiki)'

# Google's front end sheds load from traffic it doesn't like -- including,
# empirically, requests carrying urllib's default User-Agent -- with a 503
# rather than always queueing it, and occasionally a 429 if a quota's
# involved. Google's own client guidance is to retry both with backoff
# rather than treat them as hard failures.
RETRYABLE_STATUSES = {429, 503}
MAX_ATTEMPTS = 3
RETRY_BACKOFF_SECONDS = 1

# Width, in pixels, to have Google render covers at (see find_cover_url).
COVER_WIDTH = 800

# Google Books' `categories` field is raw BISAC subject headings (the book
# trade's standardized -- but publisher/shelving-oriented, not reader-facing
# -- classification), formatted as "TopLevel / Sub / Sub" paths. The leading
# segment is one of these two umbrella terms on nearly every novel, adding
# no genre information of its own, so it's dropped whenever a more specific
# segment follows it.
GENERIC_TOP_LEVEL_CATEGORIES = {'fiction', 'nonfiction', 'non-fiction'}

# Enough candidates for _pick_match to skip past study guides, summaries
# and other books that merely mention the title, without paging.
MAX_RESULTS = 10


def _normalize(text):
    """Lowercase, fold accents, and turn all punctuation into spaces, so
    "Dept. of Speculation" and "Dept of Speculation", or "Addie LaRue" and
    "Addie Larue", compare equal."""
    text = unicodedata.normalize('NFKD', text or '')
    text = ''.join(c for c in text if not unicodedata.combining(c))
    return ' '.join(re.sub(r'[^\w\s]', ' ', text.lower()).split())


def _surname(author):
    """Last word of the author's name. Searching on this alone sidesteps
    initials, which Google stores inconsistently ("V. E. Schwab" vs our
    "V.E. Schwab") and which Books' tokenizer won't match across."""
    words = _normalize(author).split()
    return words[-1] if words else ''


def _queries(title, author):
    """Plain keyword queries to try, most specific first. Deliberately no
    intitle:/inauthor: operators: observed in practice, Google Books
    returns zero results for many fielded queries that plainly should
    match ("tender is the flesh inauthor:bazterrica", "vicious
    inauthor:schwab", and every operator-only query), while keyword
    searches for the same books work. _pick_match checks title and author
    on our side instead. Punctuation is stripped so a stray "word:" can't
    be read as an operator. The full author name (initials included) ranks
    the right book far higher than the surname alone -- "appliance morgan"
    buries J. O. Morgan's Appliance under office-equipment catalogues."""
    normalized_title = _normalize(title)
    normalized_author = _normalize(author)

    queries = [
        f'{normalized_title} {normalized_author}'.strip(),
        f'"{normalized_title}" {_surname(author)}'.strip(),
        f'"{normalized_title}"',
    ]
    return list(dict.fromkeys(queries))


def _strip_article(normalized_title):
    return re.sub(r'^(the|a|an) ', '', normalized_title)


def _pick_match(items, title, author):
    """First result whose title starts with ours (tolerating subtitles
    Google appends, e.g. ": A Novel") and, if we know the author, whose
    authors include our surname. Google sometimes splits the subtitle into
    its own field, so title + subtitle is compared too, and a leading
    article is ignored on both sides.

    Among matches, retail editions (those with an ISBN) and ones with a
    cover image win over the rest, in Google's order otherwise. Without
    an ISBN, a match is usually a library scan (e.g. a 1972 Metamorphosis)
    whose "cover" is a photo of the title or copyright page. None if
    nothing qualifies."""
    wanted_title = _strip_article(_normalize(title))
    surname = _surname(author)

    matches = []
    for item in items:
        info = item.get('volumeInfo', {})
        found_title = _strip_article(_normalize(f"{info.get('title', '')} {info.get('subtitle', '')}"))
        if not wanted_title or not found_title.startswith(wanted_title):
            continue
        if surname and not any(surname in _normalize(a).split() for a in info.get('authors', [])):
            continue
        matches.append(item)

    if not matches:
        return None
    # max() keeps the first of equally ranked items, preserving Google's order.
    return max(matches, key=_edition_rank)


def _edition_rank(item):
    info = item.get('volumeInfo', {})
    has_isbn = any(i.get('type', '').startswith('ISBN') for i in info.get('industryIdentifiers', []))
    has_cover = bool(info.get('imageLinks'))
    return (has_isbn, has_cover)


class GoogleBooksUtil:
    def __init__(self, api_key):
        self.api_key = api_key

    def find_volume_info(self, title, author):
        """Search Google Books by title/author, then fetch and return the
        full volumeInfo for the best match by its volume ID.

        The search endpoint's volumeInfo is a trimmed summary: categories
        collapse to one broad label (often just "Fiction", regardless of
        how specifically the book is actually categorized) and imageLinks
        is limited to the smallest couple of sizes. GET /v1/volumes/{id}
        returns the full BISAC category list and the complete set of cover
        sizes, so that's what this returns whenever the detail fetch
        succeeds -- falling back to the search summary otherwise.

        Without langRestrict, Google Books will happily rank a foreign
        translation's edition above the English one (observed: an
        Indonesian description came back for an English-language title),
        and there's no per-request way to ask for the description in a
        given language -- it's a property of which edition matched. Since
        this whole pipeline assumes English throughout, the search is tried
        restricted to English-language editions first. Obscure titles and
        books translated *into* English (where an English edition may not
        exist on Google Books at all) can come up empty under that
        restriction, so a second, unrestricted search is tried before
        giving up -- some match (even non-English) still gets a cover and
        genres, and Gemini is instructed to translate the synopsis to
        English regardless of source language.

        Within each language pass, a few keyword queries are tried in turn
        (see _queries). Results are vetted by _pick_match rather than
        blindly taking the first one, since keyword search often ranks
        study guides, summaries or unrelated books first.
        """
        item = self._find_item(title, author, lang_restrict='en')
        if item is None:
            return None
        if not item:
            print(f'No English-language Google Books match for "{title}" by {author}; retrying without a language restriction')
            item = self._find_item(title, author, lang_restrict=None)
        if not item:
            return None

        summary_info = item.get('volumeInfo', {})
        volume_id = item.get('id')
        if not volume_id:
            return summary_info

        return self._fetch_full_volume_info(volume_id) or summary_info

    def _find_item(self, title, author, lang_restrict):
        """Try each query from _queries in turn and return the first
        acceptable search result. Returns {} if every search succeeded but
        none matched, or None if a request failed outright (same
        distinction as _search)."""
        for query in _queries(title, author):
            items = self._search(query, title, author, lang_restrict)
            if items is None:
                return None
            item = _pick_match(items, title, author)
            if item:
                return item
        return {}

    def _search(self, query, title, author, lang_restrict):
        """Run one search, optionally restricted to a language. Returns the
        items list (possibly empty, if the search succeeded but matched
        nothing), or None if the request itself failed -- distinguished so
        find_volume_info can tell "no match in this language" (worth
        retrying without the restriction) apart from "the request errored
        out" (not worth retrying at all)."""
        params = {
            'q': query,
            'key': self.api_key,
            'maxResults': MAX_RESULTS,
        }
        if lang_restrict:
            params['langRestrict'] = lang_restrict
        url = f'{BASE_URL}?{urllib.parse.urlencode(params)}'

        try:
            data = json.loads(self._fetch_with_retry(url))
        except Exception as e:
            print(f'Google Books search failed for "{title}" by {author}: {e}')
            return None

        return data.get('items', [])

    def _fetch_full_volume_info(self, volume_id):
        url = f'{BASE_URL}/{volume_id}?{urllib.parse.urlencode({"key": self.api_key})}'

        try:
            data = json.loads(self._fetch_with_retry(url))
            return data.get('volumeInfo', {})
        except Exception as e:
            print(f'Google Books volume detail fetch failed for {volume_id}: {e}')
            return None

    def find_cover_url(self, volume_info):
        """Return a large cover image URL for a volumeInfo dict, or None if
        it has no thumbnail to build one from.

        Only the thumbnail links are trusted to be the front cover. The
        detail endpoint's small/medium/large/extraLarge links render the
        preview at a higher zoom, which for publisher previews is often an
        interior page instead (observed: Tender Is the Flesh's extraLarge
        is its blank title page with the Scribner logo). Google's own
        fife=w<width> parameter re-renders the thumbnail at that width,
        so it gets the real cover at a usable size. edge=curl, which
        Google adds to some publisher thumbnails, draws a fake page curl
        on the corner, so it's removed."""
        image_links = volume_info.get('imageLinks', {})
        thumbnail = image_links.get('thumbnail') or image_links.get('smallThumbnail')
        if not thumbnail:
            return None

        # Google Books returns these as http:// -- upgrade to https.
        parts = urllib.parse.urlsplit(thumbnail.replace('http://', 'https://', 1))
        params = [(k, v) for k, v in urllib.parse.parse_qsl(parts.query) if k not in ('edge', 'zoom', 'fife')]
        params += [('zoom', '1'), ('fife', f'w{COVER_WIDTH}')]
        return urllib.parse.urlunsplit(parts._replace(query=urllib.parse.urlencode(params)))

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
        try:
            return self._fetch_with_retry(cover_url)
        except Exception as e:
            print(f'Failed to download Google Books cover from {cover_url}: {e}')
            return None

    def _fetch_with_retry(self, url):
        """GET url with a real User-Agent (Google's front end sheds
        urllib's default one under load) and retry on 429/503, which
        Google's client guidance treats as transient rather than final."""
        request = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})

        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                with urllib.request.urlopen(request, timeout=10) as response:
                    return response.read()
            except urllib.error.HTTPError as e:
                if e.code in RETRYABLE_STATUSES and attempt < MAX_ATTEMPTS:
                    time.sleep(RETRY_BACKOFF_SECONDS * attempt)
                    continue
                raise
