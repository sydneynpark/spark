output "function_name" {
  value = aws_lambda_function.this.function_name
}

output "arn" {
  value = aws_lambda_function.this.arn
}

output "source_hash" {
  description = "Changes when the function's code, locked dependencies, or Python version do."
  value       = local.source_hash

  # So whatever this triggers runs after the function's been updated.
  depends_on = [aws_lambda_function.this]
}
