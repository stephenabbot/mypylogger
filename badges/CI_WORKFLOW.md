# CI-Only Badge Update Workflow

This document describes the CI-only badge update workflow for mypylogger v0.2.0, which ensures badges always reflect the actual state of code in the main branch.

## Overview

The badge system is designed to work exclusively in CI/CD environments to prevent local inconsistencies and ensure badges reflect actual tested code state. Local development focuses on code quality validation only.

## Workflow Architecture

```
Local Development          CI/CD Environment
─────────────────          ─────────────────
                          
Code Changes               ┌─ Quality Gate Tests ─┐
     │                     │                      │
     ▼                     │  • Linting           │
                          │  • Type Checking     │
Local Testing             │  • Unit Tests        │
• Code Quality Only       │  • Security Scans    │
• No Badge Updates        │                      │
• Security Validation     └──────────────────────┘
                                      │
     │                               ▼
     ▼                          Tests Pass?
                                      │
Push to Main Branch                  ▼
     │                          ┌─ Badge Updates ─┐
     ▼                          │                 │
                               │  • Generate URLs │
GitHub Actions                 │  • Update README │
     │                          │  • Commit Changes│
     ▼                          │  • Push to Main  │
                               └─────────────────────┘
```

## Local Development Workflow

### Focus Areas
- **Code Quality**: Linting, formatting, type checking
- **Test Execution**: Unit tests, integration tests
- **Security Validation**: Local security scans for validation only
- **Badge Generation**: Test badge generation without README updates

### Restricted Operations
- ❌ README badge updates
- ❌ Badge commits to repository
- ❌ Badge status modifications

### Commands
```bash
# Run all quality checks (no badge updates)
./scripts/run_tests.sh

# Test badge generation only (local development)
uv run python -m badges --generate-only --no-status-detection

# Phase-specific testing
./scripts/run_tests.sh --phase=phase-5-project-badges
```

## CI/CD Workflow

### Trigger Conditions
Badge updates occur automatically when:
- ✅ All quality gate tests pass
- ✅ Running in CI environment (`GITHUB_ACTIONS=true`)
- ✅ Tests have passed (`TESTS_PASSED=true`)
- ✅ On main branch (`refs/heads/main`)

### Badge Update Process

1. **Environment Verification**
   ```bash
   # CI environment check
   if [ "$GITHUB_ACTIONS" = "true" ] && [ "$TESTS_PASSED" = "true" ]; then
     # Proceed with badge updates
   fi
   ```

2. **Git Configuration**
   ```bash
   git config --local user.email "action@github.com"
   git config --local user.name "GitHub Action"
   ```

3. **Badge Generation**
   ```bash
   uv run python -m badges --ci-mode
   ```

4. **README Update**
   - Generate all 8 badge types
   - Update README.md with new badges
   - Commit with `[skip ci]` message
   - Push to main branch

### GitHub Actions Integration

#### Quality Gate Workflow
```yaml
- name: Update badges (CI-only)
  if: success() && github.ref == 'refs/heads/main'
  run: |
    export PATH="$HOME/.cargo/bin:$PATH"
    export TESTS_PASSED=true
    export GITHUB_REPOSITORY=${{ github.repository }}
    export PYPI_PACKAGE=mypylogger
    uv run python -m badges --ci-mode
  env:
    GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

#### Required Permissions
```yaml
permissions:
  contents: write         # Required for badge updates
  security-events: read   # Required for CodeQL status
```

## Badge Types

The system generates 8 badge types:

1. **Quality Gate**: Overall CI/CD status
2. **Security**: Comprehensive security status (local + GitHub CodeQL)
3. **Code Style**: Ruff formatting compliance
4. **Type Checking**: mypy validation status
5. **Python Versions**: Supported Python versions
6. **PyPI Version**: Current package version
7. **Downloads**: Monthly PyPI download count
8. **License**: MIT license badge

## PyPI Compatibility

### Package Structure
The badge system is designed to work correctly with PyPI package structure:

```
mypylogger/
├── src/mypylogger/     # Main package
├── badges/             # Badge system (development only)
├── README.md           # Package description with badges
└── pyproject.toml      # Package configuration
```

### PyPI Integration
- **Version Badge**: Uses PyPI API for real-time version display
- **Downloads Badge**: Uses shields.io direct PyPI integration
- **Python Versions**: Reflects pyproject.toml compatibility

### Post-Publication Verification
After PyPI publication, badges automatically reflect:
- ✅ Current published version
- ✅ Real-time download statistics
- ✅ Python version compatibility
- ✅ License information

## Configuration

### Environment Variables
```bash
# Required for CI badge updates
export GITHUB_ACTIONS=true
export TESTS_PASSED=true
export GITHUB_REPOSITORY=owner/repo
export PYPI_PACKAGE=package-name

# Optional for GitHub API access
export GITHUB_TOKEN=ghp_xxx
```

### Badge Configuration
Located in `badges/config.py`:
```python
BADGE_CONFIG = {
    'github_repo': 'stabbotco1/mypylogger',
    'pypi_package': 'mypylogger',
    'shields_base_url': 'https://img.shields.io',
    # ... additional configuration
}
```

## Security Considerations

### CI-Only Updates
- Prevents local badge inconsistencies
- Ensures badges reflect actual CI test results
- Maintains single source of truth (CI environment)

### Git Operations
- Uses `[skip ci]` to prevent infinite loops
- Atomic README updates with retry logic
- Proper error handling and rollback

### API Security
- GitHub API access with proper token handling
- Rate limit respect and error handling
- No sensitive data in badge URLs

## Troubleshooting

### Common Issues

#### Badge Updates Not Working
```bash
# Check CI environment
echo "GITHUB_ACTIONS: $GITHUB_ACTIONS"
echo "TESTS_PASSED: $TESTS_PASSED"

# Check permissions
# Ensure workflow has contents: write permission
```

#### Local Badge Update Attempts
```bash
# Expected behavior - should fail
uv run python -m badges
# Output: "Badge updates are only allowed in CI/CD environments"
```

#### Git Configuration Issues
```bash
# Manual git setup (CI should handle this)
git config --local user.email "action@github.com"
git config --local user.name "GitHub Action"
```

### Debug Commands
```bash
# Test badge generation (local)
uv run python -m badges --generate-only --verbose

# Check badge configuration
uv run python -m badges --config-check

# Dry run (no actual updates)
uv run python -m badges --dry-run
```

## Development vs CI Separation

| Aspect | Local Development | CI/CD Environment |
|--------|------------------|-------------------|
| **Focus** | Code Quality | Badge Accuracy |
| **Tests** | All quality checks | All quality checks + badge updates |
| **Security** | Validation only | Validation + badge integration |
| **README** | No modifications | Automatic updates |
| **Git** | Manual commits | Automated badge commits |
| **Speed** | Fast feedback | Complete validation |

## Best Practices

### For Developers
1. **Focus on Code Quality**: Use local testing for rapid feedback
2. **Trust CI for Badges**: Let CI handle badge accuracy
3. **Test Badge Generation**: Use `--generate-only` for testing
4. **Review Badge Changes**: Check CI-generated badge updates

### For CI/CD
1. **Run After Tests**: Only update badges after successful tests
2. **Use Proper Permissions**: Ensure `contents: write` permission
3. **Handle Failures Gracefully**: Don't fail builds on badge errors
4. **Monitor API Limits**: Respect GitHub API rate limits

This workflow ensures badges are always accurate, up-to-date, and reflect the actual state of the codebase as validated by CI/CD processes.