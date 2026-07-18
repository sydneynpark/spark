import unittest
from unittest.mock import MagicMock
import test.sample_events as sample_events
import lambda_function
import aws_util


class TestLambda(unittest.TestCase):
    
    def setUp(self) -> None:
        self.mock_aws = aws_util.AWSUtil()
        lambda_function.aws = self.mock_aws

    def test_lambda_for_photo_create_event(self):
        event = sample_events.UploadTreeSwallowPhoto


        self.mock_aws.get_s3_object = MagicMock(return_value=sample_events.TreeSwallowPhotoS3Object)

        result = lambda_function.lambda_handler(event, None)
        assert 'Birds' in result

    def test_date_from_key(self):
        key = '2025/05/17/2025-05-17 095156 - Tree Swallow.jpg'
        assert lambda_function._date_from_key(key) == '2025-05-17'

    def test_date_from_key_with_no_date_path(self):
        assert lambda_function._date_from_key('uploads/tree-swallow.jpg') is None

if __name__ == '__main__':
    unittest.main()
