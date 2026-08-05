from datetime import datetime
import os
import botocore.response

current_dir = os.path.dirname(os.path.abspath(__file__))

def file_to_streamingbody(file_slug):
    file_path = os.path.join(current_dir, f'resources/{file_slug}.md')
    file_size = os.path.getsize(file_path)
    print(f'File size of {file_path} is {file_size}')
    f = open(file_path, 'rb')
    return botocore.response.StreamingBody(f, file_size)

UploadSampleBookReview = {
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
          "name": "spark.wiki.books",
          "ownerIdentity": {
            "principalId": "EXAMPLE"
          },
          "arn": "arn:aws:s3:::spark.wiki.books"
        },
        "object": {
          "key": "Project+Hail+Mary.md",
          "size": 630,
          "eTag": "d41d8cd98f00b204e9800998ecf8427e",
          "sequencer": "0A1B2C3D4E5F678901"
        }
      }
    }
  ]
}

DeleteSampleBookReview = {
  "Records": [
    {
      "eventVersion": "2.0",
      "eventSource": "aws:s3",
      "awsRegion": "us-east-1",
      "eventTime": "1970-01-01T00:00:00.000Z",
      "eventName": "ObjectRemoved:Delete",
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
          "name": "spark.wiki.books",
          "ownerIdentity": {
            "principalId": "EXAMPLE"
          },
          "arn": "arn:aws:s3:::spark.wiki.books"
        },
        "object": {
          "key": "Project+Hail+Mary.md",
          "size": 630,
          "eTag": "d41d8cd98f00b204e9800998ecf8427e",
          "sequencer": "0A1B2C3D4E5F678901"
        }
      }
    }
  ]
}

UploadCoverImage = {
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
          "name": "spark.wiki.books",
          "ownerIdentity": {
            "principalId": "EXAMPLE"
          },
          "arn": "arn:aws:s3:::spark.wiki.books"
        },
        "object": {
          "key": "covers%2FProject+Hail+Mary.jpg",
          "size": 57929,
          "eTag": "d41d8cd98f00b204e9800998ecf8427e",
          "sequencer": "0A1B2C3D4E5F678901"
        }
      }
    }
  ]
}

SampleBookReview = file_to_streamingbody('sample-book-review')

SampleBookReviewS3Object = {
  'Body': SampleBookReview,
  'DeleteMarker': False,
  'AcceptRanges': 'string',
  'Expiration': 'string',
  'Restore': 'string',
  'LastModified': datetime(2026, 7, 20),
  'ETag': 'd41d8cd98f00b204e9800998ecf8427e',
  'ContentType': 'text/markdown'
}
