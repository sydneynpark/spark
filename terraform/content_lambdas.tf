# The content-management Lambdas, which S3 invokes when content is uploaded
# to (or deleted from) its bucket, populating the DynamoDB tables the site's
# API serves.

module "update_photo_metadata" {
  source = "./modules/python_lambda"

  function_name = "UpdatePhotoMetadata"
  description   = "An Amazon S3 trigger that retrieves metadata for the object that has been updated."
  project_dir   = "${path.root}/../ContentManagement/UpdatePhotoMetadata"
  memory_size   = 256
  timeout       = 30

  # Pillow, from https://github.com/keithrozario/Klayers (Pillow 11.0.0 for
  # Python 3.12). It has to match the project's .python-version.
  layers = ["arn:aws:lambda:us-east-1:770693421928:layer:Klayers-p312-pillow:2"]

  permissions_boundary = local.workload_boundary_arn
  policy               = data.aws_iam_policy_document.update_photo_metadata.json
}

data "aws_iam_policy_document" "update_photo_metadata" {
  statement {
    sid       = "ReadPhotos"
    actions   = ["s3:GetObject"]
    resources = ["${aws_s3_bucket.content["photos"].arn}/*"]
  }

  statement {
    sid       = "WriteThumbnails"
    actions   = ["s3:PutObject"]
    resources = ["${aws_s3_bucket.content["thumbnails"].arn}/*"]
  }

  # Bird photos' taxonomy, and the rest's dates.
  statement {
    sid     = "WritePhotoMetadata"
    actions = ["dynamodb:PutItem"]
    resources = [
      aws_dynamodb_table.photos.arn,
      aws_dynamodb_table.normal_photos.arn,
    ]
  }
}

module "update_blog_post_metadata" {
  source = "./modules/python_lambda"

  function_name = "UpdateBlogPostMetadata"
  project_dir   = "${path.root}/../ContentManagement/UpdateBlogPostMetadata"
  memory_size   = 128
  timeout       = 3

  role_description     = "Allows the UpdateBlogPostMetadata Lambda function to read blog posts, and index them."
  permissions_boundary = local.workload_boundary_arn
  policy               = data.aws_iam_policy_document.update_blog_post_metadata.json
}

data "aws_iam_policy_document" "update_blog_post_metadata" {
  statement {
    sid       = "ReadPosts"
    actions   = ["s3:GetObject"]
    resources = ["${aws_s3_bucket.content["blog"].arn}/*"]
  }

  statement {
    sid       = "IndexPosts"
    actions   = ["dynamodb:PutItem", "dynamodb:DeleteItem"]
    resources = [aws_dynamodb_table.posts.arn]
  }
}

module "update_book_review" {
  source = "./modules/python_lambda"

  function_name = "UpdateBookReview"
  project_dir   = "${path.root}/../ContentManagement/UpdateBookReview"
  memory_size   = 128
  # Google Books and Gemini lookups for each review.
  timeout = 300

  permissions_boundary = local.workload_boundary_arn
  policy               = data.aws_iam_policy_document.update_book_review.json
}

data "aws_iam_policy_document" "update_book_review" {
  source_policy_documents = [data.aws_iam_policy_document.decrypt_parameters.json]

  # Without ListBucket, getting a missing object is AccessDenied rather
  # than NoSuchKey.
  statement {
    sid       = "ListReviews"
    actions   = ["s3:ListBucket"]
    resources = [aws_s3_bucket.content["books"].arn]
  }

  statement {
    sid       = "ReadReviews"
    actions   = ["s3:GetObject"]
    resources = ["${aws_s3_bucket.content["books"].arn}/*"]
  }

  # Saved when a review is processed, deleted along with it.
  statement {
    sid       = "WriteCovers"
    actions   = ["s3:PutObject", "s3:DeleteObject"]
    resources = ["${aws_s3_bucket.content["books"].arn}/covers/*"]
  }

  statement {
    sid       = "WriteReviews"
    actions   = ["dynamodb:Query", "dynamodb:PutItem", "dynamodb:DeleteItem"]
    resources = [aws_dynamodb_table.books.arn]
  }

  statement {
    sid     = "ReadAPIKeys"
    actions = ["ssm:GetParameter"]
    resources = [
      "${local.ssm_parameter_arn_prefix}/GoogleBooksAPIKey",
      "${local.ssm_parameter_arn_prefix}/GeminiAPIKey",
    ]
  }
}

# Each content bucket's trigger: the function S3 invokes, on which events.
locals {
  content_triggers = {
    blog = {
      function_name = module.update_blog_post_metadata.function_name
      function_arn  = module.update_blog_post_metadata.arn
      events        = ["s3:ObjectCreated:*", "s3:ObjectRemoved:*"]
      # As the console named them (changing one replaces it).
      statement_id = "lambda-334591f7-d838-4edf-9930-8f9d3263c32f"
    }
    books = {
      function_name = module.update_book_review.function_name
      function_arn  = module.update_book_review.arn
      events        = ["s3:ObjectCreated:*", "s3:ObjectRemoved:*"]
      statement_id  = "${local.account_id}_event_permissions_from_spark_wiki_books_for_UpdateBookReview"
    }
    photos = {
      function_name = module.update_photo_metadata.function_name
      function_arn  = module.update_photo_metadata.arn
      events        = ["s3:ObjectCreated:*", "s3:ObjectRemoved:*"]
      statement_id  = "lambda-707d2ae9-c6b7-42e9-8d3c-ca0c0b39d438"
    }
  }
}

resource "aws_lambda_permission" "content_trigger" {
  for_each = local.content_triggers

  statement_id   = each.value.statement_id
  action         = "lambda:InvokeFunction"
  function_name  = each.value.function_name
  principal      = "s3.amazonaws.com"
  source_arn     = aws_s3_bucket.content[each.key].arn
  source_account = local.account_id
}

resource "aws_s3_bucket_notification" "content" {
  for_each = local.content_triggers

  bucket = aws_s3_bucket.content[each.key].id

  lambda_function {
    lambda_function_arn = each.value.function_arn
    events              = each.value.events
  }

  # S3 checks it can invoke the function when the trigger is saved.
  depends_on = [aws_lambda_permission.content_trigger]
}
