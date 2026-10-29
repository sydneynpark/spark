# Sample data

The content the local stack (see the [README](../README.md)) starts with.
Each time its emulated AWS starts, [devstack/seed.py](../devstack/seed.py)
uploads each folder to the bucket it stands in for, keeping its paths as
keys, and the buckets' triggers process it as they would in production --
filling the tables, and making the photos' thumbnails.

| Path | Uploaded to | Processed by |
| --- | --- | --- |
| `books/markdown/` | `spark.wiki.books` (`<title>.md`) | `UpdateBookReview`, unless in `books/table/` |
| `photos/originals/` | `spark.wiki.photos` (`birds/YYYY/MM/DD/<photo>.jpg`, and the rest in `photos/`) | `UpdatePhotoMetadata` |
| `posts/` | `spark.wiki.blog` (`YYYY/MM/DD/<post>.md`) | `UpdateBlogPostMetadata` |

The book reviews are a snapshot of the ones live on spark.wiki, already
processed -- covers, genres, and synopses included -- so they're loaded as they
are, rather than processed again:

| Path | Loaded into |
| --- | --- |
| `books/table/` | `spark.wiki.books` table, one item per file, as the live API serves it |
| `books/covers/` | `spark.wiki.books/covers/`, from https://books.spark.wiki |

Refresh them from the live site with `./dev snapshot-books`, then
`./dev reseed` to load them. Review files aren't public, so it writes one from
the live item, in the admin page's format, for any live review whose file is
missing or out of date.

The bird photos are a selection of the ones live on spark.wiki, shrunk to at most
2048 pixels across, but with the keywords and capture dates
`UpdatePhotoMetadata` reads still in them. Change the selection in
[devstack/snapshot_live_birds.py](../devstack/snapshot_live_birds.py), and
copy it with `./dev snapshot-birds`, then `./dev reseed` to load it.

The other (non-bird) photos, in `originals/photos/`, are placeholders, drawn
rather than taken. Only the first has a capture date (EXIF); the rest get
theirs from their folders.

Content added locally, e.g. through the admin page, goes to the emulated
buckets, not here, so it's gone once the stack stops.

`photos/selected.csv` is an export of some photo table items, which nothing
reads.
