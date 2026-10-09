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
python -m unittest test\test_markdown_util.py
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

Every push builds this Lambda and plans deploying it, for you to approve -- see [terraform/README.md](../../terraform/README.md).
