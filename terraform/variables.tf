variable "aws_region" {
  description = "AWS region for deployment"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "function_name" {
  description = "Lambda function name"
  type        = string
  default     = "incident-commander"
}

variable "lambda_timeout" {
  description = "Lambda timeout in seconds (max investigation time)"
  type        = number
  default     = 300  # 5 minutes for full investigation
}

variable "lambda_memory" {
  description = "Lambda memory in MB"
  type        = number
  default     = 1024  # 1GB for LLM operations
}

variable "openai_api_key" {
  description = "OpenAI API key for LLM agents"
  type        = string
  sensitive   = true
}

variable "demo_log_group" {
  description = "CloudWatch log group name for demo app"
  type        = string
  default     = "/aws/lambda/demo-checkout-service"
}

variable "demo_function_name" {
  description = "Demo app Lambda function name"
  type        = string
  default     = "demo-checkout-service"
}
