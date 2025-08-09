# Update Blog Post Metadata lambda

This lambda reads the metadata of a blog post stored in S3, and writes that metadata to a DynamoDB table so that metadata is queryable. This lambda is intended to be subscribed to S3 update and delete events.


## Local development

Requirements: 
* Python version 3.12

```ps
python -m venv .env
.env\Scripts\Activate.ps1
pip install -U pip wheel
pip install -r src/requirements.txt
```

## Running Tests

```ps
$env:PYTHONPATH = ".\src"
python -m unittest test\test_blog_post_parsing.py
```

## Zipping for upload to Lambda


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
