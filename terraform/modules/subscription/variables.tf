variable "commander_function_name" {
  description = "Name of the Incident Commander Lambda function"
  type        = string
}

variable "commander_lambda_arn" {
  description = "ARN of the Incident Commander Lambda function"
  type        = string
}

variable "demo_log_group_name" {
  description = "Name of the demo checkout service CloudWatch Log Group"
  type        = string
}

variable "demo_log_group_arn" {
  description = "ARN of the demo checkout service CloudWatch Log Group"
  type        = string
}
