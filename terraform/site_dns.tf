# spark.wiki's DNS (the domain is registered elsewhere, delegated to this
# zone's name servers), and the site's TLS certificates.

resource "aws_route53_zone" "spark_wiki" {
  name    = "spark.wiki"
  comment = ""

  lifecycle {
    prevent_destroy = true
  }
}

# spark.wiki, for the frontend's distribution.
resource "aws_acm_certificate" "apex" {
  domain_name       = "spark.wiki"
  validation_method = "DNS"
  key_algorithm     = "RSA_2048"

  options {
    certificate_transparency_logging_preference = "ENABLED"
  }

  lifecycle {
    create_before_destroy = true
  }
}

# *.spark.wiki, for the API and the CDNs.
resource "aws_acm_certificate" "wildcard" {
  domain_name       = "*.spark.wiki"
  validation_method = "DNS"
  key_algorithm     = "RSA_2048"

  options {
    certificate_transparency_logging_preference = "ENABLED"
  }

  lifecycle {
    create_before_destroy = true
  }
}

# Both certificates validate (and renew) with the same record.
resource "aws_route53_record" "certificate_validation" {
  zone_id = aws_route53_zone.spark_wiki.zone_id
  name    = one(aws_acm_certificate.apex.domain_validation_options).resource_record_name
  type    = one(aws_acm_certificate.apex.domain_validation_options).resource_record_type
  records = [one(aws_acm_certificate.apex.domain_validation_options).resource_record_value]
  ttl     = 300

  lifecycle {
    precondition {
      condition     = one(aws_acm_certificate.wildcard.domain_validation_options).resource_record_name == one(aws_acm_certificate.apex.domain_validation_options).resource_record_name
      error_message = "The certificates no longer share a validation record: give *.spark.wiki's its own."
    }
  }
}

# Each site hostname, and the CloudFront distribution serving it.
locals {
  cloudfront_hostnames = {
    "spark.wiki"        = aws_cloudfront_distribution.frontend
    "books.spark.wiki"  = aws_cloudfront_distribution.books
    "photos.spark.wiki" = aws_cloudfront_distribution.photos
  }
}

resource "aws_route53_record" "cloudfront" {
  for_each = local.cloudfront_hostnames

  zone_id = aws_route53_zone.spark_wiki.zone_id
  name    = each.key
  type    = "A"

  alias {
    name                   = each.value.domain_name
    zone_id                = each.value.hosted_zone_id
    evaluate_target_health = false
  }
}

resource "aws_route53_record" "api" {
  zone_id = aws_route53_zone.spark_wiki.zone_id
  name    = "api.spark.wiki"
  type    = "A"

  alias {
    name                   = aws_api_gateway_domain_name.api.regional_domain_name
    zone_id                = aws_api_gateway_domain_name.api.regional_zone_id
    evaluate_target_health = true
  }
}

# Google Workspace: mail, and verifying the domain.
resource "aws_route53_record" "mx" {
  zone_id = aws_route53_zone.spark_wiki.zone_id
  name    = "spark.wiki"
  type    = "MX"
  ttl     = 300
  records = ["1 aspmx.l.google.com"]
}

resource "aws_route53_record" "txt" {
  zone_id = aws_route53_zone.spark_wiki.zone_id
  name    = "spark.wiki"
  type    = "TXT"
  ttl     = 300
  records = ["google-site-verification=sF3_SkbV47lC4FH8ff8ffd2VBol9uYX46PdHzICHXA4"]
}

resource "aws_route53_record" "google_verification" {
  zone_id = aws_route53_zone.spark_wiki.zone_id
  name    = "pokyb2llby26.spark.wiki"
  type    = "CNAME"
  ttl     = 300
  records = ["gv-7kqglyw7j26p4i.dv.googlehosted.com"]
}
