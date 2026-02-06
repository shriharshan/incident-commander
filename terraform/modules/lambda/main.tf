resource "aws_lambda_function" "incident_commander" {
  function_name = var.function_name
  role          = aws_iam_role.lambda_exec.arn
  
  filename         = "${path.module}/../../../lambda-package.zip"
  source_code_hash = filebase64sha256("${path.module}/../../../lambda-package.zip")
  
  runtime       = "python3.12"
  handler       = "lambda_handler.handler"
  timeout       = var.timeout
  memory_size   = var.memory_size
  
  environment {
    variables = {
      OPENAI_API_KEY       = var.openai_api_key
      OPENAI_MODEL         = "gpt-4"
      LOG_GROUP_NAME       = var.demo_log_group
      DEMO_FUNCTION_NAME   = var.demo_function_name
      REPORTS_BUCKET       = var.reports_bucket_name
    }
  }
  
  logging_config {
    log_format = "JSON"
    log_group  = aws_cloudwatch_log_group.lambda_logs.name
  }
}

# IAM Role for Lambda
resource "aws_iam_role" "lambda_exec" {
  name = "${var.function_name}-exec-role"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

# Basic Lambda execution policy
resource "aws_iam_role_policy_attachment" "lambda_basic" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# CloudWatch Logs read policy
resource "aws_iam_policy" "cloudwatch_read" {
  name = "${var.function_name}-cloudwatch-read"
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:StartQuery",
          "logs:GetQueryResults",
          "logs:GetLogEvents",
          "logs:FilterLogEvents",
          "logs:DescribeLogStreams"
        ]
        Resource = [
          "arn:aws:logs:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:log-group:${var.demo_log_group}:*"
        ]
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "cloudwatch_read" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = aws_iam_policy.cloudwatch_read.arn
}

# CloudWatch Metrics read policy
resource "aws_iam_policy" "cloudwatch_metrics" {
  name = "${var.function_name}-cloudwatch-metrics"
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "cloudwatch:GetMetricStatistics",
          "cloudwatch:GetMetricData",
          "cloudwatch:ListMetrics"
        ]
        Resource = "*"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "cloudwatch_metrics" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = aws_iam_policy.cloudwatch_metrics.arn
}

# CloudTrail read policy
resource "aws_iam_policy" "cloudtrail_read" {
  name = "${var.function_name}-cloudtrail-read"
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "cloudtrail:LookupEvents"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "lambda:GetFunction",
          "lambda:GetFunctionConfiguration"
        ]
        Resource = "arn:aws:lambda:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:function:${var.demo_function_name}"
      }
    ]
  })
}


# S3 Write Policy for Reports
resource "aws_iam_policy" "s3_write" {
  name = "${var.function_name}-s3-write"
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:PutObject",
          "s3:PutObjectAcl",
          "s3:ListBucket"
        ]
        Resource = [
          "arn:aws:s3:::incident-commander-reports-*",
          "arn:aws:s3:::incident-commander-reports-*/*"
        ]
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "s3_write" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = aws_iam_policy.s3_write.arn
}


# CloudWatch Logs for Commander
resource "aws_cloudwatch_log_group" "lambda_logs" {
  name              = "/aws/lambda/${var.function_name}"
  retention_in_days = 7  # Keep investigation logs for 7 days
}

# Lambda Function URL (for HTTP invocation)
resource "aws_lambda_function_url" "commander_url" {
  function_name      = aws_lambda_function.incident_commander.function_name
  authorization_type = "NONE"  # Public endpoint (use API Gateway + auth in production)
  
  cors {
    allow_origins = ["*"]
    allow_methods = ["POST"]
    max_age       = 86400
  }
}

data "aws_region" "current" {}
data "aws_caller_identity" "current" {}

output "function_name" {
  value = aws_lambda_function.incident_commander.function_name
}

output "function_arn" {
  value = aws_lambda_function.incident_commander.arn
}

output "function_url" {
  value = aws_lambda_function_url.commander_url.function_url
}

output "log_group_name" {
  value = aws_cloudwatch_log_group.lambda_logs.name
}
