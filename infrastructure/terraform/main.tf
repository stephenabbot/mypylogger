# AWS OIDC Infrastructure for mypylogger PyPI Publishing
# Terraform configuration for GitHub Actions OIDC authentication

terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
  
  default_tags {
    tags = {
      Project     = "mypylogger"
      Purpose     = "PyPI-Publishing"
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  }
}

# Data source for GitHub OIDC thumbprints
data "tls_certificate" "github_actions" {
  url = "https://token.actions.githubusercontent.com"
}

# OIDC Identity Provider for GitHub Actions
resource "aws_iam_openid_connect_provider" "github_actions" {
  url = "https://token.actions.githubusercontent.com"
  
  client_id_list = [
    "sts.amazonaws.com"
  ]
  
  thumbprint_list = [
    data.tls_certificate.github_actions.certificates[0].sha1_fingerprint,
    "6938fd4d98bab03faadb97b34396831e3780aea1", # GitHub Actions OIDC
    "1c58a3a8518e8759bf075b76b750d4f2df264fcd"  # Backup thumbprint
  ]

  tags = {
    Name = "${var.project_name}-github-oidc-provider"
  }
}

# IAM Role for GitHub Actions PyPI Publishing
resource "aws_iam_role" "github_actions_role" {
  name = "${var.project_name}-github-actions-pypi-role"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Federated = aws_iam_openid_connect_provider.github_actions.arn
        }
        Action = "sts:AssumeRoleWithWebIdentity"
        Condition = {
          StringEquals = {
            "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com"
          }
          StringLike = {
            "token.actions.githubusercontent.com:sub" = "repo:${var.github_org}/${var.github_repo}:*"
          }
        }
      }
    ]
  })

  tags = {
    Name = "${var.project_name}-github-actions-role"
  }
}

# IAM Policy for accessing PyPI token from Secrets Manager
resource "aws_iam_policy" "pypi_secrets_policy" {
  name        = "${var.project_name}-pypi-secrets-policy"
  description = "Policy for accessing PyPI token from AWS Secrets Manager"
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue",
          "secretsmanager:DescribeSecret"
        ]
        Resource = aws_secretsmanager_secret.pypi_token.arn
      }
    ]
  })

  tags = {
    Name = "${var.project_name}-pypi-secrets-policy"
  }
}

# Attach policy to role
resource "aws_iam_role_policy_attachment" "github_actions_policy" {
  role       = aws_iam_role.github_actions_role.name
  policy_arn = aws_iam_policy.pypi_secrets_policy.arn
}

# AWS Secrets Manager secret for PyPI token
resource "aws_secretsmanager_secret" "pypi_token" {
  name        = "${var.project_name}/pypi-token"
  description = "PyPI API token for ${var.project_name} package publishing"
  
  # Enable automatic rotation every 90 days
  rotation_rules {
    automatically_after_days = 90
  }

  tags = {
    Name = "${var.project_name}-pypi-token"
  }
}

# PyPI token secret version
resource "aws_secretsmanager_secret_version" "pypi_token" {
  secret_id = aws_secretsmanager_secret.pypi_token.id
  secret_string = jsonencode({
    token      = var.pypi_token
    repository = "https://upload.pypi.org/legacy/"
    package    = var.project_name
  })
}

# Lambda function for token rotation (optional)
resource "aws_lambda_function" "pypi_token_rotation" {
  count = var.enable_token_rotation ? 1 : 0
  
  filename         = "pypi_token_rotation.zip"
  function_name    = "${var.project_name}-pypi-token-rotation"
  role            = aws_iam_role.pypi_token_rotation_role[0].arn
  handler         = "index.lambda_handler"
  runtime         = "python3.9"
  timeout         = 60

  source_code_hash = data.archive_file.pypi_token_rotation_zip[0].output_base64sha256

  tags = {
    Name = "${var.project_name}-pypi-token-rotation"
  }
}

# Create Lambda deployment package
data "archive_file" "pypi_token_rotation_zip" {
  count = var.enable_token_rotation ? 1 : 0
  
  type        = "zip"
  output_path = "pypi_token_rotation.zip"
  
  source {
    content = templatefile("${path.module}/lambda/pypi_token_rotation.py", {
      secret_arn = aws_secretsmanager_secret.pypi_token.arn
    })
    filename = "index.py"
  }
}

# IAM Role for Lambda rotation function
resource "aws_iam_role" "pypi_token_rotation_role" {
  count = var.enable_token_rotation ? 1 : 0
  
  name = "${var.project_name}-pypi-rotation-role"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })

  tags = {
    Name = "${var.project_name}-pypi-rotation-role"
  }
}

# IAM Policy for Lambda rotation function
resource "aws_iam_policy" "pypi_token_rotation_policy" {
  count = var.enable_token_rotation ? 1 : 0
  
  name        = "${var.project_name}-pypi-rotation-policy"
  description = "Policy for PyPI token rotation Lambda function"
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:*:*:*"
      },
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:UpdateSecret",
          "secretsmanager:GetSecretValue",
          "secretsmanager:PutSecretValue",
          "secretsmanager:DescribeSecret"
        ]
        Resource = aws_secretsmanager_secret.pypi_token.arn
      }
    ]
  })

  tags = {
    Name = "${var.project_name}-pypi-rotation-policy"
  }
}

# Attach policy to Lambda role
resource "aws_iam_role_policy_attachment" "pypi_token_rotation_policy" {
  count = var.enable_token_rotation ? 1 : 0
  
  role       = aws_iam_role.pypi_token_rotation_role[0].name
  policy_arn = aws_iam_policy.pypi_token_rotation_policy[0].arn
}

# Lambda permission for Secrets Manager to invoke rotation
resource "aws_lambda_permission" "allow_secrets_manager" {
  count = var.enable_token_rotation ? 1 : 0
  
  statement_id  = "AllowSecretsManagerInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.pypi_token_rotation[0].function_name
  principal     = "secretsmanager.amazonaws.com"
}