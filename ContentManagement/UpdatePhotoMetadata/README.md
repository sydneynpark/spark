# Update Photo Metadata lambda

This lambda reads the metadata of a photo stored in S3, and writes that metadata to a DynamoDB table so that metadata is queryable. This lambda is intended to be subscribed to S3 update and delete events.


## Local development

Requirements:
* [uv](https://docs.astral.sh/uv/), which manages both the Python 3.12 interpreter (pinned in `.python-version` — this version is required for the Pillow Lambda layer and the Lambda runtime) and dependencies.

```ps
uv sync
```

`pyproject.toml` splits dependencies the same way `src/requirements.txt`, `src/requirements.local.txt`, and `test/requirements.txt` used to: `dependencies` (boto3, defusedxml) are what actually ship in the Lambda zip, while the `dev` group (Pillow, botocore) is only needed locally — Pillow because prod gets it from a Lambda layer instead, and botocore to build fake `StreamingBody` objects in tests. `uv sync` installs both by default.

## Running Tests

```ps
$env:PYTHONPATH = ".\src"
uv run python -m unittest test\test_lambda.py
```

## Zipping for upload to Lambda


```
rm -r .build
mkdir .build/packages
uv export --no-dev --no-hashes -o .build/requirements.txt
uv pip install --target .build/packages -r .build/requirements.txt
cp src/*.py .build/packages
cp "src/Bird keywords.txt" .build/packages

$compress = @{
  Path = ".build/packages/*"
  CompressionLevel = "Fastest"
  DestinationPath = ".build/lambda.zip"
}
Compress-Archive @compress -Force
```

Upload the resulting `lambda.zip` file to Lambda. (`deploy.py`/`deploy.ps1` does all of this for you — see the root [deploy.md](../../deploy.md).)

This Lambda relies on [the Klayers lambda layer](https://github.com/keithrozario/Klayers) for Pillow. 

Lambda layer ARN for Pillow 11.0.0, built for Python 3.12 in us-east-1, is `arn:aws:lambda:us-east-1:770693421928:layer:Klayers-p312-pillow:2`