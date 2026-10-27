"""
Copies the book reviews live on spark.wiki into sample-data/books, for the
local stack to start with (see sample-data/README.md): each review's table
item as the public API serves it, its cover from the books CDN, and its
review file. Run it with ./dev snapshot-books.

Review files aren't public, so one is written from the live item, in the
format the admin page publishes, for each live review that doesn't already
have one, or whose existing one no longer matches what's live. Review files
for reviews that aren't live are left alone.
"""

import contextlib
import io
import json
import shutil
import sys
import urllib.parse
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / 'backend' / 'src'))
sys.path.insert(0, str(REPO / 'ContentManagement' / 'UpdateBookReview' / 'src'))

from book_review_util import BookReviewUtil  # noqa: E402
from utils.book_review_builder import build_review_markdown  # noqa: E402

API_URL = 'https://api.spark.wiki'
COVERS_CDN_URL = 'https://books.spark.wiki'

BOOKS_DIR = REPO / 'sample-data' / 'books'
MARKDOWN_DIR = BOOKS_DIR / 'markdown'
TABLE_DIR = BOOKS_DIR / 'table'
COVERS_DIR = BOOKS_DIR / 'covers'

# What the API adds to each item, rather than reads from the table.
API_ONLY_FIELDS = ['star_rating']

# The fields of an item that come from its review file, rather than from
# UpdateBookReview's enrichment.
REVIEW_FIELDS = ['title', 'author', 'date', 'date_reviewed', 'rating_elements', 'commentary']


def fetch(url):
    request = urllib.request.Request(url, headers={'User-Agent': 'spark.wiki devstack snapshot'})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read()


def live_items():
    # The API lists the latest review of each title, as the site shows them.
    books = json.loads(fetch(f'{API_URL}/books?limit=10000'))['books']
    for book in books:
        for field in API_ONLY_FIELDS:
            book.pop(field, None)
    return sorted(books, key=lambda b: b['title'])


def review_fields(markdown, s3_uri):
    # Without the review it prints as it parses.
    with contextlib.redirect_stdout(io.StringIO()):
        item = BookReviewUtil().parse(markdown).to_item(s3_uri)
    # Numbers as the API serves them, e.g. Decimal('3') as 3.
    return json.loads(json.dumps({f: item[f] for f in REVIEW_FIELDS}, default=float))


def markdown_for(item):
    """A review file that UpdateBookReview reads back as `item`."""
    overall = [c['text'] for c in item['commentary'] if 'point' not in c]
    if len(overall) > 1:
        raise ValueError('has more than one overall commentary entry')
    markdown = build_review_markdown({
        'title': item['title'],
        'author': item['author'],
        'date_reviewed': item['date_reviewed'],
        'rating_elements': item['rating_elements'],
        'overall_review': overall[0] if overall else '',
        'commentary': [c for c in item['commentary'] if 'point' in c],
    })
    if review_fields(markdown, item['s3_uri']) != {f: item[f] for f in REVIEW_FIELDS}:
        raise ValueError("doesn't round-trip through a review file")
    return markdown


def review_file(item):
    key = urllib.parse.urlparse(item['s3_uri']).path.lstrip('/')
    return MARKDOWN_DIR / key


def main():
    items = live_items()
    print(f'Found {len(items)} live review(s)')

    # Made afresh, so reviews that are no longer live go too.
    for directory in [TABLE_DIR, COVERS_DIR]:
        shutil.rmtree(directory, ignore_errors=True)
        directory.mkdir(parents=True)
    MARKDOWN_DIR.mkdir(parents=True, exist_ok=True)

    written, kept, skipped = [], [], []
    for item in items:
        title = item['title']
        with open(TABLE_DIR / f'{title}.json', 'w', encoding='utf-8') as f:
            json.dump(item, f, indent=2, ensure_ascii=False, sort_keys=True)
            f.write('\n')

        if item.get('cover_key'):
            path = '/'.join(urllib.parse.quote(part) for part in item['cover_key'].split('/'))
            (BOOKS_DIR / item['cover_key']).write_bytes(fetch(f'{COVERS_CDN_URL}/{path}'))

        path = review_file(item)
        live_fields = {f: item[f] for f in REVIEW_FIELDS}
        if path.exists() and review_fields(path.read_text(encoding='utf-8'), item['s3_uri']) == live_fields:
            kept.append(title)
            continue
        try:
            path.write_text(markdown_for(item), encoding='utf-8')
            written.append(title)
        except ValueError as e:
            skipped.append(f'{title} ({e})')

    not_live = sorted(
        p.stem for p in MARKDOWN_DIR.glob('*.md')
        if p.stem not in {review_file(item).stem for item in items}
    )

    print(f'Wrote {len(items)} table item(s) to {TABLE_DIR.relative_to(REPO)}')
    print(f'Wrote {sum(1 for i in items if i.get("cover_key"))} cover(s) to {COVERS_DIR.relative_to(REPO)}')
    print(f'Review files in {MARKDOWN_DIR.relative_to(REPO)}: {len(kept)} already matched, {len(written)} written')
    for title in written:
        print(f'  wrote: {title}')
    for title in skipped:
        print(f'  NOT written: {title}')
    for title in not_live:
        print(f'  not live, left alone: {title}')


if __name__ == '__main__':
    main()
