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

    def test_lambda_for_blog_post_create_event(self):
        event = sample_events.UploadSamplePost

        self.mock_aws.get_s3_object = MagicMock(return_value=sample_events.SamplePostS3Object)

        result = lambda_function.lambda_handler(event, None)
        
        # Verify the lambda processed successfully
        self.assertEqual(result['statusCode'], 200)
        self.assertIn('metadata', result)
        
        # Verify it contains expected blog metadata
        metadata_str = result['metadata']
        self.assertIn('Hello World', metadata_str)
        self.assertIn('Sydney Park', metadata_str)
        self.assertIn('2025-07-29', metadata_str)

if __name__ == '__main__':
    unittest.main()