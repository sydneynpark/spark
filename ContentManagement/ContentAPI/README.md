# Backend



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

## Zipping for upload to Lambda


```
mkdir .build/packages
pip install --target .build/packages -r src/requirements.txt
cp src/*.py .build/packages
cp src/handlers/* .build/packages/handlers
cp src/utils/* .build/packages/utils

$compress = @{
  Path = ".build/packages/*"
  CompressionLevel = "Fastest"
  DestinationPath = ".build/lambda.zip"
}
Compress-Archive @compress -Force
```

Upload the resulting `lambda.zip` file to Lambda.
