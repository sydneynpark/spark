# The site's frontend: frontend/build (built by .github/workflows/build.yml),
# uploaded to the bucket CloudFront serves the site from. Only changed files
# are uploaded, files no longer in the build are deleted, and CloudFront's
# cache is invalidated after any change. (The bucket and distribution
# themselves aren't managed here yet.)

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

  bucket       = "spark.wiki.frontend"
  key          = each.key
  source       = "${local.frontend_build}/${each.key}"
  etag         = filemd5("${local.frontend_build}/${each.key}")
  content_type = each.value

  lifecycle {
    precondition {
      condition     = each.value != null
      error_message = "No content type for ${each.key}: add its extension to content_types in terraform/site/frontend.tf."
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
    distribution_id = "E2JO5BSJ5WRP9P"
    paths           = ["/*"]
  }
}
