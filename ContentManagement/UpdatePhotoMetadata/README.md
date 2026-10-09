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

## Dependencies

`src/requirements.in` lists the direct dependencies. `src/requirements.txt` is
generated from it, pinning every package (including transitive ones) to an
exact version and hash; local installs and the deployed Lambda both use it.
After editing `requirements.in`, regenerate it from this directory:

```
uv pip compile src/requirements.in --universal --python-version 3.12 --generate-hashes -o src/requirements.txt
```

Add `--upgrade` to also move everything to the latest versions.

## Deploying

Pushing to `master` deploys this Lambda -- see [terraform/README.md](../../terraform/README.md).

## Pillow

This Lambda relies on [the Klayers lambda layer](https://github.com/keithrozario/Klayers) for Pillow, attached in [terraform/content_lambdas.tf](../../terraform/content_lambdas.tf).

Lambda layer ARN for Pillow 11.0.0, built for Python 3.12 in us-east-1, is `arn:aws:lambda:us-east-1:770693421928:layer:Klayers-p312-pillow:2`
