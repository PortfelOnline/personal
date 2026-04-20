# Reference repos auto-update setup

**Date:** 2026-04-20
**Machine:** darwin (macOS)

Unified mechanism for auto-updating read-only reference repos (design systems, awesome-lists, tool sources) — one weekly launchd agent handles everything.

## Architecture

```
~/.claude/
├── refs/                          # Reference repos pool
│   ├── awesome-design-md/         # VoltAgent/awesome-design-md (59 DESIGN.md)
│   ├── awesome-claude-code/       # hesreallyhim/awesome-claude-code
│   └── extra.list                 # In-place paths (active repos)
├── scripts/
│   └── update-refs.sh             # The updater (bash)
└── logs/
    └── refs.log                   # Run history

~/Library/LaunchAgents/
└── com.local.refs.update.plist    # Schedules weekly run (Mon 09:00)
```

## Two source modes

### 1. Managed pool — `~/.claude/refs/*/`

Any subdir with `.git` is auto-discovered. Updater does `git fetch + reset --hard origin/<default-branch>`. **Do not commit inside** — work will be destroyed.

Add new repo:
```bash
cd ~/.claude/refs && git clone <url>
```

### 2. Extra paths — `~/.claude/refs/extra.list`

One path per line (`~` is expanded). Repos stay in-place (not moved).
**Safety guard:** if repo is dirty OR has local commits ahead of upstream, skipped with a notice. Protects active projects.

Current contents:
```
~/.agents/superpowers_repo
~/serena
```

Add new path:
```bash
echo '~/path/to/repo' >> ~/.claude/refs/extra.list
```

## The updater script

`~/.claude/scripts/update-refs.sh`:

```bash
#!/bin/bash
export PATH="/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin"
# Generic updater for reference repos.
# Installed as LaunchAgent com.local.refs.update.
#
# Sources:
#   1) Any subdir of ~/.claude/refs/ that contains a .git (managed pool)
#   2) Paths listed in ~/.claude/refs/extra.list (in-place, SAFETY-GUARDED)

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

  POOL_COUNT=0
  for repo in "$REFS"/*/; do
    [ -d "${repo}.git" ] || continue
    name=$(basename "$repo")
    update_repo "${repo%/}" "pool" "[pool] $name"
    POOL_COUNT=$((POOL_COUNT + 1))
  done
  [ "$POOL_COUNT" -eq 0 ] && echo "  (pool is empty)"

  if [ -f "$EXTRA_LIST" ]; then
    while IFS= read -r line || [ -n "$line" ]; do
      line="${line%%#*}"
      line="${line#"${line%%[![:space:]]*}"}"
      line="${line%"${line##*[![:space:]]}"}"
      [ -z "$line" ] && continue
      expanded="${line/#\~/$HOME}"
      update_repo "$expanded" "extra" "[extra] $line"
    done < "$EXTRA_LIST"
  fi

  echo
} >> "$LOG" 2>&1
```

## LaunchAgent

`~/Library/LaunchAgents/com.local.refs.update.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTD/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.local.refs.update</string>
    <key>ProgramArguments</key>
    <array>
        <string>/Users/evgenijgrudev/.claude/scripts/update-refs.sh</string>
    </array>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Weekday</key><integer>1</integer>
        <key>Hour</key><integer>9</integer>
        <key>Minute</key><integer>0</integer>
    </dict>
    <key>RunAtLoad</key><false/>
    <key>StandardOutPath</key>
    <string>/Users/evgenijgrudev/.claude/logs/refs.stdout.log</string>
    <key>StandardErrorPath</key>
    <string>/Users/evgenijgrudev/.claude/logs/refs.stderr.log</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
    </dict>
</dict>
</plist>
```

Load: `launchctl load ~/Library/LaunchAgents/com.local.refs.update.plist`

## Key design decisions

- **`bash` not `zsh`** — zsh has a function-scope quirk where `local a="$1" b="$2" c="$3"` in a single line breaks PATH inheritance inside functions. Bash is predictable here.
- **Safety guard only for extra** — pool entries are assumed read-only (no user commits), so hard-reset without check. Extra paths may be active work, so skip if dirty/ahead.
- **Two sources, one script** — pool for fully read-only refs you want updated aggressively; extra for in-place updates of tool sources that you don't commit to but don't want moved.
- **No symlinks across home** — moving `~/superpowers` into `refs/` would break `~/.agents/skills/superpowers` symlink chain. `extra.list` pattern solves this without touching real paths.

## Helper CLI: `refs-add`

Symlinked from `~/.local/bin/refs-add` → `~/.claude/scripts/refs-add.sh`. Does auto-detection of URL vs path.

```bash
refs-add https://github.com/foo/bar.git    # → pool (clone into refs/)
refs-add ~/some/existing/repo               # → extra.list (in-place)
refs-add --list                             # dashboard: HEAD, size, remote, schedule
refs-add --run                              # trigger update now
refs-add --remove awesome-design-md         # remove (pool: rm -rf; extra: comment out)
refs-add --help
```

Sample `--list` output:
```
Pool (~/.claude/refs/):
  awesome-claude-code            84c0750  31M   https://github.com/hesreallyhim/awesome-claude-code.git
  awesome-design-md              6dc4def  428K  https://github.com/VoltAgent/awesome-design-md.git

Extra (~/.claude/refs/extra.list):
  ~/.agents/superpowers_repo    b557648   https://github.com/obra/superpowers.git
  ~/serena                      84891b59  https://github.com/oraios/serena

Updater: /Users/<user>/.claude/scripts/update-refs.sh
Schedule: com.local.refs.update (launchd) — Mon 09:00
```

## Low-level commands

```bash
# Manual run (bypass helper)
~/.claude/scripts/update-refs.sh && tail ~/.claude/logs/refs.log

# Check launchd status
launchctl list | grep refs.update

# Disable
launchctl unload ~/Library/LaunchAgents/com.local.refs.update.plist

# Re-enable
launchctl load ~/Library/LaunchAgents/com.local.refs.update.plist
```

## Restoring on a new machine

This repo stashes all three artifacts under `scripts/`:
- `scripts/update-refs.sh`
- `scripts/refs-add.sh`
- `scripts/com.local.refs.update.plist`

Bootstrap:
```bash
mkdir -p ~/.claude/scripts ~/.claude/refs ~/.claude/logs ~/.local/bin
cp scripts/update-refs.sh scripts/refs-add.sh ~/.claude/scripts/
chmod +x ~/.claude/scripts/{update-refs.sh,refs-add.sh}
ln -sf ~/.claude/scripts/refs-add.sh ~/.local/bin/refs-add

# Edit the plist to use your username, then:
cp scripts/com.local.refs.update.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.local.refs.update.plist
```

## Notes from this session

- Found duplicate `~/superpowers` (3.7M) vs `~/.agents/superpowers_repo` (6.3M). Plugin system uses `~/.claude/plugins/cache/...` (official), but `~/.agents/skills/superpowers` symlinks to `~/.agents/superpowers_repo/skills`. So `~/.agents/superpowers_repo` is actively wired; `~/superpowers` was an orphan manual clone. Deleted the orphan.
- `localai` and `bin/ccflare` skipped — localai is my fork (active), ccflare is stale and huge (252M).
