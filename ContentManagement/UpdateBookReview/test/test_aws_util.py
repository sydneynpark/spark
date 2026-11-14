import unittest
from unittest.mock import MagicMock
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
import aws_util
from book_review_util import BookReviewUtil


class TestStoreBookReview(unittest.TestCase):

    def setUp(self):
        test_file_path = os.path.join(os.path.dirname(__file__), 'resources', 'sample-book-review.md')
        with open(test_file_path, 'r', encoding='utf-8') as f:
            self.book_review = BookReviewUtil().parse(f.read())

        self.table = MagicMock()
        self.aws = aws_util.AWSUtil()
        self.aws.dynamodb = MagicMock()
        self.aws.dynamodb.Table.return_value = self.table

    def test_removes_items_left_under_an_older_date_reviewed(self):
        # The review was first uploaded with a later date, then edited to
        # an earlier one (the sample's date_reviewed is 2026-07-20).
        self.table.query.return_value = {'Items': [
            {'title': 'Project Hail Mary', 'date': 20260720},
            {'title': 'Project Hail Mary', 'date': 20260801},
        ]}

        self.aws.store_book_review('s3://spark.wiki.books/Project Hail Mary.md', self.book_review)

        self.table.put_item.assert_called_once()
        self.table.delete_item.assert_called_once_with(Key={'title': 'Project Hail Mary', 'date': 20260801})

    def test_keeps_the_item_it_just_stored(self):
        self.table.query.return_value = {'Items': [{'title': 'Project Hail Mary', 'date': 20260720}]}

        self.aws.store_book_review('s3://spark.wiki.books/Project Hail Mary.md', self.book_review)

        self.table.delete_item.assert_not_called()


if __name__ == '__main__':
    unittest.main()
