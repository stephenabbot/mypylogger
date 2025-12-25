#!/bin/bash

# Simple script to resolve security file timestamp conflicts
# Usage: ./scripts/resolve_security_conflicts.sh

set -e

echo "🔧 Resolving security file timestamp conflicts..."

# Check if we're in a rebase
if [ ! -d ".git/rebase-apply" ] && [ ! -d ".git/rebase-merge" ]; then
    echo "❌ No rebase in progress. Run this script during a rebase conflict."
    exit 1
fi

# Set Git editor to avoid interactive prompts
export GIT_EDITOR="true"

echo "📝 Accepting newer timestamps for security files..."

# Resolve conflicts by accepting "theirs" (newer timestamps)
git checkout --theirs security/findings/SECURITY_FINDINGS.md 2>/dev/null || echo "  - SECURITY_FINDINGS.md: no conflict or file not found"
git checkout --theirs security/reports/latest/bandit.json 2>/dev/null || echo "  - latest/bandit.json: no conflict or file not found"
git checkout --theirs security/reports/archived/*/bandit.json 2>/dev/null || echo "  - archived bandit.json files: no conflicts or files not found"

# Stage the resolved files
echo "📦 Staging resolved files..."
git add security/ 2>/dev/null || echo "  - No security files to stage"

# Continue the rebase automatically
echo "🚀 Continuing rebase..."
git rebase --continue

echo "✅ Security conflicts resolved and rebase continued!"
echo "💡 If more conflicts appear, run this script again."