#!/bin/bash

# Terraform deployment script for PyPI OIDC infrastructure
# Usage: ./deploy.sh <github-org> <pypi-token>

set -e

# Configuration
TERRAFORM_DIR="$(dirname "$0")"
cd "$TERRAFORM_DIR"

# Validate arguments
if [ $# -ne 2 ]; then
    echo "Usage: $0 <github-org> <pypi-token>"
    echo "Example: $0 myorg pypi-AgEIcHlwaS5vcmcC..."
    exit 1
fi

GITHUB_ORG="$1"
PYPI_TOKEN="$2"

echo "🚀 Deploying PyPI OIDC infrastructure with Terraform..."
echo "GitHub Org: $GITHUB_ORG"
echo ""

# Check if Terraform is installed
if ! command -v terraform &> /dev/null; then
    echo "❌ Terraform not found. Please install Terraform first."
    exit 1
fi

# Check if AWS CLI is configured
if ! aws sts get-caller-identity > /dev/null 2>&1; then
    echo "❌ AWS CLI not configured. Please run 'aws configure' first."
    exit 1
fi

# Initialize Terraform
echo "🔧 Initializing Terraform..."
terraform init

# Validate Terraform configuration
echo "✅ Validating Terraform configuration..."
terraform validate

# Plan deployment
echo "📋 Planning Terraform deployment..."
terraform plan \
    -var="github_org=$GITHUB_ORG" \
    -var="pypi_token=$PYPI_TOKEN" \
    -out=tfplan

# Apply deployment
echo "📦 Applying Terraform deployment..."
terraform apply tfplan

if [ $? -eq 0 ]; then
    echo "✅ Infrastructure deployed successfully!"
    
    # Show outputs
    echo ""
    echo "📋 Terraform Outputs:"
    terraform output
    
    # Get values for GitHub Actions configuration
    ROLE_ARN=$(terraform output -raw github_actions_role_arn)
    SECRET_NAME=$(terraform output -raw pypi_token_secret_name)
    AWS_REGION=$(terraform output -raw aws_region)
    
    echo ""
    echo "🔧 GitHub Actions Configuration:"
    echo "Add these secrets to your GitHub repository:"
    echo "  AWS_ROLE_ARN: $ROLE_ARN"
    echo "  AWS_SECRET_NAME: $SECRET_NAME"
    echo "  AWS_REGION: $AWS_REGION"
    
    # Clean up plan file
    rm -f tfplan
    
else
    echo "❌ Infrastructure deployment failed!"
    exit 1
fi