import unittest
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from decimal import Decimal
from book_review_util import BookReviewUtil

class TestBookReviewUtil(unittest.TestCase):

    def setUp(self):
        test_file_path = os.path.join(os.path.dirname(__file__), 'resources', 'sample-book-review.md')
        with open(test_file_path, 'r', encoding='utf-8') as f:
            self.markdown_content = f.read()
        self.book_review = BookReviewUtil().parse(self.markdown_content)

    def test_metadata_parsing(self):
        self.assertEqual(self.book_review.title, 'Project Hail Mary')
        self.assertEqual(self.book_review.author, 'Andy Weir')
        self.assertEqual(self.book_review.date_reviewed, '2026-07-20')

    def test_rating_elements_parsing(self):
        self.assertEqual(len(self.book_review.rating_elements), 4)

        plot = self.book_review.rating_elements[0]
        self.assertEqual(plot['name'], 'Plot')
        self.assertEqual(plot['weight'], 5)
        self.assertEqual(plot['rating'], 9)
        self.assertIn('mystery unfolds naturally', plot['elaboration'])

        characters = self.book_review.rating_elements[1]
        self.assertEqual(characters['name'], 'Characters')
        self.assertNotIn('elaboration', characters)

    def test_commentary_parsing(self):
        commentary = self.book_review.commentary
        self.assertEqual(len(commentary), 3)

        self.assertEqual(commentary[0]['point'], '15')
        self.assertIn("Rocky's introduction", commentary[0]['text'])

        self.assertEqual(commentary[1]['point'], '62')

        self.assertIsNone(commentary[2]['point'])
        self.assertIn('page-turner', commentary[2]['text'])

    def test_to_item(self):
        item = self.book_review.to_item('s3://spark.wiki.books/Project Hail Mary.md')

        self.assertEqual(item['title'], 'Project Hail Mary')
        self.assertEqual(item['date'], 20260720)
        self.assertEqual(item['date_reviewed'], '2026-07-20')
        self.assertEqual(item['s3_uri'], 's3://spark.wiki.books/Project Hail Mary.md')
        self.assertEqual(len(item['rating_elements']), 4)
        self.assertEqual(len(item['commentary']), 3)

        self.assertEqual(item['commentary'][0]['point'], Decimal('15'))
        self.assertNotIn('point', item['commentary'][2])

        # cover_key is only set by the lambda after successfully storing a
        # downloaded Google Books cover, not by parsing the review file itself.
        self.assertNotIn('cover_key', item)

    def test_to_item_includes_cover_key_when_set(self):
        self.book_review.cover_key = 'covers/Project Hail Mary.jpg'
        item = self.book_review.to_item('s3://spark.wiki.books/Project Hail Mary.md')
        self.assertEqual(item['cover_key'], 'covers/Project Hail Mary.jpg')

    def test_cover_s3_key(self):
        self.assertEqual(self.book_review.cover_s3_key(), 'covers/Project Hail Mary.jpg')

    def test_date_as_number(self):
        self.assertEqual(self.book_review.date_as_number(), 20260720)

if __name__ == '__main__':
    unittest.main()
