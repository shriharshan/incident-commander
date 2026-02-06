resource "aws_cloudwatch_log_subscription_filter" "error_stream" {
  name            = "incident-commander-error-stream"
  log_group_name  = var.demo_log_group_name
  filter_pattern  = "{ $.level = \"ERROR\" }"  # Stream only ERROR logs
  destination_arn = var.commander_lambda_arn
  
  depends_on = [aws_lambda_permission.allow_cloudwatch_logs]
}

# Permission for CloudWatch Logs to invoke Commander Lambda
resource "aws_lambda_permission" "allow_cloudwatch_logs" {
  statement_id  = "AllowCloudWatchLogsInvoke"
  action        = "lambda:InvokeFunction"
  function_name = var.commander_function_name
  principal     = "logs.amazonaws.com"
  source_arn    = "${var.demo_log_group_arn}:*"
}

output "subscription_filter_name" {
  value       = aws_cloudwatch_log_subscription_filter.error_stream.name
  description = "Name of the CloudWatch Logs subscription filter"
}
