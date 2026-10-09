# Adoption of resources originally created in the console. Each is a no-op
# once applied, and can then be deleted.

import {
  to = module.content_api.aws_lambda_function.this
  id = "ContentAPI"
}

import {
  to = module.update_photo_metadata.aws_lambda_function.this
  id = "UpdatePhotoMetadata"
}

import {
  to = module.update_blog_post_metadata.aws_lambda_function.this
  id = "UpdateBlogPostMetadata"
}

import {
  to = module.update_book_review.aws_lambda_function.this
  id = "UpdateBookReview"
}
