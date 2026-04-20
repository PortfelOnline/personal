#!/bin/bash
export PATH="/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin"
# Generic updater for reference repos.
# Installed as LaunchAgent com.local.refs.update.
#
# Sources of repos:
#   1) Any subdir of ~/.claude/refs/ that contains a .git (managed pool — safe to hard-reset)
#   2) Paths listed in ~/.claude/refs/extra.list (in-place update, SAFETY-GUARDED)
#
# For each repo the script does `git fetch + reset --hard origin/<default-branch>`.
# Safety guard for extra.list entries: SKIP if repo is dirty OR ahead of upstream.
# (Pool entries are assumed read-only, so guard does not apply there.)
#
# Add new managed repo: cd ~/.claude/refs && git clone <url>
# Add new extra path  : echo '~/path/to/repo' >> ~/.claude/refs/extra.list

REFS="$HOME/.claude/refs"
LOG="$HOME/.claude/logs/refs.log"
EXTRA_LIST="$REFS/extra.list"

mkdir -p "$(dirname "$LOG")" "$REFS"

update_repo() {
  local path
  local mode
  local label
  path="$1"
  mode="$2"
  label="$3"

  if [ ! -d "$path/.git" ]; then
    echo "  $label: NOT_A_GIT_REPO ($path)"
    return
  fi

  cd "$path" || { echo "  $label: CANNOT_CD"; return; }

  local branch before after dirty ahead
  branch=$(git symbolic-ref --short HEAD 2>/dev/null)
  [ -z "$branch" ] && branch="main"
  before=$(git rev-parse --short HEAD 2>/dev/null)

  if [ "$mode" = "extra" ]; then
    dirty=$(git status --porcelain 2>/dev/null | awk 'END{print NR}')
    ahead=$(git rev-list --count "@{u}..HEAD" 2>/dev/null)
    [ -z "$ahead" ] && ahead=0
    if [ "$dirty" -ne 0 ] || [ "$ahead" -ne 0 ]; then
      echo "  $label: SKIP (dirty=$dirty ahead=$ahead) @ $before"
      return
    fi
  fi

  git fetch --prune --quiet origin 2>/dev/null
  git reset --hard "origin/$branch" --quiet 2>/dev/null
  git gc --auto --quiet 2>/dev/null
  after=$(git rev-parse --short HEAD 2>/dev/null)

  if [ "$before" = "$after" ]; then
    echo "  $label: up-to-date ($after)"
  else
    echo "  $label: $before → $after"
  fi
}

{
  echo "=== $(date '+%Y-%m-%d %H:%M:%S %Z') ==="

  # 1) Managed pool
  POOL_COUNT=0
  for repo in "$REFS"/*/; do
    [ -d "${repo}.git" ] || continue
    name=$(basename "$repo")
    update_repo "${repo%/}" "pool" "[pool] $name"
    POOL_COUNT=$((POOL_COUNT + 1))
  done
  [ "$POOL_COUNT" -eq 0 ] && echo "  (pool is empty)"

  # 2) Extra list (in-place)
  if [ -f "$EXTRA_LIST" ]; then
    while IFS= read -r line || [ -n "$line" ]; do
      line="${line%%#*}"                              # strip comments
      line="${line#"${line%%[![:space:]]*}"}"         # ltrim
      line="${line%"${line##*[![:space:]]}"}"         # rtrim
      [ -z "$line" ] && continue
      expanded="${line/#\~/$HOME}"                    # expand leading ~
      update_repo "$expanded" "extra" "[extra] $line"
    done < "$EXTRA_LIST"
  fi

  echo
} >> "$LOG" 2>&1
