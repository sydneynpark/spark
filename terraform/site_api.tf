# The site's API, https://api.spark.wiki: the backend's ContentAPI Lambda,
# behind an API Gateway REST API that proxies every request to it.

module "content_api" {
  source = "./modules/python_lambda"

  function_name = "ContentAPI"
  project_dir   = "${path.root}/../backend"
  memory_size   = 128
  timeout       = 45

  role_name            = "ContentAPI-role-rab0br82"
  role_path            = "/service-role/"
  permissions_boundary = local.workload_boundary_arn
  policy               = data.aws_iam_policy_document.content_api.json
}

data "aws_iam_policy_document" "content_api" {
  source_policy_documents = [data.aws_iam_policy_document.decrypt_parameters.json]

  statement {
    sid     = "ReadTables"
    actions = ["dynamodb:GetItem", "dynamodb:Query", "dynamodb:Scan"]
    resources = [
      aws_dynamodb_table.books.arn,
      aws_dynamodb_table.photos.arn,
      "${aws_dynamodb_table.photos.arn}/index/*",
    ]
  }

  statement {
    sid       = "ListPostsAndPhotos"
    actions   = ["s3:ListBucket"]
    resources = [aws_s3_bucket.content["blog"].arn, aws_s3_bucket.content["photos"].arn]
  }

  statement {
    sid       = "ReadPosts"
    actions   = ["s3:GetObject"]
    resources = ["${aws_s3_bucket.content["blog"].arn}/*"]
  }

  # The admin page's review publishing, and photo uploads (whose presigned
  # URLs carry this role's permissions) and folders.
  statement {
    sid     = "AdminUploads"
    actions = ["s3:PutObject"]
    resources = [
      "${aws_s3_bucket.content["books"].arn}/*",
      "${aws_s3_bucket.content["photos"].arn}/*",
    ]
  }

  statement {
    sid     = "ReadAdminLogin"
    actions = ["ssm:GetParameter"]
    resources = [
      "${local.ssm_parameter_arn_prefix}/AdminUsername",
      "${local.ssm_parameter_arn_prefix}/AdminPasswordHash",
      "${local.ssm_parameter_arn_prefix}/AdminTokenSecret",
    ]
  }
}

resource "aws_api_gateway_rest_api" "api" {
  name               = "api.spark.wiki"
  binary_media_types = ["*/*"]

  endpoint_configuration {
    types           = ["REGIONAL"]
    ip_address_type = "ipv4"
  }
}

# Every path but / goes to the Lambda, which does its own routing (and CORS).
resource "aws_api_gateway_resource" "proxy" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  parent_id   = aws_api_gateway_rest_api.api.root_resource_id
  path_part   = "{all+}"
}

resource "aws_api_gateway_method" "proxy" {
  rest_api_id   = aws_api_gateway_rest_api.api.id
  resource_id   = aws_api_gateway_resource.proxy.id
  http_method   = "ANY"
  authorization = "NONE"

  request_parameters = {
    "method.request.path.all" = true
  }
}

# Proxy integrations ignore method and integration responses, so there are
# none. (The console made a 200 integration response with a null template,
# which the provider fails to read; see README.md.)
resource "aws_api_gateway_integration" "proxy" {
  rest_api_id             = aws_api_gateway_rest_api.api.id
  resource_id             = aws_api_gateway_resource.proxy.id
  http_method             = aws_api_gateway_method.proxy.http_method
  type                    = "AWS_PROXY"
  integration_http_method = "POST"
  uri                     = module.content_api.invoke_arn
  passthrough_behavior    = "WHEN_NO_MATCH"
  content_handling        = "CONVERT_TO_TEXT"
  timeout_milliseconds    = 29000
  cache_key_parameters    = ["method.request.path.all"]
}

resource "aws_lambda_permission" "api" {
  # As the console named it (changing it replaces it).
  statement_id  = "d7be9d2e-a636-51e7-bb87-00c1c55fc32b"
  action        = "lambda:InvokeFunction"
  function_name = module.content_api.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.api.execution_arn}/*/*/*"
}

# Errors API Gateway returns itself (e.g. the Lambda timing out), with CORS
# headers so the browser lets the frontend read them.
resource "aws_api_gateway_gateway_response" "errors" {
  for_each = toset(["DEFAULT_4XX", "DEFAULT_5XX"])

  rest_api_id   = aws_api_gateway_rest_api.api.id
  response_type = each.value

  response_parameters = {
    "gatewayresponse.header.Access-Control-Allow-Headers" = "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'"
    "gatewayresponse.header.Access-Control-Allow-Methods" = "'GET'"
    "gatewayresponse.header.Access-Control-Allow-Origin"  = "'*'"
  }

  response_templates = {
    "application/json" = "{\"message\":$context.error.messageString}"
  }
}

resource "aws_api_gateway_deployment" "api" {
  rest_api_id = aws_api_gateway_rest_api.api.id

  # Redeploys whenever the API's configuration changes.
  triggers = {
    redeployment = sha1(jsonencode([
      aws_api_gateway_resource.proxy,
      aws_api_gateway_method.proxy,
      aws_api_gateway_integration.proxy,
      aws_api_gateway_gateway_response.errors,
    ]))
  }

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_api_gateway_stage" "live" {
  rest_api_id   = aws_api_gateway_rest_api.api.id
  deployment_id = aws_api_gateway_deployment.api.id
  stage_name    = "LIVE"

  xray_tracing_enabled = true
  # Its current setting, though there's no cache.
  cache_cluster_size = "0.5"
}

resource "aws_api_gateway_method_settings" "live" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  stage_name  = aws_api_gateway_stage.live.stage_name
  method_path = "*/*"

  settings {
    # Errors only. Never data_trace_enabled: it logs whole requests and
    # responses, admin passwords and tokens included.
    logging_level      = "ERROR"
    data_trace_enabled = false
    metrics_enabled    = false

    throttling_burst_limit = 5000
    throttling_rate_limit  = 10000

    caching_enabled                            = false
    cache_ttl_in_seconds                       = 300
    cache_data_encrypted                       = false
    require_authorization_for_cache_control    = true
    unauthorized_cache_control_header_strategy = "SUCCEED_WITH_RESPONSE_HEADER"
  }
}

# Where the stage's execution logs go, which API Gateway creates itself.
resource "aws_cloudwatch_log_group" "api_execution" {
  name              = "API-Gateway-Execution-Logs_${aws_api_gateway_rest_api.api.id}/${aws_api_gateway_stage.live.stage_name}"
  retention_in_days = 3
}

resource "aws_api_gateway_domain_name" "api" {
  domain_name              = "api.spark.wiki"
  regional_certificate_arn = aws_acm_certificate.wildcard.arn
  security_policy          = "TLS_1_2"

  endpoint_configuration {
    types           = ["REGIONAL"]
    ip_address_type = "ipv4"
  }
}

resource "aws_api_gateway_base_path_mapping" "api" {
  domain_name = aws_api_gateway_domain_name.api.domain_name
  api_id      = aws_api_gateway_rest_api.api.id
  stage_name  = aws_api_gateway_stage.live.stage_name
}

# API Gateway's account-wide settings: the role it writes execution logs
# with (for every API in the account and region; this is the only one).
resource "aws_api_gateway_account" "this" {
  cloudwatch_role_arn = aws_iam_role.api_gateway_logs.arn
}

resource "aws_iam_role" "api_gateway_logs" {
  name                 = "APIGateway_api.spark.wiki"
  description          = "Allows API Gateway to write execution logs."
  permissions_boundary = local.workload_boundary_arn

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "apigateway.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

# Exactly this one: it doesn't need to invoke the Lambda, which allows API
# Gateway to itself (aws_lambda_permission.api).
resource "aws_iam_role_policy_attachments_exclusive" "api_gateway_logs" {
  role_name   = aws_iam_role.api_gateway_logs.name
  policy_arns = ["arn:aws:iam::aws:policy/service-role/AmazonAPIGatewayPushToCloudWatchLogs"]
}

resource "aws_iam_role_policies_exclusive" "api_gateway_logs" {
  role_name    = aws_iam_role.api_gateway_logs.name
  policy_names = []
}
