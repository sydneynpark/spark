# After UpdatePhotoMetadata's or UpdateBookReview's code changes, reprocess
# every existing photo or review with the new code, as if each were uploaded
# again. Each runs once the function's update has finished, on the machine
# applying this (the deploy workflow) with its AWS credentials. If one fails,
# Terraform marks it to run again on the next apply.

resource "terraform_data" "reprocess_photos" {
  triggers_replace = module.update_photo_metadata.source_hash

  provisioner "local-exec" {
    command = "uv run --no-project --with-requirements ${path.root}/../scripts/requirements.txt ${path.root}/../scripts/refreshPhotoMetadata.py"
  }
}

resource "terraform_data" "reprocess_book_reviews" {
  triggers_replace = module.update_book_review.source_hash

  provisioner "local-exec" {
    command = "uv run --no-project --with-requirements ${path.root}/../scripts/requirements.txt ${path.root}/../scripts/refreshBookReviewData.py"
  }
}
