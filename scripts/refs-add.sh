#!/bin/bash
# refs-add — add a reference repo to the auto-update pool.
#
# Usage:
#   refs-add <git-url>         → clones into ~/.claude/refs/ (pool, hard-reset updates)
#   refs-add <local-path>      → appends to ~/.claude/refs/extra.list (in-place, safety-guarded)
#   refs-add --list            → show current state
#   refs-add --run             → trigger update now
#   refs-add --remove <name>   → remove from pool (rm -rf) or extra.list (comment out)
#   refs-add --help            → this message

set -euo pipefail

REFS="$HOME/.claude/refs"
EXTRA_LIST="$REFS/extra.list"
SCRIPT_DIR="$HOME/.claude/scripts"

die() { echo "ERROR: $*" >&2; exit 1; }

cmd_help() {
  sed -n '3,10p' "$0" | sed 's/^# \{0,1\}//'
}

is_git_url() {
  case "$1" in
    http://*|https://*|git@*|ssh://*|git://*) return 0 ;;
    *.git) return 0 ;;
    *) return 1 ;;
  esac
}

cmd_list() {
  echo "Pool (~/.claude/refs/):"
  local found=0
  for d in "$REFS"/*/; do
    [ -d "${d}.git" ] || continue
    found=1
    name=$(basename "$d")
    cd "$d"
    head=$(git rev-parse --short HEAD 2>/dev/null || echo "?")
    remote=$(git config --get remote.origin.url 2>/dev/null || echo "?")
    size=$(du -sh . 2>/dev/null | awk '{print $1}')
    printf "  %-30s %s  %s  %s\n" "$name" "$head" "$size" "$remote"
  done
  [ "$found" -eq 0 ] && echo "  (empty)"

  echo
  echo "Extra (~/.claude/refs/extra.list):"
  if [ -f "$EXTRA_LIST" ]; then
    grep -v '^\s*#' "$EXTRA_LIST" | grep -v '^\s*$' | while read -r line; do
      expanded="${line/#\~/$HOME}"
      if [ -d "$expanded/.git" ]; then
        cd "$expanded"
        head=$(git rev-parse --short HEAD 2>/dev/null || echo "?")
        remote=$(git config --get remote.origin.url 2>/dev/null || echo "?")
        printf "  %-40s %s  %s\n" "$line" "$head" "$remote"
      else
        printf "  %-40s MISSING (no .git)\n" "$line"
      fi
    done
  fi

  echo
  if [ -x "$SCRIPT_DIR/update-refs.sh" ]; then
    echo "Updater: $SCRIPT_DIR/update-refs.sh"
  fi
  if launchctl list 2>/dev/null | grep -q "com.local.refs.update"; then
    echo "Schedule: com.local.refs.update (launchd) — Mon 09:00"
  else
    echo "Schedule: NOT LOADED (run launchctl load ~/Library/LaunchAgents/com.local.refs.update.plist)"
  fi
}

cmd_run() {
  [ -x "$SCRIPT_DIR/update-refs.sh" ] || die "$SCRIPT_DIR/update-refs.sh not found"
  "$SCRIPT_DIR/update-refs.sh"
  tail -n 20 "$HOME/.claude/logs/refs.log"
}

cmd_add_url() {
  local url="$1"
  mkdir -p "$REFS"

  local name
  name=$(basename "$url" .git)
  local target="$REFS/$name"

  [ -e "$target" ] && die "pool entry already exists: $target"

  echo "Cloning $url → $target ..."
  git clone --depth 1 "$url" "$target"

  local size
  size=$(du -sh "$target" | awk '{print $1}')
  echo "OK: $name added to pool ($size). It will be updated weekly (Mon 09:00) via launchd."
  echo "Trigger update now: refs-add --run"
}

cmd_add_path() {
  local path="$1"
  local abspath

  if [ "${path:0:1}" = "~" ]; then
    abspath="${path/#\~/$HOME}"
  elif [ "${path:0:1}" = "/" ]; then
    abspath="$path"
  else
    abspath="$(cd "$(dirname "$path")" 2>/dev/null && pwd)/$(basename "$path")" || \
      die "cannot resolve: $path"
  fi

  [ -d "$abspath" ] || die "not a directory: $abspath"
  [ -d "$abspath/.git" ] || die "not a git repo: $abspath (no .git)"

  mkdir -p "$REFS"
  touch "$EXTRA_LIST"

  # Write canonical form: replace $HOME with ~ for portability
  local canonical="${abspath/#$HOME/\~}"

  # Dedup
  if grep -Fxq "$canonical" "$EXTRA_LIST" 2>/dev/null; then
    echo "Already in extra.list: $canonical"
    return
  fi

  echo "$canonical" >> "$EXTRA_LIST"
  echo "OK: $canonical added to extra.list (in-place update, skipped if dirty/ahead)."
  echo "Trigger update now: refs-add --run"
}

cmd_remove() {
  local target="$1"
  [ -z "$target" ] && die "--remove needs a name or path"

  # Try pool first
  if [ -d "$REFS/$target/.git" ]; then
    read -r -p "Delete pool entry $REFS/$target ? [y/N] " yn
    [ "$yn" = "y" ] || [ "$yn" = "Y" ] || { echo "aborted"; return; }
    rm -rf "${REFS:?}/$target"
    echo "Removed: $REFS/$target"
    return
  fi

  # Try extra.list (match canonical form)
  if [ -f "$EXTRA_LIST" ]; then
    local canonical="${target/#$HOME/\~}"
    if grep -Fxq "$canonical" "$EXTRA_LIST"; then
      # Comment out instead of delete — preserve history in file
      sed -i.bak "s|^$(printf '%s' "$canonical" | sed 's/[]\/$*.^[]/\\&/g')\$|# removed $(date +%Y-%m-%d): &|" "$EXTRA_LIST"
      rm -f "$EXTRA_LIST.bak"
      echo "Commented out in extra.list: $canonical"
      return
    fi
  fi

  die "not found: $target"
}

# --- dispatch ---
case "${1:-}" in
  ""|--help|-h) cmd_help ;;
  --list|-l) cmd_list ;;
  --run|-r) cmd_run ;;
  --remove) cmd_remove "${2:-}" ;;
  *)
    if is_git_url "$1"; then
      cmd_add_url "$1"
    else
      cmd_add_path "$1"
    fi
    ;;
esac
