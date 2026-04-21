#!/bin/bash
# Ежедневный инкрементный бекап на Mail.ru Cloud
# nice 19 (lowest CPU priority), только когда Mac активен
# Rolling retention: 30 дней

set -uo pipefail

RCLONE="/usr/local/bin/rclone"
REMOTE="mailru:Backups"
SOURCE="$HOME"
LOG_DIR="$HOME/.backup_mailru_logs"
LOG_FILE="$LOG_DIR/$(date +%Y-%m-%d).log"
TODAY=$(date +%Y-%m-%d)
RETENTION_DAYS=30

mkdir -p "$LOG_DIR"
echo "=== Backup started: $(date) ===" >> "$LOG_FILE"

# Проверяем сеть
if ! ping -c 1 -t 5 cloud.mail.ru &>/dev/null; then
    echo "Network unavailable, skipping." >> "$LOG_FILE"
    exit 0
fi

# Только WiFi — не заливать через мобильный интернет
ACTIVE_IFACE=$(route get default 2>/dev/null | awk '/interface:/ {print $2}')
WIFI_IFACE=$(networksetup -listallhardwareports 2>/dev/null | awk '/Wi-Fi/{getline; print $2}')
if [ "$ACTIVE_IFACE" != "$WIFI_IFACE" ]; then
    echo "Not on WiFi (active: $ACTIVE_IFACE, wifi: $WIFI_IFACE) — skipping." >> "$LOG_FILE"
    exit 0
fi

# Пропускаем если Mac простаивает > 4 часа (спит/заблокирован)
IDLE_MS=$(/usr/sbin/ioreg -c IOHIDSystem | awk '/HIDIdleTime/ {print int($NF/1000000); exit}' || true)
IDLE_HOURS=$((IDLE_MS / 3600000))
if [ "$IDLE_HOURS" -ge 4 ]; then
    echo "System idle ${IDLE_HOURS}h — skipping." >> "$LOG_FILE"
    exit 0
fi

# Удаляем бекапы старше 7 дней
CUTOFF=$(date -v-${RETENTION_DAYS}d +%Y-%m-%d)
echo "Cutoff: $CUTOFF — cleaning old backups..." >> "$LOG_FILE"
while IFS= read -r dir; do
    dir="${dir%/}"
    if [[ "$dir" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]] && [[ "$dir" < "$CUTOFF" ]]; then
        echo "  Purging: $dir" >> "$LOG_FILE"
        "$RCLONE" purge "$REMOTE/daily/$dir" --log-file="$LOG_FILE" 2>&1 || true
    fi
done < <("$RCLONE" lsf "$REMOTE/daily/" --dirs-only 2>/dev/null)

# Инкрементный sync в current/, изменившиеся/удалённые файлы → daily/YYYY-MM-DD/
echo "Syncing to $REMOTE/current  (backup-dir → daily/$TODAY)..." >> "$LOG_FILE"

nice -n 19 "$RCLONE" sync "$SOURCE" "$REMOTE/current" \
    --backup-dir "$REMOTE/daily/$TODAY" \
    --transfers 4 \
    --checkers 8 \
    --bwlimit "10M" \
    --max-size 1900M \
    --exclude "Library/**" \
    --exclude "Parallels/**" \
    --exclude "Applications/**" \
    --exclude ".Trash/**" \
    --exclude ".cache/**" \
    --exclude ".npm/**" \
    --exclude ".yarn/cache/**" \
    --exclude ".bun/**" \
    --exclude "**/node_modules/**" \
    --exclude "**/.git/objects/**" \
    --exclude "**/.worktrees/**" \
    --exclude "**/build/intermediates/**" \
    --exclude "**/build/tmp/**" \
    --exclude "*.vmdk" \
    --exclude "*.vdi" \
    --exclude "*.iso" \
    --exclude ".DS_Store" \
    --exclude "**/Code Cache/**" \
    --exclude "**/Cache/**" \
    --exclude "**/cache/**" \
    --exclude "**/*-browser-profile/**" \
    --exclude ".gemini/antigravity/browser_recordings/**" \
    --exclude ".antigravity/**" \
    --exclude ".playwright-mcp/**" \
    --exclude ".local/share/uv/**" \
    --exclude ".local/share/solana/**" \
    --exclude ".ScreamingFrogSEOSpider/**" \
    --exclude ".cpanm/**" \
    --exclude ".remember/logs/**" \
    --exclude ".gradle/caches/**" \
    --exclude ".gradle/wrapper/**" \
    --log-file="$LOG_FILE" \
    --log-level INFO \
    --stats 60s \
    --stats-log-level INFO || {
    EXIT_CODE=$?
    if [ $EXIT_CODE -eq 1 ]; then
        echo "=== Backup finished with minor errors (code 1 — some files skipped): $(date) ===" >> "$LOG_FILE"
        exit 0
    fi
    echo "=== Backup FAILED (code $EXIT_CODE): $(date) ===" >> "$LOG_FILE"
    exit $EXIT_CODE
}

echo "=== Backup finished: $(date) ===" >> "$LOG_FILE"

# Проверка целостности: сравниваем контрольные суммы source vs облако
echo "=== Integrity check started: $(date) ===" >> "$LOG_FILE"
CHECK_ERRORS=0
"$RCLONE" check "$SOURCE" "$REMOTE/current" \
    --exclude "Library/**" \
    --exclude "Parallels/**" \
    --exclude "Applications/**" \
    --exclude ".Trash/**" \
    --exclude ".cache/**" \
    --exclude ".npm/**" \
    --exclude ".yarn/cache/**" \
    --exclude ".bun/**" \
    --exclude "**/node_modules/**" \
    --exclude "**/.git/objects/**" \
    --exclude "**/.worktrees/**" \
    --exclude "**/build/intermediates/**" \
    --exclude "**/build/tmp/**" \
    --exclude "*.vmdk" \
    --exclude "*.vdi" \
    --exclude "*.iso" \
    --exclude ".DS_Store" \
    --exclude "**/Code Cache/**" \
    --exclude "**/Cache/**" \
    --exclude "**/cache/**" \
    --exclude "**/*-browser-profile/**" \
    --exclude ".gemini/antigravity/browser_recordings/**" \
    --exclude ".antigravity/**" \
    --exclude ".playwright-mcp/**" \
    --exclude ".local/share/uv/**" \
    --exclude ".local/share/solana/**" \
    --exclude ".ScreamingFrogSEOSpider/**" \
    --exclude ".cpanm/**" \
    --exclude ".remember/logs/**" \
    --exclude ".gradle/caches/**" \
    --exclude ".gradle/wrapper/**" \
    --max-size 1900M \
    --log-file="$LOG_FILE" \
    --log-level ERROR \
    2>&1 | tee -a "$LOG_FILE" || CHECK_ERRORS=$?

if [ "$CHECK_ERRORS" -eq 0 ]; then
    echo "=== Integrity check PASSED: $(date) ===" >> "$LOG_FILE"
else
    echo "=== Integrity check FAILED (code $CHECK_ERRORS): $(date) ===" >> "$LOG_FILE"
fi

# Оставляем только последние 30 лог-файлов
ls -t "$LOG_DIR"/*.log 2>/dev/null | tail -n +31 | xargs rm -f 2>/dev/null || true
