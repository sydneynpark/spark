import re
import frontmatter

COMMENTARY_HEADING_PATTERN = re.compile(r'^###\s+(.+?)\s*$', re.MULTILINE)
COMMENTARY_POINT_PATTERN = re.compile(r'^(\d+(?:\.\d+)?)\s*%$')


def _parse_commentary(body):
    # Commentary items live under `### <percentage>%` headings for a point in
    # the book, or any other `###` heading (by convention `Overall`) for the
    # single commentary item that applies to the whole book.
    headings = list(COMMENTARY_HEADING_PATTERN.finditer(body))
    commentary = []
    for index, match in enumerate(headings):
        heading = match.group(1).strip()
        start = match.end()
        end = headings[index + 1].start() if index + 1 < len(headings) else len(body)
        text = body[start:end].strip()

        point_match = COMMENTARY_POINT_PATTERN.match(heading)
        point = float(point_match.group(1)) if point_match else None

        commentary.append({'point': point, 'text': text})
    return commentary


def parse_book_review(markdown_content, s3_uri=None):
    """Parse a book review markdown file (see sample-data/books) into the
    same shape the UpdateBookReview lambda stores in DynamoDB, but with
    plain int/float/str values instead of Decimal."""
    post = frontmatter.loads(markdown_content)
    metadata = post.metadata

    date_reviewed = str(metadata.get('date_reviewed', '') or '')
    digits = date_reviewed.replace('-', '')
    date_number = int(digits) if digits.isdigit() else 0

    rating_elements = []
    for element in metadata.get('rating_elements', []):
        item = {
            'name': element.get('name', ''),
            'weight': element.get('weight'),
            'rating': element.get('rating'),
        }
        if element.get('elaboration'):
            item['elaboration'] = element.get('elaboration').strip()
        rating_elements.append(item)

    return {
        # `or ''` covers both a missing key and a key present but empty
        # (e.g. `author:` with nothing after it, which YAML parses as None
        # rather than a missing key).
        'title': metadata.get('title', '') or '',
        'date': date_number,
        'date_reviewed': date_reviewed,
        'author': metadata.get('author', '') or '',
        's3_uri': s3_uri,
        'rating_elements': rating_elements,
        'commentary': _parse_commentary(post.content),
    }
