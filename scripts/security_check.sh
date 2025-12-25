#!/bin/bash

# Security Check Script for mypylogger v0.2.8
#
# This script performs comprehensive local security validation
# to ensure code meets zero-tolerance security policy before
# pushing to the repository.
#
# Requirements Addressed:
# - 6.3: Fail on any security vulnerabilities
# - 6.4: Require zero security issues before code integration
# - 6.5: Scan both direct and transitive dependencies
# - 6.6: Provide detailed security reporting

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SECURITY_REPORT_DIR="$PROJECT_ROOT/security/reports/latest"
TIMESTAMP=$(date -u '+%Y%m%d_%H%M%S')

# Handle command line arguments
if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
    echo -e "${BLUE}🛡️  mypylogger v0.2.8 Security Check Script${NC}"
    echo -e "${BLUE}====================================${NC}"
    echo ""
    echo "This script performs comprehensive local security validation"
    echo "to ensure code meets zero-tolerance security policy."
    echo ""
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  --help, -h    Show this help message"
    echo "  --version     Show version information"
    echo ""
    echo "Security checks performed:"
    echo "  • Dependency vulnerability scanning"
    echo "  • Code security analysis"
    echo "  • Secret detection"
    echo "  • Configuration validation"
    echo ""
    exit 0
fi

if [[ "${1:-}" == "--version" ]]; then
    echo "mypylogger v0.2.8 Security Check Script"
    echo "Zero-tolerance security policy enforcement"
    exit 0
fi

# Create security reports directory
mkdir -p "$SECURITY_REPORT_DIR"

echo -e "${BLUE}🛡️  mypylogger v0.2.8 Security Check Script${NC}"
echo -e "${BLUE}====================================${NC}"
echo "Timestamp: $(date -u '+%Y-%m-%d %H:%M:%S UTC')"
echo "Project root: $PROJECT_ROOT"
echo "Reports directory: $SECURITY_REPORT_DIR"
echo ""

# Function to print section headers
print_section() {
    echo -e "\n${BLUE}$1${NC}"
    echo -e "${BLUE}$(printf '=%.0s' $(seq 1 ${#1}))${NC}"
}

# Function to print success messages
print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

# Function to print error messages
print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Function to print warning messages
print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Initialize security check results
SECURITY_ISSUES_FOUND=0
DEPENDENCY_ISSUES=0
CODE_ISSUES=0
SECRET_ISSUES=0

# Change to project root
cd "$PROJECT_ROOT"

print_section "🔍 Environment Validation"

# Check if we're in a git repository
if [ ! -d ".git" ]; then
    print_error "Not in a git repository. Please run from project root."
    exit 1
fi

# Check if UV is available
if ! command_exists uv; then
    print_error "UV package manager not found. Please install UV first."
    echo "Install with: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

# Check if project dependencies are installed
if [ ! -f "uv.lock" ]; then
    print_error "uv.lock file not found. Please run 'uv sync' first."
    exit 1
fi

print_success "Environment validation passed"

print_section "📦 Installing Security Tools"

# Install security tools
echo "Installing security analysis tools..."
uv run pip install bandit safety pip-audit truffleHog3 || {
    print_error "Failed to install security tools"
    exit 1
}

print_success "Security tools installed successfully"

print_section "🔒 Dependency Security Scan"

echo "Scanning dependencies for known vulnerabilities..."

# Run pip-audit for comprehensive dependency scanning
echo "Running pip-audit (comprehensive dependency audit)..."
AUDIT_REPORT="$SECURITY_REPORT_DIR/pip-audit-$TIMESTAMP.json"
if uv run pip-audit --format=json --output="$AUDIT_REPORT" --progress-spinner=off; then
    print_success "pip-audit: No vulnerabilities found"
else
    print_error "pip-audit: Vulnerabilities detected"
    echo "Detailed report: $AUDIT_REPORT"
    uv run pip-audit --format=table --progress-spinner=off || true
    DEPENDENCY_ISSUES=$((DEPENDENCY_ISSUES + 1))
    SECURITY_ISSUES_FOUND=$((SECURITY_ISSUES_FOUND + 1))
fi

# Run safety check for known vulnerabilities
echo ""
echo "Running safety check (known vulnerability database)..."
SAFETY_REPORT="$SECURITY_REPORT_DIR/safety-$TIMESTAMP.json"
if uv run safety check --json --output="$SAFETY_REPORT"; then
    print_success "safety: No known vulnerabilities found"
else
    print_error "safety: Known vulnerabilities detected"
    echo "Detailed report: $SAFETY_REPORT"
    uv run safety check || true
    DEPENDENCY_ISSUES=$((DEPENDENCY_ISSUES + 1))
    SECURITY_ISSUES_FOUND=$((SECURITY_ISSUES_FOUND + 1))
fi

# Generate dependency tree for analysis
echo ""
echo "Generating dependency tree for analysis..."
DEPENDENCY_TREE="$SECURITY_REPORT_DIR/dependency-tree-$TIMESTAMP.txt"
uv tree --frozen > "$DEPENDENCY_TREE"
print_success "Dependency tree generated: $DEPENDENCY_TREE"

print_section "🔬 Code Security Analysis"

echo "Analyzing source code for security vulnerabilities..."

# Run Bandit security linter
echo "Running Bandit (Python security linter)..."
BANDIT_REPORT="$SECURITY_REPORT_DIR/bandit-$TIMESTAMP.json"
if uv run bandit -r src/ -f json -o "$BANDIT_REPORT" -ll; then
    print_success "Bandit: No security issues found in source code"
else
    print_error "Bandit: Security issues detected in source code"
    echo "Detailed report: $BANDIT_REPORT"
    echo ""
    echo "Security issues found:"
    uv run bandit -r src/ -f txt || true
    CODE_ISSUES=$((CODE_ISSUES + 1))
    SECURITY_ISSUES_FOUND=$((SECURITY_ISSUES_FOUND + 1))
fi

# Additional code pattern checks
echo ""
echo "Running additional security pattern checks..."

# Check for common insecure patterns
PATTERN_ISSUES=0

# Check for hardcoded secrets patterns
if grep -r -i -E "(password|secret|key|token|api_key)\s*=\s*['\"][^'\"]+['\"]" src/ --include="*.py" 2>/dev/null; then
    print_error "Potential hardcoded secrets found in source code"
    PATTERN_ISSUES=$((PATTERN_ISSUES + 1))
fi

# Check for SQL injection patterns
if grep -r -E "execute\s*\(\s*['\"].*%.*['\"]" src/ --include="*.py" 2>/dev/null; then
    print_error "Potential SQL injection patterns found"
    PATTERN_ISSUES=$((PATTERN_ISSUES + 1))
fi

# Check for eval/exec usage
if grep -r -E "(eval|exec)\s*\(" src/ --include="*.py" 2>/dev/null; then
    print_error "Dangerous eval/exec usage found"
    PATTERN_ISSUES=$((PATTERN_ISSUES + 1))
fi

if [ $PATTERN_ISSUES -eq 0 ]; then
    print_success "No insecure code patterns detected"
else
    CODE_ISSUES=$((CODE_ISSUES + PATTERN_ISSUES))
    SECURITY_ISSUES_FOUND=$((SECURITY_ISSUES_FOUND + PATTERN_ISSUES))
fi

print_section "🕵️  Secret Detection Scan"

echo "Scanning repository for exposed secrets..."

# Check if TruffleHog is available (try different installation methods)
TRUFFLEHOG_CMD=""
if command_exists trufflehog; then
    TRUFFLEHOG_CMD="trufflehog"
elif command_exists truffleHog; then
    TRUFFLEHOG_CMD="truffleHog"
elif uv run python -c "import truffleHog3" 2>/dev/null; then
    TRUFFLEHOG_CMD="uv run python -m truffleHog3"
else
    print_warning "TruffleHog not available, using basic secret pattern detection"
fi

SECRET_SCAN_REPORT="$SECURITY_REPORT_DIR/secret-scan-$TIMESTAMP.json"

if [ -n "$TRUFFLEHOG_CMD" ]; then
    echo "Running TruffleHog secret detection..."
    if $TRUFFLEHOG_CMD git file://. --json --no-update > "$SECRET_SCAN_REPORT" 2>/dev/null; then
        # Check if any secrets were found
        if [ -s "$SECRET_SCAN_REPORT" ] && [ "$(cat "$SECRET_SCAN_REPORT" | wc -l)" -gt 0 ]; then
            print_error "Secrets detected in repository"
            echo "Detailed report: $SECRET_SCAN_REPORT"
            cat "$SECRET_SCAN_REPORT" | head -20  # Show first 20 lines
            SECRET_ISSUES=$((SECRET_ISSUES + 1))
            SECURITY_ISSUES_FOUND=$((SECURITY_ISSUES_FOUND + 1))
        else
            print_success "TruffleHog: No secrets detected"
        fi
    else
        print_warning "TruffleHog scan failed, falling back to pattern detection"
    fi
fi

# Basic secret pattern detection as fallback
echo ""
echo "Running basic secret pattern detection..."
SECRET_PATTERNS_FOUND=0

# Common secret patterns
SECRET_PATTERNS=(
    "-----BEGIN.*PRIVATE KEY-----"
    "-----BEGIN.*CERTIFICATE-----"
    "['\"][A-Za-z0-9+/]{40,}['\"]"  # Base64 encoded secrets
    "AKIA[0-9A-Z]{16}"              # AWS Access Key
    "sk_live_[0-9a-zA-Z]{24}"       # Stripe Live Key
    "sk_test_[0-9a-zA-Z]{24}"       # Stripe Test Key
    "ghp_[0-9a-zA-Z]{36}"           # GitHub Personal Access Token
)

for pattern in "${SECRET_PATTERNS[@]}"; do
    if grep -r -E "$pattern" . --exclude-dir=.git --exclude-dir=.mypy_cache --exclude-dir=.pytest_cache --exclude-dir=security 2>/dev/null; then
        print_error "Potential secret pattern found: $pattern"
        SECRET_PATTERNS_FOUND=$((SECRET_PATTERNS_FOUND + 1))
    fi
done

# Check for common secret files
echo ""
echo "Checking for common secret file patterns..."
SECRET_FILES=$(find . -type f \( \
    -name "*.pem" -o \
    -name "*.key" -o \
    -name "*.p12" -o \
    -name "*.pfx" -o \
    -name ".env" -o \
    -name ".env.*" -o \
    -name "id_rsa" -o \
    -name "id_dsa" -o \
    -name "*.crt" -o \
    -name "*.cer" \
\) -not -path "./.git/*" -not -path "./.*cache/*" 2>/dev/null || true)

if [ -n "$SECRET_FILES" ]; then
    print_warning "Potential secret files detected:"
    echo "$SECRET_FILES"
    echo "Please verify these files do not contain sensitive information."
fi

if [ $SECRET_PATTERNS_FOUND -eq 0 ]; then
    print_success "No secret patterns detected"
else
    SECRET_ISSUES=$((SECRET_ISSUES + SECRET_PATTERNS_FOUND))
    SECURITY_ISSUES_FOUND=$((SECURITY_ISSUES_FOUND + SECRET_PATTERNS_FOUND))
fi

print_section "📊 Security Scan Summary"

echo "Security scan completed at: $(date -u '+%Y-%m-%d %H:%M:%S UTC')"
echo ""
echo "Scan Results:"
echo "============="
echo "Dependency issues found: $DEPENDENCY_ISSUES"
echo "Code security issues found: $CODE_ISSUES"
echo "Secret detection issues found: $SECRET_ISSUES"
echo "Total security issues found: $SECURITY_ISSUES_FOUND"
echo ""

# Generate summary report
SUMMARY_REPORT="$SECURITY_REPORT_DIR/security-summary-$TIMESTAMP.json"
cat > "$SUMMARY_REPORT" << EOF
{
  "timestamp": "$(date -u '+%Y-%m-%d %H:%M:%S UTC')",
  "scan_type": "local_security_check",
  "project": "mypylogger-v0.2.0",
  "results": {
    "total_issues": $SECURITY_ISSUES_FOUND,
    "dependency_issues": $DEPENDENCY_ISSUES,
    "code_issues": $CODE_ISSUES,
    "secret_issues": $SECRET_ISSUES
  },
  "reports": {
    "pip_audit": "$AUDIT_REPORT",
    "safety": "$SAFETY_REPORT",
    "bandit": "$BANDIT_REPORT",
    "secret_scan": "$SECRET_SCAN_REPORT",
    "dependency_tree": "$DEPENDENCY_TREE"
  },
  "zero_tolerance_policy": {
    "enabled": true,
    "policy_met": $([ $SECURITY_ISSUES_FOUND -eq 0 ] && echo "true" || echo "false")
  }
}
EOF

echo "Summary report generated: $SUMMARY_REPORT"
echo ""

# Zero-tolerance policy enforcement
print_section "🚨 Zero-Tolerance Policy Enforcement"

if [ $SECURITY_ISSUES_FOUND -eq 0 ]; then
    print_success "SECURITY POLICY COMPLIANCE"
    echo ""
    echo "🎉 Excellent! No security issues detected."
    echo ""
    echo "✅ Zero-tolerance policy requirements met:"
    echo "  - No dependency vulnerabilities found"
    echo "  - No code security issues detected"
    echo "  - No secrets exposed in repository"
    echo ""
    echo "Your code is ready for commit and push to the repository."
    echo "The CI/CD security scans should pass successfully."
    echo ""
    echo "Next steps:"
    echo "1. Commit your changes: git add . && git commit -m 'your message'"
    echo "2. Push to repository: git push origin main"
    echo "3. Monitor CI/CD security scan results"
    
    exit 0
else
    print_error "SECURITY POLICY VIOLATION"
    echo ""
    echo "🚨 CRITICAL: Security issues detected!"
    echo ""
    echo "❌ Zero-tolerance policy violation:"
    echo "  - Total security issues: $SECURITY_ISSUES_FOUND"
    echo "  - Dependency vulnerabilities: $DEPENDENCY_ISSUES"
    echo "  - Code security issues: $CODE_ISSUES"
    echo "  - Secret exposure issues: $SECRET_ISSUES"
    echo ""
    echo "🔒 REQUIRED ACTIONS:"
    echo "1. Review detailed security reports in: $SECURITY_REPORT_DIR"
    echo "2. Fix ALL identified security vulnerabilities"
    echo "3. Update dependencies to secure versions: uv lock"
    echo "4. Remove any exposed secrets from repository"
    echo "5. Re-run this script to verify fixes: ./scripts/security_check.sh"
    echo "6. Only commit and push after ALL issues are resolved"
    echo ""
    echo "💡 Security Resources:"
    echo "- Project security policy: .github/SECURITY.md"
    echo "- Security configuration: .github/SECURITY_CONFIG.yml"
    echo "- Vulnerability databases: https://github.com/advisories"
    echo ""
    echo "⚠️  DO NOT commit or push code until all security issues are resolved."
    echo "The CI/CD pipeline will block integration of vulnerable code."
    
    exit 1
fi