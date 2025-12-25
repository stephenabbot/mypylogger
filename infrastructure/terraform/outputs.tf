# Outputs for AWS OIDC Infrastructure

output "github_actions_role_arn" {
  description = "ARN of the IAM role for GitHub Actions"
  value       = aws_iam_role.github_actions_role.arn
}

output "pypi_token_secret_arn" {
  description = "ARN of the PyPI token secret"
  value       = aws_secretsmanager_secret.pypi_token.arn
}

output "pypi_token_secret_name" {
  description = "Name of the PyPI token secret"
  value       = aws_secretsmanager_secret.pypi_token.name
}

output "oidc_provider_arn" {
  description = "ARN of the GitHub OIDC provider"
  value       = aws_iam_openid_connect_provider.github_actions.arn
}

output "aws_region" {
  description = "AWS region where resources are deployed"
  value       = var.aws_region
}

# GitHub Actions configuration values
output "github_actions_config" {
  description = "Configuration values for GitHub Actions"
  value = {
    AWS_ROLE_ARN    = aws_iam_role.github_actions_role.arn
    AWS_SECRET_NAME = aws_secretsmanager_secret.pypi_token.name
    AWS_REGION      = var.aws_region
  }
}