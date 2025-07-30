# Security Setup Guide

## Overview
This directory contains sensitive configuration files that should NEVER be committed to git. This guide explains how to set up your development environment securely.

## Critical Security Files

### Secret Configuration Files
The following files contain actual secrets and credentials and are **NEVER** committed to git:
- `config/development_secrets.json`
- `config/production_secrets.json`
- `config/staging_secrets.json`
- `config/testing_secrets.json`
- `kubernetes/manifests/configmaps-secrets.yaml`

### Template Files
Template files show the structure without actual secrets:
- `config/development_secrets.json.template`
- `config/production_secrets.json.template`
- `kubernetes/manifests/configmaps-secrets.yaml.template`

## Setup Instructions

### 1. Copy Template Files
```bash
# Copy templates to create your local secret files
cp config/development_secrets.json.template config/development_secrets.json
cp config/production_secrets.json.template config/production_secrets.json
cp kubernetes/manifests/configmaps-secrets.yaml.template kubernetes/manifests/configmaps-secrets.yaml
```

### 2. Update Secret Values
Replace all placeholder values in the copied files with actual secrets:

#### Development Secrets
- Replace `YOUR_DEV_PASSWORD` with actual database password
- Update any other placeholder values

#### Production Secrets
- Replace `${PRODUCTION_DATABASE_URL}` with actual database URL
- Replace `${VAULT_TOKEN}` with actual Vault token
- Replace `${HSM_AUTH_TOKEN}` with actual HSM token
- Update all other environment variables

#### Kubernetes Secrets
- Replace `YOUR_BASE64_ENCODED_JWT_SECRET` with actual base64-encoded JWT secret
- Replace `YOUR_BASE64_ENCODED_ANALYTICS_API_KEY` with actual API key
- Replace all other placeholder values with actual secrets

### 3. Verify Git Ignore
Ensure these files are in your `.gitignore`:
```bash
git check-ignore config/development_secrets.json
git check-ignore config/production_secrets.json
git check-ignore kubernetes/manifests/configmaps-secrets.yaml
```

## Security Best Practices

### 1. Never Commit Secrets
- Always use template files for structure
- Keep actual secrets in local files only
- Use environment variables for sensitive data

### 2. Use Secure Storage
- Store production secrets in HashiCorp Vault
- Use AWS KMS for key management
- Implement secret rotation

### 3. Access Control
- Limit access to production secrets
- Use role-based access control
- Audit secret access regularly

### 4. Development vs Production
- Use different secret files for different environments
- Never use production secrets in development
- Use mock/placeholder values for testing

## Troubleshooting

### Git Still Tracking Secret Files
If git is still tracking secret files:
```bash
git rm --cached config/development_secrets.json
git rm --cached config/production_secrets.json
git rm --cached kubernetes/manifests/configmaps-secrets.yaml
```

### Missing Template Files
If template files are missing, recreate them from the examples in this repository.

### Environment Variables
For production deployments, use environment variables instead of files:
```bash
export DATABASE_URL="postgresql://user:pass@host:port/db"
export JWT_SECRET="your-jwt-secret"
export VAULT_TOKEN="your-vault-token"
```

## Emergency Procedures

### If Secrets Are Committed
1. **IMMEDIATELY** rotate all exposed secrets
2. Remove the commit from git history
3. Update all systems with new secrets
4. Audit for unauthorized access

### Secret Rotation
- Rotate secrets regularly (30-90 days)
- Use automated rotation where possible
- Test rotation procedures in staging first

## Contact
For security issues or questions, contact the security team immediately. 