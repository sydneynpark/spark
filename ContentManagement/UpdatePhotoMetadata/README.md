# Update Photo Metadata lambda

This lambda reads the metadata of a photo stored in S3, and writes that metadata to a DynamoDB table so that metadata is queryable. This lambda is intended to be subscribed to S3 update and delete events.


## Local development

Requirements: 
* Python version 3.12 (this version is required for the Pillow Lambda layer and the Lambda runtime)

```ps
python -m venv .env
.env\Scripts\Activate.ps1
pip install -U pip wheel
pip install -r src/requirements.txt
pip install -r src/requirements.local.txt
pip install -r test/requirements.txt
```

## Running Tests

```ps
$env:PYTHONPATH = ".\src"
python -m unittest test\test_lambda.py
```

## Zipping for upload to S3


```
mkdir .build/packages
pip install --target .build/packages -r src/requirements.txt
cp src/*.py .build/packages

$compress = @{
  Path = ".build/packages/*"
  CompressionLevel = "Fastest"
  DestinationPath = ".build/lambda.zip"
}
Compress-Archive @compress -Force
```

Upload the resulting `lambda.zip` file to Lambda.

This Lambda relies on [the Klayers lambda layer](https://github.com/keithrozario/Klayers) for Pillow. 

Lambda layer ARN for Pillow 11.0.0, built for Python 3.12 in us-east-1, is `arn:aws:lambda:us-east-1:770693421928:layer:Klayers-p312-pillow:2`