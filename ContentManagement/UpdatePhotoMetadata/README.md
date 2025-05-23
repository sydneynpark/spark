# Update Photo Metadata lambda

This lambda reads the metadata of a photo stored in S3, and writes that metadata to a DynamoDB table so that metadata is queryable. This lambda is intended to be subscribed to S3 update and delete events.

## Local development

```ps
python -m venv .env
.env\Scripts\Activate.ps1
pip install -U pip wheel
pip install -r src/requirements.txt
pip install -r test/requirements.txt
```

## Running Tests

```ps
$env:PYTHONPATH = ".\src"
python -m unittest test\test_lambda.py
```

## Zipping for upload to S3

```ps
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