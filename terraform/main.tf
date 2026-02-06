terraform {
  required_version = ">= 1.6"
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

module "lambda" {
  source = "./modules/lambda"
  
  function_name     = var.function_name
  timeout           = var.lambda_timeout
  memory_size       = var.lambda_memory
  openai_api_key    = var.openai_api_key
  demo_log_group    = var.demo_log_group
  demo_function_name = var.demo_function_name
  reports_bucket_name = aws_s3_bucket.reports_bucket.id
}

data "aws_caller_identity" "current" {}

module "subscription" {
  source = "./modules/subscription"

  commander_function_name = module.lambda.function_name
  commander_lambda_arn    = module.lambda.function_arn
  demo_log_group_name     = var.demo_log_group
  demo_log_group_arn      = "arn:aws:logs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:log-group:${var.demo_log_group}"
}

output "function_name" {
  value = module.lambda.function_name
}

output "function_arn" {
  value = module.lambda.function_arn
}

output "function_url" {
  value = module.lambda.function_url
}

output "log_group_name" {
  value = module.lambda.log_group_name
}

# S3 Bucket for RCA Reports
resource "aws_s3_bucket" "reports_bucket" {
  bucket_prefix = "incident-commander-reports-"
  force_destroy = true

  tags = {
    Name        = "Incident Commander Reports"
    Environment = "Demo"
  }
}

resource "aws_s3_bucket_public_access_block" "reports_bucket_public_access" {
  bucket = aws_s3_bucket.reports_bucket.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

output "reports_bucket_name" {
  value = aws_s3_bucket.reports_bucket.id
}
