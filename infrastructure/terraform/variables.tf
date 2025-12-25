# Variables for AWS OIDC Infrastructure

variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Name of the project"
  type        = string
  default     = "mypylogger"
}

variable "github_org" {
  description = "GitHub organization or username"
  type        = string
}

variable "github_repo" {
  description = "GitHub repository name"
  type        = string
  default     = "mypylogger"
}

variable "pypi_token" {
  description = "PyPI API token for publishing"
  type        = string
  sensitive   = true
}

variable "environment" {
  description = "Environment name (e.g., production, staging)"
  type        = string
  default     = "production"
}

variable "enable_token_rotation" {
  description = "Enable automatic PyPI token rotation"
  type        = bool
  default     = false
}