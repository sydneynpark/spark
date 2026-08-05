# Backend



## Local development

Requirements:
* [uv](https://docs.astral.sh/uv/), which manages both the Python 3.12 interpreter (pinned in `.python-version`) and dependencies (declared in `pyproject.toml`, locked in `uv.lock`).

```ps
uv sync
```

This creates `.venv` and installs the dependencies declared in `pyproject.toml` into it.

To run the local API server:

```ps
uv run run_local.py
```

## Zipping for upload to Lambda

```
rm -r .build
mkdir .build/packages
uv export --no-dev --no-hashes -o .build/requirements.txt
uv pip install --target .build/packages -r .build/requirements.txt
cp src/*.py .build/packages
cp -r src/handlers/. .build/packages/handlers
cp -r src/utils/. .build/packages/utils

$compress = @{
  Path = ".build/packages/*"
  CompressionLevel = "Fastest"
  DestinationPath = ".build/lambda.zip"
}
Compress-Archive @compress -Force
```

Upload the resulting `lambda.zip` file to Lambda. (`deploy.py`/`deploy.ps1` does all of this for you — see the root [deploy.md](../deploy.md).)
