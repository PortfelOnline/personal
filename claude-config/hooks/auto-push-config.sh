#!/bin/bash
# Auto-push .claude config changes to GitHub (PortfelOnline/personal)
# Synces CLAUDE.md changes to personal repo and pushes
set -euo pipefail

PERSONAL_DIR="$HOME/personal"

# 1. Sync CLAUDE.md if changed
if diff -q "$HOME/.claude/CLAUDE.md" "$PERSONAL_DIR/CLAUDE.md" 2>/dev/null; then
    echo "[auto-push] CLAUDE.md unchanged"
    exit 0
fi

# 2. Copy to personal repo
cp "$HOME/.claude/CLAUDE.md" "$PERSONAL_DIR/CLAUDE.md"
cd "$PERSONAL_DIR"

# 3. Wait for any running git process (max 10s)
for i in $(seq 1 20); do
    if [ -f .git/index.lock ]; then
        sleep 0.5
    else
        break
    fi
done

# 4. Commit and push
git add CLAUDE.md
git diff --cached --quiet && echo "[auto-push] Nothing changed" && exit 0

TIMESTAMP=$(date -u '+%Y-%m-%d %H:%M UTC')
git commit -m "chore: auto-push .claude config [$TIMESTAMP]"
git push origin main 2>&1 || echo "[auto-push] Push failed (network?)"
echo "[auto-push] Done"
