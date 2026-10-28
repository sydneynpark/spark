import copy
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

    def test_lambda_skips_folder_placeholder(self):
        event = copy.deepcopy(sample_events.UploadTreeSwallowPhoto)
        event['Records'][0]['s3']['object']['key'] = 'birds%2F2025%2F05%2F17%2F'
        self.mock_aws.get_s3_object = MagicMock()

        result = lambda_function.lambda_handler(event, None)
        assert result == []
        self.mock_aws.get_s3_object.assert_not_called()

    def test_lambda_for_non_bird_photo_create_event(self):
        event = copy.deepcopy(sample_events.UploadTreeSwallowPhoto)
        event['Records'][0]['s3']['object']['key'] = 'photos%2F2025%2F05%2F17%2F2025-05-17%20095156%20-%20Tree%20Swallow.jpg'
        self.mock_aws.get_s3_object = MagicMock(return_value={
            'Body': sample_events.file_to_streamingbody('tree-swallow'),
        })
        self.mock_aws.dynamodb = MagicMock()
        self.mock_aws.put_s3_object = MagicMock()

        result = lambda_function.lambda_handler(event, None)

        # Just its date: no taxonomy, though the photo has keywords for one.
        expected = {
            's3_uri': 's3://spark.wiki.photos/photos/2025/05/17/2025-05-17 095156 - Tree Swallow.jpg',
            'date': '2025-05-17',
        }
        assert result == expected
        self.mock_aws.dynamodb.Table.assert_called_once_with('spark.wiki.normal-photos')
        self.mock_aws.dynamodb.Table.return_value.put_item.assert_called_once_with(Item=expected)
        bucket, key, _ = self.mock_aws.put_s3_object.call_args.args
        assert (bucket, key) == ('spark.wiki.thumbnails', 'thumbnail/photos/2025/05/17/2025-05-17 095156 - Tree Swallow.jpg')

    def test_lambda_skips_keys_outside_the_collections(self):
        for key in ['archive%2F2025%2F05%2F17%2Fold.jpg', '2025%2F05%2F17%2Fold.jpg']:
            event = copy.deepcopy(sample_events.UploadTreeSwallowPhoto)
            event['Records'][0]['s3']['object']['key'] = key
            self.mock_aws.get_s3_object = MagicMock()

            assert lambda_function.lambda_handler(event, None) == []
            self.mock_aws.get_s3_object.assert_not_called()

    def test_date_from_key(self):
        key = 'birds/2025/05/17/2025-05-17 095156 - Tree Swallow.jpg'
        assert lambda_function._date_from_key(key) == '2025-05-17'

    def test_date_from_key_with_no_date_path(self):
        assert lambda_function._date_from_key('uploads/tree-swallow.jpg') is None

if __name__ == '__main__':
    unittest.main()
