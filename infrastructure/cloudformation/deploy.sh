#!/bin/bash

# AWS CloudFormation deployment script for PyPI OIDC infrastructure
# Usage: ./deploy.sh <github-org> <github-repo> <pypi-token>

set -e

# Configuration
STACK_NAME="mypylogger-pypi-oidc"
TEMPLATE_FILE="pypi-oidc-stack.yaml"
REGION="${AWS_DEFAULT_REGION:-us-east-1}"

# Validate arguments
if [ $# -ne 3 ]; then
    echo "Usage: $0 <github-org> <github-repo> <pypi-token>"
    echo "Example: $0 myorg mypylogger pypi-AgEIcHlwaS5vcmcC..."
    exit 1
fi

GITHUB_ORG="$1"
GITHUB_REPO="$2"
PYPI_TOKEN="$3"

echo "🚀 Deploying PyPI OIDC infrastructure..."
echo "Stack Name: $STACK_NAME"
echo "Region: $REGION"
echo "GitHub Org: $GITHUB_ORG"
echo "GitHub Repo: $GITHUB_REPO"
echo ""

# Check if AWS CLI is configured
if ! aws sts get-caller-identity > /dev/null 2>&1; then
    echo "❌ AWS CLI not configured. Please run 'aws configure' first."
    exit 1
fi

# Deploy CloudFormation stack
echo "📦 Deploying CloudFormation stack..."
aws cloudformation deploy \
    --template-file "$TEMPLATE_FILE" \
    --stack-name "$STACK_NAME" \
    --parameter-overrides \
        GitHubOrg="$GITHUB_ORG" \
        GitHubRepo="$GITHUB_REPO" \
        PyPIToken="$PYPI_TOKEN" \
    --capabilities CAPABILITY_NAMED_IAM \
    --region "$REGION" \
    --tags \
        Project=mypylogger \
        Purpose=PyPI-Publishing \
        Environment=production

if [ $? -eq 0 ]; then
    echo "✅ Stack deployed successfully!"
    
    # Get stack outputs
    echo ""
    echo "📋 Stack Outputs:"
    aws cloudformation describe-stacks \
        --stack-name "$STACK_NAME" \
        --region "$REGION" \
        --query 'Stacks[0].Outputs[*].[OutputKey,OutputValue]' \
        --output table
    
    # Get the role ARN for GitHub Actions configuration
    ROLE_ARN=$(aws cloudformation describe-stacks \
        --stack-name "$STACK_NAME" \
        --region "$REGION" \
        --query 'Stacks[0].Outputs[?OutputKey==`GitHubActionsRoleArn`].OutputValue' \
        --output text)
    
    SECRET_NAME=$(aws cloudformation describe-stacks \
        --stack-name "$STACK_NAME" \
        --region "$REGION" \
        --query 'Stacks[0].Outputs[?OutputKey==`PyPITokenSecretName`].OutputValue' \
        --output text)
    
    echo ""
    echo "🔧 GitHub Actions Configuration:"
    echo "Add these secrets to your GitHub repository:"
    echo "  AWS_ROLE_ARN: $ROLE_ARN"
    echo "  AWS_SECRET_NAME: $SECRET_NAME"
    echo "  AWS_REGION: $REGION"
    
else
    echo "❌ Stack deployment failed!"
    exit 1
fi