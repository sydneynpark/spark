from datetime import datetime
import os
import botocore.response

current_dir = os.path.dirname(os.path.abspath(__file__))

def file_to_streamingbody(file_slug):
    file_path = os.path.join(current_dir, f'resources/{file_slug}.jpg')
    file_size = os.path.getsize(file_path)
    print(f'File size of {file_path} is {file_size}')
    f = open(file_path, 'rb')
    return botocore.response.StreamingBody(f, file_size)

UploadTreeSwallowPhoto = {
  "Records": [
    {
      "eventVersion": "2.0",
      "eventSource": "aws:s3",
      "awsRegion": "us-east-1",
      "eventTime": "1970-01-01T00:00:00.000Z",
      "eventName": "ObjectCreated:Put",
      "userIdentity": {
        "principalId": "EXAMPLE"
      },
      "requestParameters": {
        "sourceIPAddress": "127.0.0.1"
      },
      "responseElements": {
        "x-amz-request-id": "EXAMPLE123456789",
        "x-amz-id-2": "EXAMPLE123/5678abcdefghijklambdaisawesome/mnopqrstuvwxyzABCDEFGH"
      },
      "s3": {
        "s3SchemaVersion": "1.0",
        "configurationId": "testConfigRule",
        "bucket": {
          "name": "spark.wiki.photos",
          "ownerIdentity": {
            "principalId": "EXAMPLE"
          },
          "arn": "arn:aws:s3:::spark.wiki.photos"
        },
        "object": {
          "key": "2025%2F05%2F17%2F2025-05-17%20095156%20-%20Tree%20Swallow.jpg",
          "size": 6300000,
          "eTag": "0870ed374e8469daa5971927e9a43203",
          "sequencer": "0A1B2C3D4E5F678901"
        }
      }
    }
  ]
}

TreeSwallowPhoto = file_to_streamingbody('tree-swallow')

TreeSwallowPhotoS3Object = {
  'Body': TreeSwallowPhoto,
  'DeleteMarker': False,
  'AcceptRanges': 'string',
  'Expiration': 'string',
  'Restore': 'string',
  'LastModified': datetime(2025, 5, 21),
  'ETag': '0870ed374e8469daa5971927e9a43203',
  'ContentType': 'image/jpeg'
}

if __name__ == '__main__':
    streaming_body = file_to_streamingbody('tree-swallow')
    print(streaming_body)