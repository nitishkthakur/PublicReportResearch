#!/bin/bash
# Pre-commit hook to scan for secrets and API keys
# To install: cp pre-commit-hook.sh .git/hooks/pre-commit && chmod +x .git/hooks/pre-commit

echo "🔍 Running security scan before commit..."

# Run the security scanner on staged files only
python security_scan.py --staged-only 2>/dev/null || {
    echo "❌ Security scan failed - potential secrets detected!"
    echo "🔧 Please review the findings and remove any exposed keys before committing."
    echo "💡 Use environment variables instead of hardcoded keys."
    exit 1
}

echo "✅ Security scan passed - no secrets detected in staged files."
exit 0