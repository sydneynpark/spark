# The site's API, https://api.spark.wiki: the backend's Lambdas, behind an
# API Gateway REST API that proxies every request to one of them. ContentAPI
# serves the public site, and can only read; AdminAPI serves /admin/*, the
# admin page, and is the only one that can write.

module "content_api" {
  source = "./modules/python_lambda"

  function_name = "ContentAPI"
  project_dir   = "${path.root}/../backend"
  memory_size   = 128
  timeout       = 45

  permissions_boundary = local.workload_boundary_arn
  policy               = data.aws_iam_policy_document.content_api.json
}

data "aws_iam_policy_document" "content_api" {
  statement {
    sid     = "ReadTables"
    actions = ["dynamodb:GetItem", "dynamodb:Query", "dynamodb:Scan"]
    resources = [
      aws_dynamodb_table.books.arn,
      aws_dynamodb_table.photos.arn,
      "${aws_dynamodb_table.photos.arn}/index/*",
      aws_dynamodb_table.normal_photos.arn,
    ]
  }

  statement {
    sid       = "ListPosts"
    actions   = ["s3:ListBucket"]
    resources = [aws_s3_bucket.content["blog"].arn]
  }

  statement {
    sid       = "ReadPosts"
    actions   = ["s3:GetObject"]
    resources = ["${aws_s3_bucket.content["blog"].arn}/*"]
  }
}

# The same package as ContentAPI, with the admin app's entry point.
module "admin_api" {
  source = "./modules/python_lambda"

  function_name = "AdminAPI"
  project_dir   = "${path.root}/../backend"
  handler       = "admin_lambda_function.lambda_handler"
  memory_size   = 128
  # API Gateway gives up after 29 seconds anyway.
  timeout = 30

  permissions_boundary = local.workload_boundary_arn
  policy               = data.aws_iam_policy_document.admin_api.json
}

data "aws_iam_policy_document" "admin_api" {
  source_policy_documents = [data.aws_iam_policy_document.decrypt_parameters.json]

  statement {
    sid     = "ReadAdminLogin"
    actions = ["ssm:GetParameter"]
    resources = [
      "${local.ssm_parameter_arn_prefix}/AdminUsername",
      "${local.ssm_parameter_arn_prefix}/AdminPasswordHash",
      "${local.ssm_parameter_arn_prefix}/AdminTokenSecret",
    ]
  }

  # The photo uploader's folder browser.
  statement {
    sid       = "ListPhotos"
    actions   = ["s3:ListBucket"]
    resources = [aws_s3_bucket.content["photos"].arn]
  }

  # Review publishing, and photo uploads (whose presigned URLs carry this
  # role's permissions) and folders.
  statement {
    sid     = "Uploads"
    actions = ["s3:PutObject"]
    resources = [
      "${aws_s3_bucket.content["books"].arn}/*",
      "${aws_s3_bucket.content["photos"].arn}/*",
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

# /admin/* goes to AdminAPI instead: API Gateway prefers the more specific
# path. (/admin itself has no method, so it's a 403.)
resource "aws_api_gateway_resource" "admin" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  parent_id   = aws_api_gateway_rest_api.api.root_resource_id
  path_part   = "admin"
}

resource "aws_api_gateway_resource" "admin_proxy" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  parent_id   = aws_api_gateway_resource.admin.id
  path_part   = "{all+}"
}

resource "aws_api_gateway_method" "admin_proxy" {
  rest_api_id   = aws_api_gateway_rest_api.api.id
  resource_id   = aws_api_gateway_resource.admin_proxy.id
  http_method   = "ANY"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "admin_proxy" {
  rest_api_id             = aws_api_gateway_rest_api.api.id
  resource_id             = aws_api_gateway_resource.admin_proxy.id
  http_method             = aws_api_gateway_method.admin_proxy.http_method
  type                    = "AWS_PROXY"
  integration_http_method = "POST"
  uri                     = module.admin_api.invoke_arn
  content_handling        = "CONVERT_TO_TEXT"
  timeout_milliseconds    = 29000
}

# Signing in has a resource of its own, so that it can be throttled
# (aws_api_gateway_method_settings.admin_login): method settings can't name
# one with a greedy path, like {all+}. POST, and OPTIONS for the CORS
# preflight, since a request for /admin/login never falls back to
# /admin/{all+}.
resource "aws_api_gateway_resource" "admin_login" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  parent_id   = aws_api_gateway_resource.admin.id
  path_part   = "login"
}

resource "aws_api_gateway_method" "admin_login" {
  for_each = toset(["POST", "OPTIONS"])

  rest_api_id   = aws_api_gateway_rest_api.api.id
  resource_id   = aws_api_gateway_resource.admin_login.id
  http_method   = each.key
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "admin_login" {
  for_each = aws_api_gateway_method.admin_login

  rest_api_id             = aws_api_gateway_rest_api.api.id
  resource_id             = aws_api_gateway_resource.admin_login.id
  http_method             = each.value.http_method
  type                    = "AWS_PROXY"
  integration_http_method = "POST"
  uri                     = module.admin_api.invoke_arn
  content_handling        = "CONVERT_TO_TEXT"
  timeout_milliseconds    = 29000
}

resource "aws_lambda_permission" "admin_api" {
  statement_id  = "APIGatewayAdmin"
  action        = "lambda:InvokeFunction"
  function_name = module.admin_api.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.api.execution_arn}/*/*/admin/*"
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
      aws_api_gateway_resource.admin,
      aws_api_gateway_resource.admin_proxy,
      aws_api_gateway_method.admin_proxy,
      aws_api_gateway_integration.admin_proxy,
      aws_api_gateway_resource.admin_login,
      aws_api_gateway_method.admin_login,
      aws_api_gateway_integration.admin_login,
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

# Signing in, far below the stage's limits: it's only for one person, and
# each attempt deliberately takes a lot of CPU (password hashing). A flood of
# them would otherwise run up AdminAPI's bill, and take up the account's few
# concurrent Lambda executions, which the public API needs too. (The rest of
# /admin/* turns away requests without a valid token in milliseconds.) Method
# settings name a resource by its path with each / escaped as ~1.
resource "aws_api_gateway_method_settings" "admin_login" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  stage_name  = aws_api_gateway_stage.live.stage_name
  method_path = "${replace(aws_api_gateway_resource.admin_login.path, "/", "~1")}/${aws_api_gateway_method.admin_login["POST"].http_method}"

  settings {
    # As for */*, above.
    logging_level      = "ERROR"
    data_trace_enabled = false
    metrics_enabled    = false

    throttling_burst_limit = 3
    throttling_rate_limit  = 1
  }

  # Both update the stage, which fails if they do it at the same time.
  depends_on = [aws_api_gateway_method_settings.live]
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

  # API Gateway checks the role can write logs.
  depends_on = [aws_iam_role_policy_attachments_exclusive.api_gateway_logs]
}

# Under /site-workload/, like the Lambdas' roles (see
# modules/python_lambda).
resource "aws_iam_role" "api_gateway_logs" {
  name                  = "APIGatewayLogs"
  path                  = "/site-workload/"
  description           = "Allows API Gateway to write execution logs."
  permissions_boundary  = local.workload_boundary_arn
  force_detach_policies = true

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "apigateway.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })

  lifecycle {
    create_before_destroy = true
  }
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
