import unittest
from unittest.mock import MagicMock
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
import test.sample_events as sample_events
import lambda_function
import aws_util


class TestLambda(unittest.TestCase):

    def setUp(self) -> None:
        self.mock_aws = aws_util.AWSUtil()
        lambda_function.aws = self.mock_aws

    def test_lambda_for_book_review_create_event(self):
        event = sample_events.UploadSampleBookReview

        self.mock_aws.get_s3_object = MagicMock(return_value=sample_events.SampleBookReviewS3Object)
        self.mock_aws.store_book_review = MagicMock()

        result = lambda_function.lambda_handler(event, None)

        self.assertEqual(result['statusCode'], 200)
        self.assertIn('metadata', result)

        metadata_str = result['metadata']
        self.assertIn('Project Hail Mary', metadata_str)
        self.assertIn('Andy Weir', metadata_str)
        self.assertIn('2026-07-20', metadata_str)

        self.mock_aws.store_book_review.assert_called_once()
        args, _ = self.mock_aws.store_book_review.call_args
        s3_uri, book_review = args
        self.assertEqual(s3_uri, 's3://spark.wiki.books/Project Hail Mary.md')
        self.assertEqual(book_review.title, 'Project Hail Mary')

    def test_lambda_for_book_review_delete_event(self):
        event = sample_events.DeleteSampleBookReview

        self.mock_aws.delete_book_review = MagicMock()

        result = lambda_function.lambda_handler(event, None)

        self.assertEqual(result['statusCode'], 200)
        # The delete event's S3 key is "Project+Hail+Mary.md"; the title used
        # as the DynamoDB partition key is recovered from that filename.
        self.mock_aws.delete_book_review.assert_called_once_with('Project Hail Mary')

if __name__ == '__main__':
    unittest.main()
