# AWS OIDC Infrastructure Deployment Guide

This guide explains how to deploy the AWS infrastructure required for secure PyPI publishing using GitHub Actions OIDC authentication.

## Overview

The infrastructure creates:
- AWS IAM OIDC Identity Provider for GitHub Actions
- IAM Role with minimal permissions for PyPI publishing
- AWS Secrets Manager secret for PyPI token storage
- Optional Lambda function for automatic token rotation

## Prerequisites

1. **AWS Account** with appropriate permissions
2. **AWS CLI** configured with credentials
3. **PyPI API Token** for your package
4. **GitHub Repository** configured for OIDC

### Required AWS Permissions

Your AWS user/role needs these permissions:
- `iam:*` (for creating roles and policies)
- `secretsmanager:*` (for managing secrets)
- `lambda:*` (for rotation function, if enabled)
- `cloudformation:*` (for CloudFormation deployment)

## Deployment Options

### Option 1: CloudFormation (Recommended)

CloudFormation provides a complete infrastructure-as-code solution with rollback capabilities.

#### Deploy with CloudFormation

```bash
cd infrastructure/cloudformation
./deploy.sh <github-org> <github-repo> <pypi-token>
```

Example:
```bash
./deploy.sh myorg mypylogger pypi-AgEIcHlwaS5vcmcCJRVOaXMxLjAyAAABhGlkAAABhGh0dHBzOi8vcHlwaS5vcmcvbGVnYWN5Lw
```

#### Manual CloudFormation Deployment

```bash
aws cloudformation deploy \
    --template-file pypi-oidc-stack.yaml \
    --stack-name mypylogger-pypi-oidc \
    --parameter-overrides \
        GitHubOrg=myorg \
        GitHubRepo=mypylogger \
        PyPIToken=pypi-AgEIcHlwaS5vcmcC... \
    --capabilities CAPABILITY_NAMED_IAM \
    --region us-east-1
```

### Option 2: Terraform

Terraform provides more flexibility and state management.

#### Deploy with Terraform

```bash
cd infrastructure/terraform
./deploy.sh <github-org> <pypi-token>
```

#### Manual Terraform Deployment

```bash
cd infrastructure/terraform

# Initialize Terraform
terraform init

# Create terraform.tfvars
cat > terraform.tfvars << EOF
github_org = "myorg"
github_repo = "mypylogger"
pypi_token = "pypi-AgEIcHlwaS5vcmcC..."
aws_region = "us-east-1"
EOF

# Plan and apply
terraform plan
terraform apply
```

## Post-Deployment Configuration

### 1. GitHub Repository Secrets

After deployment, add these secrets to your GitHub repository:

1. Go to your GitHub repository
2. Navigate to Settings → Secrets and variables → Actions
3. Add these repository secrets:

| Secret Name | Value | Description |
|-------------|-------|-------------|
| `AWS_ROLE_ARN` | `arn:aws:iam::123456789012:role/mypylogger-github-actions-pypi-role` | IAM role ARN from deployment output |
| `AWS_SECRET_NAME` | `mypylogger/pypi-token` | Secret name from deployment output |
| `AWS_REGION` | `us-east-1` | AWS region where resources are deployed |

### 2. GitHub OIDC Configuration

Ensure your GitHub repository is configured for OIDC:

1. Repository must be public or have GitHub Enterprise
2. Actions must be enabled
3. OIDC token permissions must be configured in workflow

## Security Considerations

### Minimal Permissions

The IAM role has minimal permissions:
- Only access to the specific PyPI token secret
- Only from the specified GitHub repository
- Only for the `sts.amazonaws.com` audience

### Token Security

- PyPI token is encrypted at rest in AWS Secrets Manager
- Token is only accessible during GitHub Actions execution
- No long-lived credentials stored in GitHub
- Optional automatic token rotation

### Network Security

- All communication uses HTTPS/TLS
- AWS API calls use IAM authentication
- GitHub OIDC tokens are short-lived (15 minutes)

## Troubleshooting

### Common Issues

#### 1. OIDC Trust Relationship Error

```
Error: Could not assume role with OIDC
```

**Solution**: Verify the GitHub repository path in the trust policy matches exactly:
- Check GitHub org/username spelling
- Verify repository name
- Ensure the repository is public or has Enterprise features

#### 2. Secrets Manager Access Denied

```
Error: User is not authorized to perform: secretsmanager:GetSecretValue
```

**Solution**: Verify the IAM role has the correct policy attached and the secret ARN matches.

#### 3. PyPI Token Invalid

```
Error: Invalid PyPI token
```

**Solution**: 
- Verify the PyPI token is correct and active
- Check the token has publishing permissions for your package
- Ensure the token hasn't expired

### Debugging Steps

1. **Check AWS CloudTrail** for detailed error logs
2. **Verify IAM role trust policy** matches your repository
3. **Test secret access** using AWS CLI:
   ```bash
   aws secretsmanager get-secret-value --secret-id mypylogger/pypi-token
   ```
4. **Validate OIDC provider** configuration in AWS Console

## Cleanup

### CloudFormation Cleanup

```bash
aws cloudformation delete-stack --stack-name mypylogger-pypi-oidc
```

### Terraform Cleanup

```bash
cd infrastructure/terraform
terraform destroy
```

## Cost Considerations

The infrastructure has minimal costs:
- **Secrets Manager**: ~$0.40/month per secret
- **Lambda** (if enabled): Free tier covers rotation usage
- **IAM**: No additional costs
- **CloudFormation**: No additional costs

Total estimated cost: **< $1/month**

## Next Steps

After deploying the infrastructure:

1. Configure GitHub Actions workflow (Task 2.2)
2. Implement credential management system (Task 2.3)
3. Add security tests (Task 2.4)
4. Test end-to-end publishing workflow

## Support

For issues with this infrastructure:
1. Check AWS CloudTrail logs
2. Verify GitHub repository configuration
3. Test PyPI token manually
4. Review IAM role trust relationships