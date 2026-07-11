#!/bin/bash
# Полный суточный бэкап данных+конфигов сервера n (borg, retention 14 дней).
# Второй слой к логическим дампам БД (backup-databases.sh 04:00 MSK).
# Запуск: cron 05:00 MSK. nice/ionice чтобы не мешать проду.
set -o pipefail
export BORG_REPO=/root/backups/borg
export BORG_UNKNOWN_UNENCRYPTED_REPO_ACCESS_IS_OK=yes
LOG=/var/log/server-backup.log
HOST=$(hostname)
TS=$(date +%Y-%m-%d_%H%M)
NICE="nice -n 19 ionice -c3"

exec 9>/var/lock/server-backup.lock
flock -n 9 || { echo "$(date '+%F %T') предыдущий бэкап ещё идёт, скип" >> "$LOG"; exit 0; }
log(){ echo "[$(date '+%F %T')] $1" >> "$LOG"; }

log "=== START ${HOST}-${TS} ==="

$NICE borg create \
  --stats --compression zstd,6 \
  --exclude '/root/backups/borg' \
  --exclude '/var/lib/docker/volumes/kad-cache' \
  --exclude '/var/lib/docker/volumes/kad-manticore' \
  --exclude '/var/lib/docker/volumes/kad-logs' \
  --exclude '/var/lib/docker/volumes/*_logs' \
  --exclude '/var/lib/docker/volumes/*caddy*' \
  --exclude '/opt/brave.com' \
  --exclude '/opt/google' \
  --exclude '/opt/prometheus' \
  --exclude '*/node_modules' \
  --exclude '*/.cache' \
  --exclude '*.log' \
  "::${HOST}-${TS}" \
  /var/lib/docker/volumes \
  /root \
  /etc \
  /opt \
  /home \
  /var/www \
  /usr/local \
  >> "$LOG" 2>&1
RC=$?
log "borg create rc=$RC"

# Ротация: 14 суточных + 8 недельных точек (borg = дедуп, каждый архив самодостаточен)
$NICE borg prune --list --keep-daily=14 --keep-weekly=8 --glob-archives "${HOST}-*" >> "$LOG" 2>&1
log "borg prune rc=$?"

$NICE borg compact >> "$LOG" 2>&1
log "borg compact rc=$?"

du -sh "$BORG_REPO" 2>/dev/null | awk -v d="$(date '+%F %T')" '{print "["d"] repo size: "$1}' >> "$LOG"
log "=== DONE rc=$RC ==="
exit $RC
