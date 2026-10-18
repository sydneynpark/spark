# The site's frontend, https://spark.wiki: frontend/build (built by
# .github/workflows/deploy.yml), uploaded to the bucket CloudFront serves the
# site from. Only changed files are uploaded, files no longer in the build
# are deleted, and CloudFront's cache is invalidated after any change.

locals {
  frontend_build = "${path.root}/../frontend/build"

  # Each file in the build, and its content type: null if its extension isn't
  # in content_types.
  frontend_files = {
    for path in fileset(local.frontend_build, "**") :
    path => lookup(local.content_types, lower(try(regex("\\.([^./]+)$", path)[0], "")), null)
  }

  content_types = {
    css   = "text/css"
    gif   = "image/gif"
    html  = "text/html"
    ico   = "image/x-icon"
    jpeg  = "image/jpeg"
    jpg   = "image/jpeg"
    js    = "text/javascript"
    json  = "application/json"
    map   = "application/json"
    png   = "image/png"
    svg   = "image/svg+xml"
    txt   = "text/plain"
    webp  = "image/webp"
    woff2 = "font/woff2"
  }
}

resource "aws_s3_object" "frontend" {
  for_each = local.frontend_files

  bucket       = aws_s3_bucket.frontend.id
  key          = each.key
  source       = "${local.frontend_build}/${each.key}"
  etag         = filemd5("${local.frontend_build}/${each.key}")
  content_type = each.value

  lifecycle {
    precondition {
      condition     = each.value != null
      error_message = "No content type for ${each.key}: add its extension to content_types in terraform/site_frontend.tf."
    }
  }

  # Ship API changes before UI that might call them.
  depends_on = [module.content_api]
}

resource "terraform_data" "frontend_release" {
  # Changes whenever any file is added, changed, or removed -- and, by
  # referencing every object, only once they've all been uploaded.
  input = { for key, object in aws_s3_object.frontend : key => object.etag }

  lifecycle {
    # Otherwise a missing or empty build would plan to delete the whole site.
    precondition {
      condition     = fileexists("${local.frontend_build}/index.html")
      error_message = "frontend/build has no index.html: build the frontend (npm run build) before applying."
    }

    action_trigger {
      events  = [after_create, after_update]
      actions = [action.aws_cloudfront_create_invalidation.frontend]
    }
  }
}

action "aws_cloudfront_create_invalidation" "frontend" {
  config {
    distribution_id = aws_cloudfront_distribution.frontend.id
    paths           = ["/*"]
  }
}

# Public, and served as a static website: CloudFront fetches from its website
# endpoint, over HTTP. (Unlike the content buckets, which are private behind
# origin access controls; see README.md.)
resource "aws_s3_bucket" "frontend" {
  bucket = "spark.wiki.frontend"

  lifecycle {
    prevent_destroy = true
  }
}

resource "aws_s3_bucket_public_access_block" "frontend" {
  bucket                  = aws_s3_bucket.frontend.id
  block_public_acls       = false
  ignore_public_acls      = false
  block_public_policy     = false
  restrict_public_buckets = false
}

resource "aws_s3_bucket_ownership_controls" "frontend" {
  bucket = aws_s3_bucket.frontend.id
  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}

resource "aws_s3_bucket_policy" "frontend" {
  bucket = aws_s3_bucket.frontend.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid       = "PublicReadGetObject"
      Effect    = "Allow"
      Principal = "*"
      Action    = "s3:GetObject"
      Resource  = "${aws_s3_bucket.frontend.arn}/*"
    }]
  })

  depends_on = [aws_s3_bucket_public_access_block.frontend]
}

resource "aws_s3_bucket_website_configuration" "frontend" {
  bucket = aws_s3_bucket.frontend.id

  index_document {
    suffix = "index.html"
  }

  # The frontend routes every other path itself.
  error_document {
    key = "index.html"
  }
}

resource "aws_cloudfront_distribution" "frontend" {
  aliases             = ["spark.wiki"]
  default_root_object = "index.html"
  enabled             = true
  is_ipv6_enabled     = true
  http_version        = "http2"
  price_class         = "PriceClass_All"

  origin {
    origin_id   = "spark.wiki.frontend.s3-website-us-east-1.amazonaws.com-mdrmorrlyue"
    domain_name = aws_s3_bucket_website_configuration.frontend.website_endpoint

    # Website endpoints only speak HTTP.
    custom_origin_config {
      http_port                = 80
      https_port               = 443
      origin_protocol_policy   = "http-only"
      origin_ssl_protocols     = ["SSLv3", "TLSv1", "TLSv1.1", "TLSv1.2"]
      origin_read_timeout      = 30
      origin_keepalive_timeout = 5
    }
  }

  default_cache_behavior {
    target_origin_id       = "spark.wiki.frontend.s3-website-us-east-1.amazonaws.com-mdrmorrlyue"
    viewer_protocol_policy = "redirect-to-https"
    allowed_methods        = ["GET", "HEAD"]
    cached_methods         = ["GET", "HEAD"]
    compress               = true
    cache_policy_id        = local.caching_optimized_policy_id
  }

  # The frontend's own routes (e.g. /books/...), which aren't files.
  dynamic "custom_error_response" {
    for_each = [403, 404]

    content {
      error_code            = custom_error_response.value
      response_code         = 200
      response_page_path    = "/index.html"
      error_caching_min_ttl = 10
    }
  }

  viewer_certificate {
    acm_certificate_arn      = aws_acm_certificate.apex.arn
    ssl_support_method       = "sni-only"
    minimum_protocol_version = "TLSv1.2_2021"
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  tags = {
    Name = "spark.wiki"
  }
}
