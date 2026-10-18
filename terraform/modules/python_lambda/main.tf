# A Python Lambda function deployed from one of this repo's Lambda projects:
# a directory with a .python-version, and the .build/lambda.zip that
# scripts/build_lambda.py packages from it. Along with its log group, and an
# execution role allowed to write to it, plus whatever `policy` grants.

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
}

resource "aws_lambda_function" "this" {
  function_name = var.function_name
  description   = var.description
  role          = aws_iam_role.this.arn

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

  # Lambda would otherwise create the log group itself, with no retention.
  depends_on = [aws_cloudwatch_log_group.this]
}

resource "aws_cloudwatch_log_group" "this" {
  name              = "/aws/lambda/${var.function_name}"
  retention_in_days = var.log_retention_days
}

resource "aws_iam_role" "this" {
  name        = var.role_name
  path        = var.role_path
  description = var.role_description

  # The deploy role can only create or change roles that carry this.
  permissions_boundary = var.permissions_boundary

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

data "aws_iam_policy_document" "this" {
  source_policy_documents = [var.policy]

  statement {
    sid       = "Logs"
    actions   = ["logs:CreateLogStream", "logs:PutLogEvents"]
    resources = ["${aws_cloudwatch_log_group.this.arn}:*"]
  }
}

resource "aws_iam_role_policy" "this" {
  name   = var.function_name
  role   = aws_iam_role.this.id
  policy = data.aws_iam_policy_document.this.json
}

# The role's permissions are exactly the policy above: any other inline
# policy is deleted, and any managed policy detached.
resource "aws_iam_role_policies_exclusive" "this" {
  role_name    = aws_iam_role.this.name
  policy_names = [aws_iam_role_policy.this.name]
}

resource "aws_iam_role_policy_attachments_exclusive" "this" {
  role_name   = aws_iam_role.this.name
  policy_arns = []

  # Detach the old policies only once the new one is in place.
  depends_on = [aws_iam_role_policy.this]
}
