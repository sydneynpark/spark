# Update Blog Post Metadata lambda

This lambda reads the metadata of a blog post stored in S3, and writes that metadata to a DynamoDB table so that metadata is queryable. This lambda is intended to be subscribed to S3 update and delete events.


## Local development

Requirements:
* [uv](https://docs.astral.sh/uv/), which manages both the Python 3.12 interpreter (pinned in `.python-version`) and dependencies (declared in `pyproject.toml`, locked in `uv.lock`).

```ps
uv sync
```

This creates `.venv` and installs the dependencies declared in `pyproject.toml` into it.

## Running Tests

```ps
$env:PYTHONPATH = ".\src"
uv run python -m unittest test\test_markdown_util.py
```

## Zipping for upload to Lambda


```
mkdir .build/packages
uv export --no-dev --no-hashes -o .build/requirements.txt
uv pip install --target .build/packages -r .build/requirements.txt
cp src/*.py .build/packages

$compress = @{
  Path = ".build/packages/*"
  CompressionLevel = "Fastest"
  DestinationPath = ".build/lambda.zip"
}
Compress-Archive @compress -Force
```

Upload the resulting `lambda.zip` file to Lambda. (`deploy.py`/`deploy.ps1` does all of this for you — see the root [deploy.md](../../deploy.md).)
