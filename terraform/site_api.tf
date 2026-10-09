# The site's API: the backend's ContentAPI Lambda. (API Gateway, in front of
# it, isn't managed here yet.)

module "content_api" {
  source = "./modules/python_lambda"

  function_name = "ContentAPI"
  project_dir   = "${path.root}/../backend"
  memory_size   = 128
  timeout       = 45

  # Created in the console, along with its policies; not managed here yet.
  role_arn = "arn:aws:iam::${local.account_id}:role/service-role/ContentAPI-role-rab0br82"
}
