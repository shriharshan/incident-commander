variable "function_name" {
  description = "Lambda function name"
  type        = string
}

variable "timeout" {
  description = "Lambda timeout in seconds"
  type        = number
}

variable "memory_size" {
  description = "Lambda memory in MB"
  type        = number
}

variable "openai_api_key" {
  description = "OpenAI API key"
  type        = string
  sensitive   = true
}

variable "demo_log_group" {
  description = "Demo app log group name"
  type        = string
}

variable "demo_function_name" {
  description = "Name of the demo Lambda function"
  type        = string
}

variable "reports_bucket_name" {
  description = "Name of the S3 bucket for RCA reports"
  type        = string
}
