# Sample data

Everything the site uses when run locally (`start_local.ps1`), standing in
for its S3 buckets and DynamoDB tables. Each folder mirrors the keys of what
it stands in for.

| Path | Stands in for | Read by | Written by |
| --- | --- | --- | --- |
| `books/markdown/` | `spark.wiki.books` bucket (`<title>.md`) | `UpdateBookReview/run_local.py` | Admin book review form |
| `books/covers/` | `spark.wiki.books/covers/` | Backend's local covers CDN | `UpdateBookReview/run_local.py` |
| `books/dynamo/` | `spark.wiki.books` table, one item per file | Backend | `UpdateBookReview/run_local.py`, admin book review form |
| `photos/originals/` | `spark.wiki.photos` bucket (`YYYY/MM/DD/<photo>.jpg`) | Backend's local photos CDN, `UpdatePhotoMetadata/run_local.py` | Admin photo uploader |
| `photos/thumbnails/` | `spark.wiki.thumbnails/thumbnail/` | Backend's local photos CDN | `UpdatePhotoMetadata/run_local.py` |
| `photos/photos.json` | `spark.wiki.photos` table | Backend | `UpdatePhotoMetadata/run_local.py` |
| `posts/` | `spark.wiki.blog` bucket (`YYYY/MM/DD/<post>.md`) | Backend | -- |

`books/covers/` and `books/dynamo/` are generated, so they're gitignored.
`photos/selected.csv` is an export of some photo table items, which nothing
reads.
