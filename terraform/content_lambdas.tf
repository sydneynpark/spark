# The content-management Lambdas, which run out of band when content is
# uploaded to S3, populating the DynamoDB tables the site's API serves. Their
# execution roles, and the S3 triggers that invoke them, were created in the
# console and aren't managed here yet.

module "update_photo_metadata" {
  source = "./modules/python_lambda"

  function_name = "UpdatePhotoMetadata"
  description   = "An Amazon S3 trigger that retrieves metadata for the object that has been updated."
  project_dir   = "${path.root}/../ContentManagement/UpdatePhotoMetadata"
  memory_size   = 256
  timeout       = 30
  role_arn      = "arn:aws:iam::${local.account_id}:role/service-role/Lambda_UpdatePhotoMetadata"

  # Pillow, from https://github.com/keithrozario/Klayers (Pillow 11.0.0 for
  # Python 3.12). It has to match the project's .python-version.
  layers = ["arn:aws:lambda:us-east-1:770693421928:layer:Klayers-p312-pillow:2"]
}

module "update_blog_post_metadata" {
  source = "./modules/python_lambda"

  function_name = "UpdateBlogPostMetadata"
  project_dir   = "${path.root}/../ContentManagement/UpdateBlogPostMetadata"
  memory_size   = 128
  timeout       = 3
  role_arn      = "arn:aws:iam::${local.account_id}:role/Lambda_UpdateBlogPostMetadata"
}

module "update_book_review" {
  source = "./modules/python_lambda"

  function_name = "UpdateBookReview"
  project_dir   = "${path.root}/../ContentManagement/UpdateBookReview"
  memory_size   = 128
  # Google Books and Gemini lookups for each review.
  timeout  = 300
  role_arn = "arn:aws:iam::${local.account_id}:role/service-role/UpdateBookReview-role-qcl2ltqh"
}
