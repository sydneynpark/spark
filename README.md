# spark
Personal website for spark.wiki

## Running it locally

Requirements: Docker (Docker Desktop, with Compose), and for `./dev aws`, the
AWS CLI.

```sh
./dev up
```

This starts the site, and stand-ins for the AWS services it runs on, then
prints the URL it's at: `http://localhost:<port>`, plus the same port at this
machine's LAN IP, for trying it on a phone. The admin page's login is
`admin` / `admin`.

Every checkout -- the main one, or any git worktree -- gets its own stack:
its own containers, its own emulated AWS data, and its own port (derived from
the checkout's path, so it stays the same across restarts). Several worktrees
can run at once without sharing anything. Set `SPARK_PORT` to pick a
different port.

| Command | |
| --- | --- |
| `./dev up` | Start (or update) this checkout's stack |
| `./dev url` | Print its URL |
| `./dev logs [service]` | Follow its logs |
| `./dev ps` | List its containers |
| `./dev reseed` | Start the emulated AWS over, from `sample-data/` |
| `./dev aws <args>` | The AWS CLI, against this stack's emulated AWS only |
| `./dev snapshot-books` | Copy the book reviews live on spark.wiki into `sample-data/` |
| `./dev snapshot-birds` | Copy a selection of the bird photos live on spark.wiki into `sample-data/` |
| `./dev down` | Stop it |
| `./dev destroy` | Stop it, and delete its volumes and images |
| `./dev compose <args>` | Any other `docker compose` command, for this stack |

### What's running

[compose.yaml](compose.yaml) runs, all behind one port:

* `edge`: nginx, standing in for API Gateway and the CloudFront CDNs
  (see [devstack/nginx.conf](devstack/nginx.conf) for its routes).
* `frontend`: the React dev server, with hot reloading.
* `content-api` and `admin-api`: the backend's two Lambdas
  ([backend/README.md](backend/README.md)), each a Flask dev server that
  reloads when its code changes.
* `aws`: [Moto](https://github.com/getmoto/moto), emulating S3, DynamoDB, SSM
  Parameter Store, and SQS, in memory.
* `seed`: sets the emulator up as `terraform/` sets up AWS, then loads
  [sample-data/](sample-data/README.md) into it
  ([devstack/seed.py](devstack/seed.py)).
* `lambdas`: runs the content Lambdas (`ContentManagement/`) on the buckets'
  S3 events, as S3 triggers them in AWS
  ([devstack/lambda_trigger.py](devstack/lambda_trigger.py)).

The backend and Lambdas run the same code they run in AWS: boto3 just sends
their AWS calls to the emulator. So uploading content -- through the admin
page, or with `./dev aws s3 cp` -- is processed as it is in production: a
photo gets its taxonomy, thumbnail, and table item, and a book review its
table item. The Python services run from the checkout's source, so edits
apply without a restart (or, for a Lambda, on its next event). Rebuild with
`./dev up` after changing a `requirements.txt`.

Nothing in the emulator is kept once it stops: each start sets it up again
from `sample-data/`.

### Book reviews

The stack starts with the book reviews live on spark.wiki, covers, genres,
and synopses included (see [sample-data/](sample-data/README.md)). To update
them from the live site:

```sh
./dev snapshot-books && ./dev reseed
```

Reviews added locally get no cover, genres, or synopsis unless
`UpdateBookReview` has its Google Books and Gemini API keys. To give it them,
set them when starting the stack:

```sh
GOOGLE_BOOKS_API_KEY=... GEMINI_API_KEY=... ./dev reseed
```

### Why Moto, rather than LocalStack

As of March 2026, LocalStack needs an account and an auth token to run, and
its free plan is for non-commercial use only. Moto is open source (Apache 2.0),
needs neither, and covers every service the site uses locally.
