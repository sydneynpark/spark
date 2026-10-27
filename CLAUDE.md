# spark.wiki

## Running the site

Run it with `./dev up` from the checkout you're working in (see README.md).
It prints this checkout's URL; `./dev url` prints it again. Each worktree gets
its own stack and port, so don't stop or reuse another checkout's, and don't
start servers on fixed ports outside it.

Everything AWS is emulated per stack: inspect or change it with `./dev aws`
(e.g. `./dev aws s3 ls s3://spark.wiki.photos/`,
`./dev aws dynamodb scan --table-name spark.wiki.books`), which can only reach
this stack's emulator. Content Lambda output is in `./dev logs lambdas`.
