"""Turns an admin-submitted book review payload into the same YAML
frontmatter + Markdown format used by sample-data/books/markdown/*.md, so it
can be uploaded to the spark.wiki.books S3 bucket and picked up by the
existing UpdateBookReview lambda exactly like a hand-authored review.

See ContentManagement/UpdateBookReview/src/book_review.py for the reader
side of this format.
"""
import re

import yaml

FRONT_MATTER_PATTERN = re.compile(r'\A---\s*\n(.*?)\n---\s*(?:\n|\Z)', re.DOTALL)
# The same commentary headings book_review.py reads: `### <percentage>%` for
# a point in the book, anything else (by convention `Overall`) for the book
# as a whole.
COMMENTARY_HEADING_PATTERN = re.compile(r'^###\s+(.+?)\s*$', re.MULTILINE)
COMMENTARY_POINT_PATTERN = re.compile(r'^(\d+(?:\.\d+)?)\s*%$')


def validate_review_payload(payload):
    """Return an error message string, or None if the payload is valid."""
    if not isinstance(payload, dict):
        return 'Request body must be a JSON object'
    if not (payload.get('title') or '').strip():
        return 'Title is required'
    if not (payload.get('author') or '').strip():
        return 'Author is required'
    if not (payload.get('date_reviewed') or '').strip():
        return 'Date reviewed is required'

    rating_elements = payload.get('rating_elements')
    if not isinstance(rating_elements, list) or not rating_elements:
        return 'At least one facet is required'
    for element in rating_elements:
        if not isinstance(element, dict) or not (element.get('name') or '').strip():
            return 'Each facet needs a name'
        weight = element.get('weight')
        if not isinstance(weight, (int, float)) or isinstance(weight, bool) or weight < 0:
            return 'Each facet needs a non-negative numeric weight'
        rating = element.get('rating')
        if not isinstance(rating, (int, float)) or isinstance(rating, bool) or not (0 <= rating <= 10):
            return 'Each facet rating must be a number between 0 and 10'
        if not isinstance(element.get('elaboration') or '', str):
            return 'A facet elaboration must be text'

    commentary = payload.get('commentary') or []
    if not isinstance(commentary, list):
        return 'Timeline entries must be a list'
    for entry in commentary:
        if not isinstance(entry, dict):
            return 'Invalid timeline entry'
        point = entry.get('point')
        if not isinstance(point, (int, float)) or isinstance(point, bool) or not (0 <= point <= 100):
            return 'Each timeline entry needs a percentage between 0 and 100'
        if not (entry.get('text') or '').strip():
            return 'Each timeline entry needs some text'

    return None


def build_review_markdown(payload):
    """Build the full '---\\n<yaml>---\\n<body>' file content for a review."""
    metadata = {
        'title': payload['title'].strip(),
        'author': payload['author'].strip(),
        'date_reviewed': payload['date_reviewed'].strip(),
        'rating_elements': [_rating_element(element) for element in payload['rating_elements']],
    }
    front_matter = yaml.safe_dump(metadata, sort_keys=False, allow_unicode=True)

    sections = []
    overall_review = (payload.get('overall_review') or '').strip()
    if overall_review:
        sections.append(f'### Overall\n{overall_review}')

    timeline = sorted(payload.get('commentary') or [], key=lambda entry: entry['point'])
    for entry in timeline:
        point_str = f"{entry['point']:g}"
        sections.append(f"### {point_str}%\n{entry['text'].strip()}")

    body = '\n## Commentary\n' + '\n\n'.join(sections) + '\n' if sections else ''

    return f'---\n{front_matter}---\n{body}'


def _rating_element(element):
    built = {
        'name': element['name'].strip(),
        'weight': element['weight'],
        'rating': element['rating'],
    }
    # The form has no field for these, but hand-written reviews can have
    # them, so editing one passes them back through rather than losing them.
    elaboration = (element.get('elaboration') or '').strip()
    if elaboration:
        built['elaboration'] = elaboration
    return built


def parse_review_markdown(markdown):
    """The reverse of build_review_markdown: a review file's content, as
    the payload that would build it. Used to fill in the admin form when
    editing a review, including ones written by hand."""
    match = FRONT_MATTER_PATTERN.match(markdown)
    metadata = (yaml.safe_load(match.group(1)) if match else None) or {}
    body = markdown[match.end():] if match else markdown

    rating_elements = []
    for element in metadata.get('rating_elements') or []:
        parsed = {
            'name': str(element.get('name') or ''),
            'weight': element.get('weight') or 0,
            'rating': element.get('rating') or 0,
        }
        if element.get('elaboration'):
            parsed['elaboration'] = str(element['elaboration']).strip()
        rating_elements.append(parsed)

    commentary = []
    overall = []
    headings = list(COMMENTARY_HEADING_PATTERN.finditer(body))
    for index, heading in enumerate(headings):
        end = headings[index + 1].start() if index + 1 < len(headings) else len(body)
        text = body[heading.end():end].strip()
        point_match = COMMENTARY_POINT_PATTERN.match(heading.group(1).strip())
        if point_match:
            point = float(point_match.group(1))
            commentary.append({'point': int(point) if point.is_integer() else point, 'text': text})
        else:
            overall.append(text)

    return {
        # `or ''` as in book_review.py: a key present but empty is None.
        'title': str(metadata.get('title') or ''),
        'author': str(metadata.get('author') or ''),
        # Unquoted YYYY-MM-DD comes back from YAML as a date object.
        'date_reviewed': str(metadata.get('date_reviewed') or ''),
        'rating_elements': rating_elements,
        'commentary': commentary,
        'overall_review': '\n\n'.join(overall),
    }
