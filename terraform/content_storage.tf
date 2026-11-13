# The site's content: photos (bird photos under birds/, the rest under
# photos/), book reviews, and blog posts, uploaded to S3 (by hand, or through
# the admin page), and what the content Lambdas derive from them
# (content_lambdas.tf): thumbnails, book covers, and the DynamoDB tables the
# API serves. Nothing here is versioned or backed up.

locals {
  content_buckets = {
    blog       = "spark.wiki.blog"
    books      = "spark.wiki.books"
    photos     = "spark.wiki.photos"
    thumbnails = "spark.wiki.thumbnails"
  }
}

resource "aws_s3_bucket" "content" {
  for_each = local.content_buckets

  bucket = each.value

  lifecycle {
    prevent_destroy = true
  }
}

# Private: CloudFront (site_cdn.tf) serves photos, thumbnails, and books, and
# the API serves blog posts.
resource "aws_s3_bucket_public_access_block" "content" {
  for_each = aws_s3_bucket.content

  bucket                  = each.value.id
  block_public_acls       = true
  ignore_public_acls      = true
  block_public_policy     = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_ownership_controls" "content" {
  for_each = aws_s3_bucket.content

  bucket = each.value.id
  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}

# The admin page uploads photos straight to the bucket, with presigned URLs
# from the API.
resource "aws_s3_bucket_cors_configuration" "photos" {
  bucket = aws_s3_bucket.content["photos"].id

  cors_rule {
    allowed_headers = ["Content-Type"]
    allowed_methods = ["PUT"]
    allowed_origins = ["https://spark.wiki", "https://www.spark.wiki"]
    max_age_seconds = 3000
  }
}

# Undoing a deploy that gave photos that aren't of birds a bucket of their
# own, spark.wiki.normal-photos, which nothing was ever uploaded to. Just
# dropping it from content_buckets would fail to apply, as the resource's
# prevent_destroy still covers it; moved to an address that isn't declared,
# it's destroyed. (These can go once that's been applied.)
moved {
  from = aws_s3_bucket.content["normal_photos"]
  to   = aws_s3_bucket.retired_normal_photos
}

moved {
  from = aws_s3_bucket_cors_configuration.photo_uploads["photos"]
  to   = aws_s3_bucket_cors_configuration.photos
}

resource "aws_dynamodb_table" "books" {
  name         = "spark.wiki.books"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "title"
  range_key    = "date"

  attribute {
    name = "title"
    type = "S"
  }

  attribute {
    name = "date"
    type = "N"
  }

  lifecycle {
    prevent_destroy = true
  }
}

resource "aws_dynamodb_table" "photos" {
  name         = "spark.wiki.photos"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "s3_uri"
  range_key    = "species"

  attribute {
    name = "s3_uri"
    type = "S"
  }

  attribute {
    name = "species"
    type = "S"
  }

  attribute {
    name = "family"
    type = "S"
  }

  attribute {
    name = "order"
    type = "S"
  }

  # The API's browse-by-taxonomy queries.
  dynamic "global_secondary_index" {
    for_each = ["species", "family", "order"]

    content {
      name            = "taxonomy-${global_secondary_index.value}"
      projection_type = "ALL"

      # In the order AWS lists them, HASH first.
      key_schema {
        attribute_name = global_secondary_index.value
        key_type       = "HASH"
      }

      key_schema {
        attribute_name = "s3_uri"
        key_type       = "RANGE"
      }
    }
  }

  lifecycle {
    prevent_destroy = true
  }
}

# Photos that aren't of birds, so have no taxonomy: one item per photo, which
# the API lists by date. Named before /photos was for them, and the bird
# photos /birds.
resource "aws_dynamodb_table" "normal_photos" {
  name         = "spark.wiki.normal-photos"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "s3_uri"

  attribute {
    name = "s3_uri"
    type = "S"
  }

  lifecycle {
    prevent_destroy = true
  }
}
