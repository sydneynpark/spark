import copy
import filecmp
import unittest
from unittest.mock import MagicMock
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
import test.sample_events as sample_events
import lambda_function
import aws_util

SRC = os.path.join(os.path.dirname(__file__), '..', 'src')
BACKEND_POST_UTIL = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'backend', 'src', 'utils', 'post_util.py')


class TestLambda(unittest.TestCase):

    def setUp(self) -> None:
        self.mock_aws = aws_util.AWSUtil()
        self.mock_aws.store_post = MagicMock()
        self.mock_aws.delete_post = MagicMock()
        lambda_function.aws = self.mock_aws

    def test_stores_a_posts_metadata(self):
        self.mock_aws.get_s3_object = MagicMock(return_value=sample_events.SamplePostS3Object)

        result = lambda_function.lambda_handler(sample_events.UploadSamplePost, None)

        self.assertEqual(result['statusCode'], 200)
        item = self.mock_aws.store_post.call_args.args[0]
        self.assertEqual(item['s3_uri'], 's3://spark.wiki.blog/2025/07/29/hello-world.md')
        self.assertEqual(item['key'], '2025/07/29/hello-world.md')
        self.assertEqual((item['title'], item['slug'], item['date'], item['written']),
                         ('Hello World', 'hello-world', '2025-07-29', '2025-07-29'))
        self.assertEqual(item['tags'], ['technology', 'blog'])
        self.assertTrue(item['preview'].startswith('Hi everybody.'))
        self.assertEqual(item['last_modified'], '2025-07-29T00:00:00')
        # No body, and no photo, which it hasn't: nothing's stored as null.
        self.assertNotIn('content', item)
        self.assertNotIn('photo', item)

    def test_deletes_a_deleted_posts_metadata(self):
        event = copy.deepcopy(sample_events.UploadSamplePost)
        event['Records'][0]['eventName'] = 'ObjectRemoved:Delete'
        self.mock_aws.get_s3_object = MagicMock()

        lambda_function.lambda_handler(event, None)

        self.mock_aws.delete_post.assert_called_once_with('s3://spark.wiki.blog/2025/07/29/hello-world.md')
        self.mock_aws.get_s3_object.assert_not_called()

    def test_lambda_skips_drafts_and_their_photos(self):
        self.mock_aws.get_s3_object = MagicMock()
        for key in ('drafts%2F0123%2Fdraft.md', 'drafts%2F0123%2Fbirds%2Fphoto.jpg'):
            event = copy.deepcopy(sample_events.UploadSamplePost)
            event['Records'][0]['s3']['object']['key'] = key

            result = lambda_function.lambda_handler(event, None)

            self.assertEqual(result['statusCode'], 200)
            self.assertIsNone(result['item'])
        self.mock_aws.get_s3_object.assert_not_called()
        self.mock_aws.store_post.assert_not_called()

    def test_post_util_is_the_backends(self):
        # The admin page publishes and previews posts with the backend's
        # post_util, so the table's items must be made with the same one.
        self.assertTrue(
            filecmp.cmp(os.path.join(SRC, 'post_util.py'), BACKEND_POST_UTIL, shallow=False),
            'src/post_util.py differs from backend/src/utils/post_util.py: copy that over this.',
        )


if __name__ == '__main__':
    unittest.main()
