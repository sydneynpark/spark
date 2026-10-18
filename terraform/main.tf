# Everything in AWS that's managed as code, in one configuration: files
# prefixed site_ are the site (frontend, API, CDNs, and DNS), content_ the
# content and the pipeline that processes it. Applied only by
# .github/workflows/deploy.yml; see README.md. What gives CI its access is
# kept out of it, in bootstrap/.

terraform {
  required_version = ">= 1.14"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.67"
    }
  }

  backend "s3" {
    bucket       = "spark-wiki-terraform-state"
    key          = "terraform.tfstate"
    region       = "us-east-1"
    use_lockfile = true
  }
}

provider "aws" {
  region = "us-east-1"

  default_tags {
    tags = {
      ManagedBy = "terraform"
    }
  }
}

data "aws_caller_identity" "current" {}

locals {
  account_id = data.aws_caller_identity.current.account_id

  # Made by hand (bootstrap/workload-boundary.json): every role this
  # configuration manages has to carry it, since the deploy role can't
  # create or change roles that don't.
  workload_boundary_arn = "arn:aws:iam::${local.account_id}:policy/SiteWorkloadBoundary"

  # SSM parameters are made by hand, and not managed here: Terraform would
  # store their values in its state, which the plan role can read.
  ssm_parameter_arn_prefix = "arn:aws:ssm:us-east-1:${local.account_id}:parameter"
}

# Lets roles decrypt SecureString parameters, through SSM only.
data "aws_iam_policy_document" "decrypt_parameters" {
  statement {
    sid       = "DecryptParameters"
    actions   = ["kms:Decrypt"]
    resources = ["*"]
    condition {
      test     = "StringEquals"
      variable = "kms:ViaService"
      values   = ["ssm.us-east-1.amazonaws.com"]
    }
  }
}
