# Adoption of resources originally created in the console. Each is a no-op
# once applied, and can then be deleted.

locals {
  zone_id = "Z06879821CJYLNK8MINIR"
  api_id  = "f9e1sa8azj"

  lambda_roles = {
    content_api               = "ContentAPI-role-rab0br82"
    update_photo_metadata     = "Lambda_UpdatePhotoMetadata"
    update_blog_post_metadata = "Lambda_UpdateBlogPostMetadata"
    update_book_review        = "UpdateBookReview-role-qcl2ltqh"
  }
}

# --- Lambda execution roles and log groups (one module each) --------------

# The roles are imported only to be replaced, by ones under /site-workload/
# (see modules/python_lambda), so that Terraform deletes them.

import {
  to = module.content_api.aws_iam_role.this
  id = local.lambda_roles.content_api
}

import {
  to = module.update_photo_metadata.aws_iam_role.this
  id = local.lambda_roles.update_photo_metadata
}

import {
  to = module.update_blog_post_metadata.aws_iam_role.this
  id = local.lambda_roles.update_blog_post_metadata
}

import {
  to = module.update_book_review.aws_iam_role.this
  id = local.lambda_roles.update_book_review
}

import {
  to = module.content_api.aws_cloudwatch_log_group.this
  id = "/aws/lambda/ContentAPI"
}

import {
  to = module.update_photo_metadata.aws_cloudwatch_log_group.this
  id = "/aws/lambda/UpdatePhotoMetadata"
}

import {
  to = module.update_blog_post_metadata.aws_cloudwatch_log_group.this
  id = "/aws/lambda/UpdateBlogPostMetadata"
}

import {
  to = module.update_book_review.aws_cloudwatch_log_group.this
  id = "/aws/lambda/UpdateBookReview"
}

# --- Content: buckets, tables, triggers ------------------------------------

import {
  for_each = local.content_buckets
  to       = aws_s3_bucket.content[each.key]
  id       = each.value
}

import {
  for_each = local.content_buckets
  to       = aws_s3_bucket_public_access_block.content[each.key]
  id       = each.value
}

import {
  for_each = local.content_buckets
  to       = aws_s3_bucket_ownership_controls.content[each.key]
  id       = each.value
}

import {
  to = aws_s3_bucket_cors_configuration.photos
  id = "spark.wiki.photos"
}

import {
  for_each = toset(["books", "photos", "thumbnails"])
  to       = aws_s3_bucket_policy.cdn[each.key]
  id       = local.content_buckets[each.key]
}

import {
  to = aws_dynamodb_table.books
  id = "spark.wiki.books"
}

import {
  to = aws_dynamodb_table.photos
  id = "spark.wiki.photos"
}

import {
  for_each = local.content_triggers
  to       = aws_lambda_permission.content_trigger[each.key]
  id       = "${each.value.function_name}/${each.value.statement_id}"
}

import {
  for_each = local.content_triggers
  to       = aws_s3_bucket_notification.content[each.key]
  id       = local.content_buckets[each.key]
}

# --- API ---------------------------------------------------------------------

import {
  to = aws_api_gateway_rest_api.api
  id = local.api_id
}

import {
  to = aws_api_gateway_resource.proxy
  id = "${local.api_id}/vcaujl"
}

import {
  to = aws_api_gateway_method.proxy
  id = "${local.api_id}/vcaujl/ANY"
}

import {
  to = aws_api_gateway_integration.proxy
  id = "${local.api_id}/vcaujl/ANY"
}

import {
  to = aws_lambda_permission.api
  id = "ContentAPI/d7be9d2e-a636-51e7-bb87-00c1c55fc32b"
}

import {
  for_each = toset(["DEFAULT_4XX", "DEFAULT_5XX"])
  to       = aws_api_gateway_gateway_response.errors[each.key]
  id       = "${local.api_id}/${each.key}"
}

# (The stage's current deployment isn't imported: Terraform makes its own.)
import {
  to = aws_api_gateway_stage.live
  id = "${local.api_id}/LIVE"
}

import {
  to = aws_api_gateway_method_settings.live
  id = "${local.api_id}/LIVE/*/*"
}

import {
  to = aws_cloudwatch_log_group.api_execution
  id = "API-Gateway-Execution-Logs_${local.api_id}/LIVE"
}

import {
  to = aws_api_gateway_domain_name.api
  id = "api.spark.wiki"
}

# The trailing / is the empty base path.
import {
  to = aws_api_gateway_base_path_mapping.api
  id = "api.spark.wiki/"
}

import {
  to = aws_api_gateway_account.this
  id = "api-gateway-account"
}

# Also replaced, like the Lambdas' roles.
import {
  to = aws_iam_role.api_gateway_logs
  id = "APIGateway_api.spark.wiki"
}

# --- Frontend ------------------------------------------------------------------

import {
  to = aws_s3_bucket.frontend
  id = "spark.wiki.frontend"
}

import {
  to = aws_s3_bucket_public_access_block.frontend
  id = "spark.wiki.frontend"
}

import {
  to = aws_s3_bucket_ownership_controls.frontend
  id = "spark.wiki.frontend"
}

import {
  to = aws_s3_bucket_policy.frontend
  id = "spark.wiki.frontend"
}

import {
  to = aws_s3_bucket_website_configuration.frontend
  id = "spark.wiki.frontend"
}

import {
  to = aws_cloudfront_distribution.frontend
  id = "E2JO5BSJ5WRP9P"
}

# --- CDNs ----------------------------------------------------------------------

import {
  to = aws_cloudfront_distribution.photos
  id = "E36I1WVQPNH4HH"
}

import {
  to = aws_cloudfront_distribution.books
  id = "E2Y8FRIT378S9Y"
}

import {
  to = aws_cloudfront_origin_access_control.photos
  id = "E19M97ILNFAK9W"
}

import {
  to = aws_cloudfront_origin_access_control.thumbnails
  id = "E2TQ4ICD2J986O"
}

import {
  to = aws_cloudfront_origin_access_control.books
  id = "E7MZSHXZJOE22"
}

import {
  to = aws_wafv2_web_acl.cdn["books"]
  id = "a63601b9-8685-486d-a01c-80e14b7ff1ce/CreatedByCloudFront-8dfd0590/CLOUDFRONT"
}

import {
  to = aws_wafv2_web_acl.cdn["photos"]
  id = "373cc68c-fb1c-4fc2-a436-86d207b77e57/CreatedByCloudFront-9decd9c5/CLOUDFRONT"
}

# --- DNS and certificates --------------------------------------------------------

import {
  to = aws_route53_zone.spark_wiki
  id = local.zone_id
}

import {
  to = aws_acm_certificate.apex
  id = "arn:aws:acm:us-east-1:${local.account_id}:certificate/373a1646-804c-45ce-9aef-ff9fe055e0f4"
}

import {
  to = aws_acm_certificate.wildcard
  id = "arn:aws:acm:us-east-1:${local.account_id}:certificate/b0cd0675-e400-4819-8fa5-312c62ee7edd"
}

import {
  to = aws_route53_record.certificate_validation
  id = "${local.zone_id}__9a94c849725c7ea154b4bf55f8fa499e.spark.wiki_CNAME"
}

import {
  for_each = local.cloudfront_hostnames
  to       = aws_route53_record.cloudfront[each.key]
  id       = "${local.zone_id}_${each.key}_A"
}

import {
  to = aws_route53_record.api
  id = "${local.zone_id}_api.spark.wiki_A"
}

import {
  to = aws_route53_record.mx
  id = "${local.zone_id}_spark.wiki_MX"
}

import {
  to = aws_route53_record.txt
  id = "${local.zone_id}_spark.wiki_TXT"
}

import {
  to = aws_route53_record.google_verification
  id = "${local.zone_id}_pokyb2llby26.spark.wiki_CNAME"
}
