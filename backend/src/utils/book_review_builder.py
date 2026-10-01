"""Turns an admin-submitted book review payload into the same YAML
frontmatter + Markdown format used by sample-data/books/markdown/*.md, so it
can be uploaded to the spark.wiki.books S3 bucket and picked up by the
existing UpdateBookReview lambda exactly like a hand-authored review.

See ContentManagement/UpdateBookReview/src/book_review.py for the reader
side of this format.
"""
import yaml


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
        'rating_elements': [
            {
                'name': element['name'].strip(),
                # Reviews store whole-number weights; the admin form already
                # rounds them, this just keeps other API callers consistent.
                'weight': round(element['weight']),
                'rating': element['rating'],
            }
            for element in payload['rating_elements']
        ],
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
