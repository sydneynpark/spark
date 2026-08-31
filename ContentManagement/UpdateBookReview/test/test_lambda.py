import unittest
from unittest.mock import MagicMock
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
import test.sample_events as sample_events
import lambda_function
import aws_util
import gemini_util
import google_books_util


class TestLambda(unittest.TestCase):

    def setUp(self) -> None:
        self.mock_aws = aws_util.AWSUtil()
        lambda_function.aws = self.mock_aws

        # No genre/synopsis/cover data by default -- individual tests opt
        # in. Setting these on lambda_function directly (rather than
        # leaving them None) means _get_google_books()/_get_gemini() never
        # try to fetch a real Parameter Store value during a test run.
        # find_cover_url is left real (it's pure logic over the volume_info
        # dict a test provides); only the network call is mocked.
        self.mock_google_books = google_books_util.GoogleBooksUtil('fake-api-key')
        self.mock_google_books.find_volume_info = MagicMock(return_value=None)
        self.mock_google_books.fetch_cover_image = MagicMock(return_value=b'fake-jpeg-bytes')
        lambda_function.google_books = self.mock_google_books

        self.mock_gemini = gemini_util.GeminiUtil('fake-api-key')
        self.mock_gemini.paraphrase_synopsis = MagicMock(return_value=None)
        lambda_function.gemini = self.mock_gemini

    def test_lambda_for_book_review_create_event(self):
        event = sample_events.UploadSampleBookReview

        self.mock_aws.get_s3_object = MagicMock(return_value=sample_events.SampleBookReviewS3Object())
        self.mock_aws.put_s3_object = MagicMock()
        self.mock_aws.store_book_review = MagicMock()
        self.mock_google_books.find_volume_info = MagicMock(return_value={
            'imageLinks': {'thumbnail': 'http://books.google.com/cover.jpg'},
        })

        result = lambda_function.lambda_handler(event, None)

        self.assertEqual(result['statusCode'], 200)
        self.assertIn('metadata', result)

        metadata_str = result['metadata']
        self.assertIn('Project Hail Mary', metadata_str)
        self.assertIn('Andy Weir', metadata_str)
        self.assertIn('2026-07-20', metadata_str)

        self.mock_google_books.find_volume_info.assert_called_once_with('Project Hail Mary', 'Andy Weir')
        # http:// from the API is upgraded to https:// before downloading.
        self.mock_google_books.fetch_cover_image.assert_called_once_with('https://books.google.com/cover.jpg')

        self.mock_aws.put_s3_object.assert_called_once_with(
            'spark.wiki.books', 'covers/Project Hail Mary.jpg', b'fake-jpeg-bytes')

        self.mock_aws.store_book_review.assert_called_once()
        args, _ = self.mock_aws.store_book_review.call_args
        s3_uri, book_review = args
        self.assertEqual(s3_uri, 's3://spark.wiki.books/Project Hail Mary.md')
        self.assertEqual(book_review.title, 'Project Hail Mary')
        self.assertEqual(book_review.cover_key, 'covers/Project Hail Mary.jpg')

    def test_lambda_stores_genres_and_paraphrased_synopsis(self):
        event = sample_events.UploadSampleBookReview

        self.mock_aws.get_s3_object = MagicMock(return_value=sample_events.SampleBookReviewS3Object())
        self.mock_aws.put_s3_object = MagicMock()
        self.mock_aws.store_book_review = MagicMock()
        self.mock_google_books.find_volume_info = MagicMock(return_value={
            'categories': ['Science Fiction', 'Space Opera'],
            'description': 'The original, copyrighted synopsis.',
        })
        self.mock_gemini.paraphrase_synopsis = MagicMock(return_value='A paraphrased synopsis.')

        lambda_function.lambda_handler(event, None)

        self.mock_google_books.find_volume_info.assert_called_once_with('Project Hail Mary', 'Andy Weir')
        self.mock_gemini.paraphrase_synopsis.assert_called_once_with('The original, copyrighted synopsis.')

        args, _ = self.mock_aws.store_book_review.call_args
        _, book_review = args
        self.assertEqual(book_review.genres, ['Science Fiction', 'Space Opera'])
        self.assertEqual(book_review.synopsis, 'A paraphrased synopsis.')
        # No imageLinks in this volume_info -- no cover should be stored.
        self.mock_aws.put_s3_object.assert_not_called()
        self.assertIsNone(book_review.cover_key)

    def test_lambda_skips_paraphrase_when_no_description_found(self):
        event = sample_events.UploadSampleBookReview

        self.mock_aws.get_s3_object = MagicMock(return_value=sample_events.SampleBookReviewS3Object())
        self.mock_aws.put_s3_object = MagicMock()
        self.mock_aws.store_book_review = MagicMock()
        self.mock_google_books.find_volume_info = MagicMock(return_value={'categories': ['Science Fiction']})

        lambda_function.lambda_handler(event, None)

        self.mock_gemini.paraphrase_synopsis.assert_not_called()
        args, _ = self.mock_aws.store_book_review.call_args
        _, book_review = args
        self.assertEqual(book_review.genres, ['Science Fiction'])
        self.assertIsNone(book_review.synopsis)

    def test_lambda_skips_cover_upload_when_no_image_links(self):
        event = sample_events.UploadSampleBookReview

        self.mock_aws.get_s3_object = MagicMock(return_value=sample_events.SampleBookReviewS3Object())
        self.mock_aws.put_s3_object = MagicMock()
        self.mock_aws.store_book_review = MagicMock()
        self.mock_google_books.find_volume_info = MagicMock(return_value={'categories': ['Science Fiction']})

        lambda_function.lambda_handler(event, None)

        self.mock_google_books.fetch_cover_image.assert_not_called()
        self.mock_aws.put_s3_object.assert_not_called()
        args, _ = self.mock_aws.store_book_review.call_args
        _, book_review = args
        self.assertIsNone(book_review.cover_key)

    def test_lambda_skips_cover_upload_when_download_fails(self):
        event = sample_events.UploadSampleBookReview

        self.mock_aws.get_s3_object = MagicMock(return_value=sample_events.SampleBookReviewS3Object())
        self.mock_aws.put_s3_object = MagicMock()
        self.mock_aws.store_book_review = MagicMock()
        self.mock_google_books.find_volume_info = MagicMock(return_value={
            'imageLinks': {'thumbnail': 'http://books.google.com/cover.jpg'},
        })
        self.mock_google_books.fetch_cover_image = MagicMock(return_value=None)

        lambda_function.lambda_handler(event, None)

        self.mock_aws.put_s3_object.assert_not_called()
        args, _ = self.mock_aws.store_book_review.call_args
        _, book_review = args
        self.assertIsNone(book_review.cover_key)

    def test_lambda_still_stores_review_when_enrichment_fails(self):
        # A Google Books/Gemini failure (bad key, rate limit, ...) shouldn't
        # stop the review itself from being stored.
        event = sample_events.UploadSampleBookReview

        self.mock_aws.get_s3_object = MagicMock(return_value=sample_events.SampleBookReviewS3Object())
        self.mock_aws.put_s3_object = MagicMock()
        self.mock_aws.store_book_review = MagicMock()
        self.mock_google_books.find_volume_info = MagicMock(side_effect=Exception('rate limited'))

        result = lambda_function.lambda_handler(event, None)

        self.assertEqual(result['statusCode'], 200)
        self.mock_aws.store_book_review.assert_called_once()
        args, _ = self.mock_aws.store_book_review.call_args
        _, book_review = args
        self.assertEqual(book_review.genres, [])
        self.assertIsNone(book_review.synopsis)
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
        self.mock_google_books.find_volume_info.assert_not_called()

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
