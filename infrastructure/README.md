# AWS OIDC Infrastructure for PyPI Publishing

This directory contains AWS infrastructure configuration for secure PyPI publishing using GitHub Actions OIDC authentication.

## Overview

The infrastructure sets up:
- AWS IAM OIDC Identity Provider for GitHub Actions
- IAM Role with minimal permissions for PyPI publishing
- AWS Secrets Manager secret for PyPI token storage
- Secure credential management without storing secrets in GitHub

## Deployment Options

### CloudFormation
Use `cloudformation/pypi-oidc-stack.yaml` for AWS CloudFormation deployment.

### Terraform
Use `terraform/` directory for Terraform-based deployment.

## Security Features

- No long-lived credentials stored in GitHub
- Temporary tokens with minimal required permissions
- Role-based access with specific PyPI publishing scope
- Automatic token expiration and rotation support

## Requirements

- AWS CLI configured with appropriate permissions
- GitHub repository configured for OIDC
- PyPI API token stored in AWS Secrets Manager

## Deployment Instructions

See individual deployment directories for specific instructions.