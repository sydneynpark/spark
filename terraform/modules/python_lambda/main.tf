# A Python Lambda function deployed from one of this repo's Lambda projects:
# a directory with src/, a .python-version, and the .build/lambda.zip that
# scripts/build_lambda.py packages from them.

terraform {
  required_providers {
    aws = {
      source = "hashicorp/aws"
    }
  }
}

locals {
  package        = "${var.project_dir}/.build/lambda.zip"
  python_version = trimspace(file("${var.project_dir}/.python-version"))

  # A hash of what the package is built from. Unlike the zip's own hash, it
  # doesn't change with the build tooling (e.g. the metadata uv writes for
  # installed packages), only with the code, its locked dependencies, or the
  # Python version.
  source_hash = sha256(join("\n", concat(
    ["python ${local.python_version}"],
    [for path in sort(fileset("${var.project_dir}/src", "**")) : "${path} ${filesha256("${var.project_dir}/src/${path}")}"],
  )))
}

resource "aws_lambda_function" "this" {
  function_name = var.function_name
  description   = var.description
  role          = var.role_arn

  # The Python version build_lambda.py installed the dependencies for.
  runtime = "python${local.python_version}"
  handler = var.handler
  # build_lambda.py installs x86_64 wheels.
  architectures = ["x86_64"]
  layers        = var.layers

  memory_size = var.memory_size
  timeout     = var.timeout

  filename         = local.package
  source_code_hash = filebase64sha256(local.package)
}
