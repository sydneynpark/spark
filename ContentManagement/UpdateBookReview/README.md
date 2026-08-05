# Update Book Review lambda

This lambda reads a book review stored in S3 (see `sample-data/books` for the file format), and writes its metadata to a DynamoDB table so that reviews are queryable. This lambda is intended to be subscribed to S3 create and delete events on the `spark.wiki.books` bucket.

Book review files use YAML frontmatter for title, author, date reviewed, and rating elements, and a Markdown body for commentary. Commentary items are marked with `### <percentage>%` headings for a point in the book, or `### Overall` for the single commentary item that applies to the whole book.

The `spark.wiki.books` DynamoDB table is keyed by `s3_uri` (partition key), matching the convention used by `spark.wiki.photos`.


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
uv run python -m unittest discover test
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
