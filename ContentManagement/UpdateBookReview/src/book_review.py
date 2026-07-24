import re
from decimal import Decimal

COMMENTARY_HEADING_PATTERN = re.compile(r'^###\s+(.+?)\s*$', re.MULTILINE)
COMMENTARY_POINT_PATTERN = re.compile(r'^(\d+(?:\.\d+)?)\s*%$')


class BookReview:
    def __init__(self, post):
        metadata_dict = post.metadata
        self.title = metadata_dict.get('title', '')
        self.author = metadata_dict.get('author', '')
        # YAML parses an unquoted YYYY-MM-DD as a date object rather than a
        # string, since date_reviewed is written unquoted in review files.
        self.date_reviewed = str(metadata_dict.get('date_reviewed', '') or '')
        self.rating_elements = metadata_dict.get('rating_elements', [])
        self.commentary = self._parse_commentary(post.content)

    def _parse_commentary(self, body):
        # Commentary items live under `### <percentage>%` headings for a point
        # in the book, or any other `###` heading (by convention `Overall`)
        # for the single commentary item that applies to the whole book.
        headings = list(COMMENTARY_HEADING_PATTERN.finditer(body))
        commentary = []
        for index, match in enumerate(headings):
            heading = match.group(1).strip()
            start = match.end()
            end = headings[index + 1].start() if index + 1 < len(headings) else len(body)
            text = body[start:end].strip()

            point_match = COMMENTARY_POINT_PATTERN.match(heading)
            point = point_match.group(1) if point_match else None

            commentary.append({'point': point, 'text': text})
        return commentary

    def date_as_number(self):
        # The table's sort key ('date') is a Number, so YYYY-MM-DD is encoded
        # as an integer YYYYMMDD -- still human-readable and sorts correctly.
        digits = self.date_reviewed.replace('-', '')
        return int(digits) if digits.isdigit() else 0

    def to_item(self, s3_uri):
        rating_elements = []
        for element in self.rating_elements:
            item = {
                'name': element.get('name', ''),
                'weight': element.get('weight'),
                'rating': element.get('rating'),
            }
            if element.get('elaboration'):
                item['elaboration'] = element.get('elaboration').strip()
            rating_elements.append(item)

        commentary = []
        for entry in self.commentary:
            item = {'text': entry['text']}
            if entry['point'] is not None:
                item['point'] = Decimal(entry['point'])
            commentary.append(item)

        return {
            'title': self.title,
            'date': self.date_as_number(),
            'date_reviewed': self.date_reviewed,
            'author': self.author,
            's3_uri': s3_uri,
            'rating_elements': rating_elements,
            'commentary': commentary,
        }

    def __str__(self):
        return f"BookReview(title='{self.title}', author='{self.author}', date_reviewed='{self.date_reviewed}')"

    def __repr__(self):
        return self.__str__()

    def debug_print(self):
        print('=== Book Review Metadata ===')
        print(f'Title: {self.title or "No title"}')
        print(f'Author: {self.author or "No author"}')
        print(f'Date Reviewed: {self.date_reviewed or "No date"}')
        print(f'Rating Elements: {self.rating_elements}')
        print(f'Commentary Items: {len(self.commentary)}')
