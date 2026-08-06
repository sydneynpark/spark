import unittest
from unittest.mock import MagicMock
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
import test.sample_events as sample_events
import lambda_function
import aws_util
import google_books_util


class TestLambda(unittest.TestCase):

    def setUp(self) -> None:
        self.mock_aws = aws_util.AWSUtil()
        lambda_function.aws = self.mock_aws

        self.mock_google_books = google_books_util.GoogleBooksUtil()
        self.mock_google_books.find_book_metadata = MagicMock(return_value={
            'cover_url': 'https://books.google.com/thumb.jpg',
            'description': 'A stranded astronaut must save humanity.',
            'genres': ['Fiction', 'Science Fiction'],
        })
        self.mock_google_books.fetch_cover_image = MagicMock(return_value=b'fake-jpeg-bytes')
        lambda_function.google_books = self.mock_google_books

    def test_lambda_for_book_review_create_event(self):
        event = sample_events.UploadSampleBookReview

        self.mock_aws.get_s3_object = MagicMock(return_value=sample_events.SampleBookReviewS3Object)
        self.mock_aws.put_s3_object = MagicMock()
        self.mock_aws.store_book_review = MagicMock()

        result = lambda_function.lambda_handler(event, None)

        self.assertEqual(result['statusCode'], 200)
        self.assertIn('metadata', result)

        metadata_str = result['metadata']
        self.assertIn('Project Hail Mary', metadata_str)
        self.assertIn('Andy Weir', metadata_str)
        self.assertIn('2026-07-20', metadata_str)

        self.mock_google_books.find_book_metadata.assert_called_once_with('Project Hail Mary', 'Andy Weir')
        self.mock_google_books.fetch_cover_image.assert_called_once_with('https://books.google.com/thumb.jpg')

        self.mock_aws.put_s3_object.assert_called_once_with(
            'spark.wiki.books', 'covers/Project Hail Mary.jpg', b'fake-jpeg-bytes')

        self.mock_aws.store_book_review.assert_called_once()
        args, _ = self.mock_aws.store_book_review.call_args
        s3_uri, book_review = args
        self.assertEqual(s3_uri, 's3://spark.wiki.books/Project Hail Mary.md')
        self.assertEqual(book_review.title, 'Project Hail Mary')
        self.assertEqual(book_review.cover_key, 'covers/Project Hail Mary.jpg')
        self.assertEqual(book_review.description, 'A stranded astronaut must save humanity.')
        self.assertEqual(book_review.genres, ['Fiction', 'Science Fiction'])

    def test_lambda_skips_cover_upload_when_no_cover_found(self):
        event = sample_events.UploadSampleBookReview

        self.mock_aws.get_s3_object = MagicMock(return_value=sample_events.SampleBookReviewS3Object)
        self.mock_aws.put_s3_object = MagicMock()
        self.mock_aws.store_book_review = MagicMock()
        self.mock_google_books.find_book_metadata = MagicMock(return_value={
            'cover_url': None,
            'description': None,
            'genres': [],
        })

        lambda_function.lambda_handler(event, None)

        self.mock_google_books.fetch_cover_image.assert_not_called()
        self.mock_aws.put_s3_object.assert_not_called()
        args, _ = self.mock_aws.store_book_review.call_args
        _, book_review = args
        self.assertIsNone(book_review.cover_key)

    def test_lambda_ignores_cover_image_it_wrote_into_the_same_bucket(self):
        # The cover upload lands in the same spark.wiki.books bucket this
        # lambda is triggered from, so it must not try to process its own
        # cover images as review files (they aren't valid UTF-8 markdown).
        event = sample_events.UploadCoverImage

        self.mock_aws.get_s3_object = MagicMock()
        self.mock_aws.store_book_review = MagicMock()

        result = lambda_function.lambda_handler(event, None)

        self.assertEqual(result['statusCode'], 200)
        self.assertEqual(result['ignored'], 'covers/Project Hail Mary.jpg')
        self.mock_aws.get_s3_object.assert_not_called()
        self.mock_aws.store_book_review.assert_not_called()
        self.mock_google_books.find_book_metadata.assert_not_called()

    def test_lambda_for_book_review_delete_event(self):
        event = sample_events.DeleteSampleBookReview

        self.mock_aws.delete_book_review = MagicMock()
        self.mock_aws.delete_s3_object = MagicMock()

        result = lambda_function.lambda_handler(event, None)

        self.assertEqual(result['statusCode'], 200)
        # The delete event's S3 key is "Project+Hail+Mary.md"; the title used
        # as the DynamoDB partition key is recovered from that filename.
        self.mock_aws.delete_book_review.assert_called_once_with('Project Hail Mary')
        self.mock_aws.delete_s3_object.assert_called_once_with(
            'spark.wiki.books', 'covers/Project Hail Mary.jpg')

if __name__ == '__main__':
    unittest.main()
