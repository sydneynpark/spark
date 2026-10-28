# The CDNs the site loads content from: https://photos.spark.wiki (bird
# photos, and under /thumbnail/, their thumbnails),
# https://normal-photos.spark.wiki (the same, for normal photos), and
# https://books.spark.wiki (book covers). Each reads its private buckets with
# an origin access control, which the buckets' policies allow.

locals {
  # AWS's Managed-CachingOptimized cache policy.
  caching_optimized_policy_id = "658327ea-f89d-4fab-a63d-7e88639e58f6"
}

resource "aws_cloudfront_distribution" "photos" {
  aliases         = ["photos.spark.wiki"]
  enabled         = true
  is_ipv6_enabled = true
  http_version    = "http2"
  price_class     = "PriceClass_All"
  web_acl_id      = aws_wafv2_web_acl.cdn["photos"].arn

  origin {
    origin_id                = "spark.wiki.photos.s3.us-east-1.amazonaws.com-mqvwkkibcft"
    domain_name              = aws_s3_bucket.content["photos"].bucket_regional_domain_name
    origin_access_control_id = aws_cloudfront_origin_access_control.photos.id
  }

  origin {
    origin_id                = "spark.wiki.thumbnails.s3.us-east-1.amazonaws.com"
    domain_name              = aws_s3_bucket.content["thumbnails"].bucket_regional_domain_name
    origin_access_control_id = aws_cloudfront_origin_access_control.thumbnails.id
  }

  default_cache_behavior {
    target_origin_id       = "spark.wiki.photos.s3.us-east-1.amazonaws.com-mqvwkkibcft"
    viewer_protocol_policy = "redirect-to-https"
    allowed_methods        = ["GET", "HEAD"]
    cached_methods         = ["GET", "HEAD"]
    compress               = true
    cache_policy_id        = local.caching_optimized_policy_id
  }

  ordered_cache_behavior {
    path_pattern           = "/thumbnail/*"
    target_origin_id       = "spark.wiki.thumbnails.s3.us-east-1.amazonaws.com"
    viewer_protocol_policy = "redirect-to-https"
    allowed_methods        = ["GET", "HEAD"]
    cached_methods         = ["GET", "HEAD"]
    compress               = true
    cache_policy_id        = local.caching_optimized_policy_id
  }

  viewer_certificate {
    acm_certificate_arn      = aws_acm_certificate.wildcard.arn
    ssl_support_method       = "sni-only"
    minimum_protocol_version = "TLSv1.2_2021"
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  tags = {
    Name = "spark.wiki.photos"
  }
}

# Laid out like photos.spark.wiki, so the frontend builds the same paths for
# either. Normal photos' thumbnails are in the same bucket as bird photos',
# under normal-photos/ (so the same key in each photos bucket doesn't
# collide), which the origin path adds back.
resource "aws_cloudfront_distribution" "normal_photos" {
  aliases         = ["normal-photos.spark.wiki"]
  enabled         = true
  is_ipv6_enabled = true
  http_version    = "http2"
  price_class     = "PriceClass_All"
  # photos.spark.wiki's: a web ACL can protect more than one distribution.
  web_acl_id = aws_wafv2_web_acl.cdn["photos"].arn

  origin {
    origin_id                = "spark.wiki.normal-photos"
    domain_name              = aws_s3_bucket.content["normal_photos"].bucket_regional_domain_name
    origin_access_control_id = aws_cloudfront_origin_access_control.normal_photos.id
  }

  origin {
    origin_id                = "spark.wiki.thumbnails/normal-photos"
    domain_name              = aws_s3_bucket.content["thumbnails"].bucket_regional_domain_name
    origin_path              = "/normal-photos"
    origin_access_control_id = aws_cloudfront_origin_access_control.thumbnails.id
  }

  default_cache_behavior {
    target_origin_id       = "spark.wiki.normal-photos"
    viewer_protocol_policy = "redirect-to-https"
    allowed_methods        = ["GET", "HEAD"]
    cached_methods         = ["GET", "HEAD"]
    compress               = true
    cache_policy_id        = local.caching_optimized_policy_id
  }

  ordered_cache_behavior {
    path_pattern           = "/thumbnail/*"
    target_origin_id       = "spark.wiki.thumbnails/normal-photos"
    viewer_protocol_policy = "redirect-to-https"
    allowed_methods        = ["GET", "HEAD"]
    cached_methods         = ["GET", "HEAD"]
    compress               = true
    cache_policy_id        = local.caching_optimized_policy_id
  }

  viewer_certificate {
    acm_certificate_arn      = aws_acm_certificate.wildcard.arn
    ssl_support_method       = "sni-only"
    minimum_protocol_version = "TLSv1.2_2021"
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  tags = {
    Name = "spark.wiki.normal-photos"
  }
}

resource "aws_cloudfront_distribution" "books" {
  aliases         = ["books.spark.wiki"]
  enabled         = true
  is_ipv6_enabled = true
  http_version    = "http2"
  price_class     = "PriceClass_All"
  web_acl_id      = aws_wafv2_web_acl.cdn["books"].arn

  origin {
    origin_id                = "spark.wiki.books.s3.us-east-1.amazonaws.com-mryhl1fewkb"
    domain_name              = aws_s3_bucket.content["books"].bucket_regional_domain_name
    origin_access_control_id = aws_cloudfront_origin_access_control.books.id
  }

  default_cache_behavior {
    target_origin_id       = "spark.wiki.books.s3.us-east-1.amazonaws.com-mryhl1fewkb"
    viewer_protocol_policy = "redirect-to-https"
    allowed_methods        = ["GET", "HEAD"]
    cached_methods         = ["GET", "HEAD"]
    compress               = true
    cache_policy_id        = local.caching_optimized_policy_id
  }

  viewer_certificate {
    acm_certificate_arn      = aws_acm_certificate.wildcard.arn
    ssl_support_method       = "sni-only"
    minimum_protocol_version = "TLSv1.2_2021"
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  tags = {
    Name = "spark.wiki.books"
  }
}

resource "aws_cloudfront_origin_access_control" "photos" {
  name                              = "oac-spark.wiki.photos.s3.us-east-1.amazonaws.com-mqvwkzezz97"
  description                       = "Created by CloudFront"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

resource "aws_cloudfront_origin_access_control" "normal_photos" {
  name                              = "spark.wiki.normal-photos.s3.us-east-1.amazonaws.com"
  description                       = ""
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

resource "aws_cloudfront_origin_access_control" "thumbnails" {
  name                              = "spark.wiki.thumbnails.s3.us-east-1.amazonaws.com"
  description                       = ""
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

resource "aws_cloudfront_origin_access_control" "books" {
  name                              = "oac-spark.wiki.books.s3.us-east-1.amazonaws.com-mryhszq059b"
  description                       = "Created by CloudFront"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

# Each bucket a CDN serves, and the distributions allowed to read it.
locals {
  cdn_buckets = {
    books         = [aws_cloudfront_distribution.books.arn]
    photos        = [aws_cloudfront_distribution.photos.arn]
    normal_photos = [aws_cloudfront_distribution.normal_photos.arn]
    thumbnails    = [aws_cloudfront_distribution.photos.arn, aws_cloudfront_distribution.normal_photos.arn]
  }
}

resource "aws_s3_bucket_policy" "cdn" {
  for_each = local.cdn_buckets

  bucket = aws_s3_bucket.content[each.key].id
  # As the console wrote them.
  policy = jsonencode({
    Version = "2008-10-17"
    Id      = "PolicyForCloudFrontPrivateContent"
    Statement = [{
      Sid       = "AllowCloudFrontServicePrincipal"
      Effect    = "Allow"
      Principal = { Service = "cloudfront.amazonaws.com" }
      Action    = "s3:GetObject"
      Resource  = "${aws_s3_bucket.content[each.key].arn}/*"
      Condition = { ArnLike = { "AWS:SourceArn" = each.value } }
    }]
  })

  # A bucket's public access block has to be settled before its policy.
  depends_on = [aws_s3_bucket_public_access_block.content]
}

# The protections CloudFront's console adds to a distribution: AWS's managed
# rules against bad IP addresses, common exploits, and known-bad inputs.
locals {
  cdn_web_acls = {
    books  = "CreatedByCloudFront-8dfd0590"
    photos = "CreatedByCloudFront-9decd9c5"
  }

  cloudfront_waf_rule_groups = [
    "AWSManagedRulesAmazonIpReputationList",
    "AWSManagedRulesCommonRuleSet",
    "AWSManagedRulesKnownBadInputsRuleSet",
  ]
}

resource "aws_wafv2_web_acl" "cdn" {
  for_each = local.cdn_web_acls

  name  = each.value
  scope = "CLOUDFRONT"

  default_action {
    allow {}
  }

  dynamic "rule" {
    for_each = local.cloudfront_waf_rule_groups

    content {
      name     = "AWS-${rule.value}"
      priority = rule.key

      override_action {
        none {}
      }

      statement {
        managed_rule_group_statement {
          vendor_name = "AWS"
          name        = rule.value
        }
      }

      visibility_config {
        sampled_requests_enabled   = true
        cloudwatch_metrics_enabled = true
        metric_name                = "AWS-${rule.value}"
      }
    }
  }

  visibility_config {
    sampled_requests_enabled   = true
    cloudwatch_metrics_enabled = true
    metric_name                = each.value
  }
}
