# Security Module Deployment Guide

## Overview

This guide provides step-by-step instructions for deploying the security module to new projects. The security module is designed as a self-contained, reusable pattern that provides automated vulnerability tracking, structured remediation planning, and real-time security documentation.

## Copy-Paste Deployment Process

### Step 1: Copy Security Module

Copy the entire `security/` directory to your target project:

```bash
# From source project
cp -r security/ /path/to/target/project/

# Or using rsync for better control
rsync -av --exclude='*.pyc' --exclude='__pycache__' security/ /path/to/target/project/security/
```

### Step 2: Verify Directory Structure

Ensure the following structure exists in your target project:

```
security/
├── findings/
│   ├── .gitkeep                      # Placeholder for findings directory
│   └── history/
│       └── .gitkeep                  # Placeholder for history directory
├── reports/
│   ├── latest/
│   │   └── .gitkeep                  # Placeholder for latest reports
│   └── archived/
│       └── .gitkeep                  # Placeholder for archived reports
├── scripts/
│   ├── update-findings.py            # Core automation engine
│   ├── migrate-legacy-reports.py     # Migration utilities
│   ├── validate-findings-document.py # Validation tools
│   └── fix-timeline.py               # Timeline repair utilities
├── config/
│   ├── scanner-settings.yml          # Scanner configurations
│   ├── findings-template.md          # Document templates
│   └── remediation-defaults.yml      # Default remediation values
├── *.py                              # Core module files
├── README.md                         # Module documentation
└── DEPLOYMENT.md                     # This deployment guide
```

### Step 3: Install Python Dependencies

The security module requires minimal Python dependencies:

```bash
# Using pip
pip install PyYAML

# Using uv (recommended)
uv add PyYAML

# Using poetry
poetry add PyYAML

# Using pipenv
pipenv install PyYAML
```

### Step 4: Configure Security Scanners

Update your project's security scanning setup to output to the security module:

#### For pip-audit:
```bash
# Add to your security scan script
pip-audit --format=json --output=security/reports/latest/pip-audit.json
```

#### For bandit:
```bash
# Add to your security scan script
bandit -r . -f json -o security/reports/latest/bandit.json
```

#### For secrets scanning:
```bash
# Example with detect-secrets
detect-secrets scan --all-files --force-use-all-plugins > security/reports/latest/secrets-scan.json
```

### Step 5: Update CI/CD Workflows

Modify your existing CI/CD workflows to integrate with the security module:

#### GitHub Actions Example:

```yaml
name: Security Scan and Update

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]
  schedule:
    - cron: '0 2 * * *'  # Daily at 2 AM

jobs:
  security-scan:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.9'
    
    - name: Install dependencies
      run: |
        pip install pip-audit bandit PyYAML
    
    - name: Run security scans
      run: |
        # Create reports directory if it doesn't exist
        mkdir -p security/reports/latest
        
        # Run pip-audit
        pip-audit --format=json --output=security/reports/latest/pip-audit.json || echo "pip-audit failed"
        
        # Run bandit
        bandit -r . -f json -o security/reports/latest/bandit.json || echo "bandit failed"
        
        # Generate dependency tree
        pip freeze > security/reports/latest/dependency-tree.txt
    
    - name: Update security findings
      run: |
        python security/scripts/update-findings.py
    
    - name: Commit security updates
      run: |
        git config --local user.email "action@github.com"
        git config --local user.name "GitHub Action"
        git add security/
        git diff --staged --quiet || git commit -m "chore: update security findings [skip ci]"
        git push || echo "No changes to push"
```

### Step 6: Initial Configuration

#### Configure Scanner Settings

Edit `security/config/scanner-settings.yml`:

```yaml
# Scanner configuration
scanners:
  pip-audit:
    enabled: true
    output_file: "security/reports/latest/pip-audit.json"
    format: "json"
    
  bandit:
    enabled: true
    output_file: "security/reports/latest/bandit.json"
    format: "json"
    
  secrets:
    enabled: false  # Enable if you use secrets scanning
    output_file: "security/reports/latest/secrets-scan.json"
    format: "json"

# Archival settings
archival:
  enabled: true
  retention_days: 365
  archive_path: "security/reports/archived"

# Document generation
document:
  template: "security/config/findings-template.md"
  output: "security/findings/SECURITY_FINDINGS.md"
  include_resolved: false
  max_age_days: 90
```

#### Configure Remediation Defaults

Edit `security/config/remediation-defaults.yml`:

```yaml
# Default remediation values for new findings
defaults:
  new_finding:
    status: "new"
    planned_action: "Under evaluation"
    target_date: null
    assigned_to: "security-team"  # Change to your team
    notes: "Newly discovered - assessment in progress"
    workaround: "None identified"
    priority: "medium"
    business_impact: "To be assessed"

# Status workflow definitions
status_workflow:
  - "new"
  - "in_progress"
  - "awaiting_upstream"
  - "completed"
  - "accepted_risk"
  - "false_positive"

# Priority levels
priority_levels:
  - "critical"
  - "high"
  - "medium"
  - "low"
  - "info"

# SLA targets (days)
sla_targets:
  critical: 1
  high: 7
  medium: 30
  low: 90
  info: 180

# Assignment rules by severity
assignment_rules:
  critical: "security-team"
  high: "security-team"
  medium: "dev-team"
  low: "dev-team"
  info: "dev-team"
```

### Step 7: Run Initial Setup

Execute the initial setup to create baseline files:

```bash
# Create initial directory structure (if needed)
mkdir -p security/findings/history
mkdir -p security/reports/latest
mkdir -p security/reports/archived

# Run initial security scans
pip-audit --format=json --output=security/reports/latest/pip-audit.json
bandit -r . -f json -o security/reports/latest/bandit.json

# Generate initial findings document
python security/scripts/update-findings.py

# Verify setup
ls -la security/findings/
```

## Configuration Guide for Different Scanner Setups

### Minimal Setup (pip-audit only)

For projects that only need dependency vulnerability scanning:

```yaml
# security/config/scanner-settings.yml
scanners:
  pip-audit:
    enabled: true
    output_file: "security/reports/latest/pip-audit.json"
    format: "json"
  
  bandit:
    enabled: false
  
  secrets:
    enabled: false
```

### Comprehensive Setup (All Scanners)

For projects requiring full security coverage:

```yaml
# security/config/scanner-settings.yml
scanners:
  pip-audit:
    enabled: true
    output_file: "security/reports/latest/pip-audit.json"
    format: "json"
    
  bandit:
    enabled: true
    output_file: "security/reports/latest/bandit.json"
    format: "json"
    exclude_paths: ["tests/", "docs/"]
    
  secrets:
    enabled: true
    output_file: "security/reports/latest/secrets-scan.json"
    format: "json"
    
  safety:
    enabled: true
    output_file: "security/reports/latest/safety.json"
    format: "json"
```

### Enterprise Setup (Custom Scanners)

For organizations with custom security tools:

```yaml
# security/config/scanner-settings.yml
scanners:
  pip-audit:
    enabled: true
    output_file: "security/reports/latest/pip-audit.json"
    format: "json"
    
  custom_scanner:
    enabled: true
    output_file: "security/reports/latest/custom-scan.json"
    format: "json"
    command: "/path/to/custom/scanner"
    args: ["--format", "json", "--output", "security/reports/latest/custom-scan.json"]

# Custom parser configuration
parsers:
  custom_scanner:
    finding_id_field: "vulnerability_id"
    severity_field: "risk_level"
    package_field: "component_name"
    version_field: "component_version"
```

## Remediation Workflow and Manual Editing

### Understanding the Remediation Registry

The remediation registry (`security/findings/remediation-plans.yml`) maintains a 1:1 mapping between security findings and remediation plans:

```yaml
findings:
  CVE-2025-8869:
    finding_id: "CVE-2025-8869"
    package: "pip"
    version: "25.2"
    severity: "high"
    remediation:
      status: "awaiting_upstream"
      planned_action: "Upgrade to pip 25.3 when released"
      target_date: "2025-11-15"
      assigned_to: "security-team"
      notes: "Official fix planned for pip 25.3 release"
      workaround: "None - vulnerability requires malicious sdist"
      priority: "high"
      business_impact: "Potential arbitrary file overwrite"
```

### Manual Editing Workflow

1. **Review Findings**: Check `security/findings/SECURITY_FINDINGS.md` for new vulnerabilities
2. **Edit Remediation Plans**: Modify `security/findings/remediation-plans.yml` with specific remediation details
3. **Preserve Manual Edits**: The automation system preserves manual edits during synchronization
4. **Track Progress**: Update status fields as remediation progresses

### Safe Manual Editing Guidelines

#### DO:
- Edit `planned_action`, `target_date`, `assigned_to`, `notes`, `workaround` fields
- Update `status` to reflect current remediation progress
- Add detailed `business_impact` assessments
- Set realistic `target_date` values

#### DON'T:
- Modify `finding_id`, `package`, `version`, `severity` (these are synchronized from scan results)
- Delete entire finding entries (they will be recreated)
- Use invalid status values (must match `status_workflow` in config)

### Remediation Status Workflow

```
new → in_progress → awaiting_upstream → completed
  ↓       ↓              ↓
accepted_risk    false_positive
```

#### Status Definitions:
- **new**: Recently discovered, assessment needed
- **in_progress**: Actively working on remediation
- **awaiting_upstream**: Waiting for vendor fix
- **completed**: Vulnerability resolved
- **accepted_risk**: Risk accepted, no action planned
- **false_positive**: Not a real vulnerability

### Example Manual Edits

#### High Priority Vulnerability:
```yaml
CVE-2025-1234:
  finding_id: "CVE-2025-1234"
  package: "requests"
  version: "2.28.0"
  severity: "high"
  remediation:
    status: "in_progress"
    planned_action: "Upgrade to requests 2.31.0 - testing in staging environment"
    target_date: "2025-11-01"
    assigned_to: "john.doe@company.com"
    notes: "Upgrade requires testing authentication flows. Staging deployment scheduled for 2025-10-28."
    workaround: "Input validation implemented in auth middleware"
    priority: "high"
    business_impact: "Could affect user authentication system"
```

#### Accepted Risk:
```yaml
CVE-2025-5678:
  finding_id: "CVE-2025-5678"
  package: "old-library"
  version: "1.0.0"
  severity: "medium"
  remediation:
    status: "accepted_risk"
    planned_action: "Risk accepted - library used in isolated test environment only"
    target_date: null
    assigned_to: "security-team"
    notes: "Library only used in development tests, not in production. Risk assessment completed 2025-10-24."
    workaround: "Library isolated in test containers"
    priority: "low"
    business_impact: "No production impact - test environment only"
```

## Troubleshooting Guide

### Common Configuration Issues

#### Issue: Scan files not found
**Symptoms**: Empty findings document, "No scan files found" errors

**Solutions**:
1. Verify scanner output paths in `security/config/scanner-settings.yml`
2. Check that scanners are actually running and producing output
3. Ensure `security/reports/latest/` directory exists and is writable

```bash
# Debug scanner output
ls -la security/reports/latest/
cat security/reports/latest/pip-audit.json | head -20
```

#### Issue: Permission denied errors
**Symptoms**: Cannot write to security directory, automation script fails

**Solutions**:
1. Check directory permissions:
```bash
chmod -R 755 security/
```

2. Verify user has write access to security directory
3. In CI/CD, ensure proper permissions are set:
```yaml
- name: Set permissions
  run: chmod -R 755 security/
```

#### Issue: Malformed scan output
**Symptoms**: JSON parsing errors, incomplete findings

**Solutions**:
1. Validate JSON output:
```bash
python -m json.tool security/reports/latest/pip-audit.json
```

2. Check scanner version compatibility
3. Review scanner command line arguments
4. Examine scanner error logs

#### Issue: Remediation sync conflicts
**Symptoms**: Manual edits being overwritten, duplicate entries

**Solutions**:
1. Verify finding IDs are unique and consistent
2. Check for concurrent automation runs
3. Review manual edit format against schema
4. Use atomic file operations:
```bash
# Backup before manual edits
cp security/findings/remediation-plans.yml security/findings/remediation-plans.yml.backup
```

### Scanner-Specific Issues

#### pip-audit Issues:
```bash
# Common pip-audit problems and solutions

# Issue: pip-audit not found
pip install pip-audit

# Issue: No vulnerabilities found (but expecting some)
pip-audit --desc  # Show descriptions for debugging

# Issue: JSON format issues
pip-audit --format=json --output=- | python -m json.tool  # Validate JSON
```

#### bandit Issues:
```bash
# Common bandit problems and solutions

# Issue: bandit not found
pip install bandit

# Issue: Too many false positives
bandit -r . -f json -ll  # Lower confidence level

# Issue: Excluding test files
bandit -r . -f json --exclude=tests/,docs/
```

### CI/CD Integration Issues

#### Issue: GitHub Actions permissions
**Symptoms**: Cannot commit security updates, push failures

**Solutions**:
1. Add proper permissions to workflow:
```yaml
permissions:
  contents: write
  pull-requests: write
```

2. Use proper authentication:
```yaml
- uses: actions/checkout@v4
  with:
    token: ${{ secrets.GITHUB_TOKEN }}
```

#### Issue: Workflow timeouts
**Symptoms**: Security scans taking too long, workflow failures

**Solutions**:
1. Add timeout settings:
```yaml
jobs:
  security-scan:
    timeout-minutes: 30
```

2. Optimize scanner configurations
3. Use caching for dependencies:
```yaml
- uses: actions/cache@v3
  with:
    path: ~/.cache/pip
    key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements.txt') }}
```

### Data Integrity Issues

#### Issue: Missing historical data
**Symptoms**: Empty history files, no audit trail

**Solutions**:
1. Initialize history files:
```bash
python security/scripts/update-findings.py --initialize-history
```

2. Migrate from legacy data:
```bash
python security/scripts/migrate-legacy-reports.py
```

#### Issue: Inconsistent finding IDs
**Symptoms**: Duplicate findings, sync errors

**Solutions**:
1. Validate finding ID format
2. Check scanner output consistency
3. Review parser logic for ID extraction
4. Use validation script:
```bash
python security/scripts/validate-findings-document.py
```

### Performance Issues

#### Issue: Slow automation execution
**Symptoms**: Long processing times, CI/CD delays

**Solutions**:
1. Profile automation script:
```bash
python -m cProfile security/scripts/update-findings.py
```

2. Optimize file I/O operations
3. Implement incremental processing
4. Use parallel processing for multiple scanners

#### Issue: Large file sizes
**Symptoms**: Git repository bloat, slow clones

**Solutions**:
1. Implement archival rotation:
```bash
# Keep only last 30 days of archived reports
find security/reports/archived/ -type d -mtime +30 -exec rm -rf {} \;
```

2. Use `.gitignore` for temporary files:
```gitignore
security/reports/latest/*.tmp
security/findings/*.backup
```

### Getting Additional Help

#### Debug Mode
Enable debug logging in automation scripts:
```bash
export DEBUG=1
python security/scripts/update-findings.py
```

#### Validation Tools
Use built-in validation:
```bash
# Validate findings document structure
python security/scripts/validate-findings-document.py

# Check remediation plan integrity
python -c "import yaml; yaml.safe_load(open('security/findings/remediation-plans.yml'))"
```

#### Community Support
1. Check project documentation in `security/README.md`
2. Review example configurations in `security/config/`
3. Examine test cases for expected behavior
4. Create minimal reproduction case for issues

This deployment guide provides comprehensive instructions for successfully deploying and configuring the security module in new projects. The modular design ensures consistent behavior across different environments while maintaining flexibility for project-specific requirements.