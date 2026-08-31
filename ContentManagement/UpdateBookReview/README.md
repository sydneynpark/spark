# Update Book Review lambda

This lambda reads a book review stored in S3 (see `sample-data/books` for the file format), and writes its metadata to a DynamoDB table so that reviews are queryable. This lambda is intended to be subscribed to S3 create and delete events on the `spark.wiki.books` bucket.

Book review files use YAML frontmatter for title, author, date reviewed, and rating elements, and a Markdown body for commentary. Commentary items are marked with `### <percentage>%` headings for a point in the book, or `### Overall` for the single commentary item that applies to the whole book.

The `spark.wiki.books` DynamoDB table is keyed by `s3_uri` (partition key), matching the convention used by `spark.wiki.photos`.

For each review, the lambda also looks the book up on the Google Books API -- one lookup serves the cover image, genres (`categories`), and `description`, which is paraphrased into a copyright-safe `synopsis` using Gemini. (Cover art previously came from Open Library; Google Books now supplies it too, via `volumeInfo.imageLinks`, so that's one fewer external dependency.) This enrichment is best-effort -- a lookup or paraphrase failure logs and is skipped rather than blocking the review from being stored. It requires two values in AWS Parameter Store (SecureString), and `ssm:GetParameter` + `kms:Decrypt` permission on them for this lambda's execution role:

* `GoogleBooksAPIKey`
* `GeminiAPIKey`

(`GeminiProjectNumber` is not currently used -- the Gemini call uses the simple API-key-based Gemini Developer API, not Vertex AI, so no GCP project is needed.)

For a local batch test run against markdown files (without touching real AWS/DynamoDB), see `run_local.py`.


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
python -m unittest discover test
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
