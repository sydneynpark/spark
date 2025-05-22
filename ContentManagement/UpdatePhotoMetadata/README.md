# Update Photo Metadata lambda

This lambda reads the metadata of a photo stored in S3, and writes that metadata to a DynamoDB table so that metadata is queryable. This lambda is intended to be subscribed to S3 update and delete events.


## Zipping for upload to S3

```
cd src
mkdir package
pip install --target ./package -r requirements.txt
cd package

$compress = @{
  Path = "./*", "../lambda_function.py"
  CompressionLevel = "Fastest"
  DestinationPath = "../lambda.zip"
}
Compress-Archive @compress
```

Upload the resulting `lambda.zip` file to S3.