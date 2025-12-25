#!/bin/bash

# Quick push script to add, commit, pull with rebase, and push
# Usage: ./scripts/quick_push.sh "commit message"

set -e  # Exit on any error

# Check if commit message is provided
if [ -z "$1" ]; then
    echo "Error: Please provide a commit message"
    echo "Usage: ./scripts/quick_push.sh \"your commit message\""
    exit 1
fi

COMMIT_MSG="$1"

echo "🔄 Adding all changes..."
git add .

echo "📝 Committing with message: $COMMIT_MSG"
git commit -m "$COMMIT_MSG"

echo "⬇️ Pulling with rebase..."
git pull --rebase origin main

echo "⬆️ Pushing to origin..."
git push origin main

echo "✅ Done! GitHub Actions should be triggered now."