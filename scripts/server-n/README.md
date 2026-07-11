# Бэкап сервера n

Суточный бэкап данных+конфигов сервера **n** (Contabo, 8 ядер / 30GB / SSD 1.2T). Настроен 2026-07-11.

## Схема — 2 слоя

| Слой | Скрипт | Cron | Что делает |
|------|--------|------|------------|
| Логические дампы БД | `backup-databases.sh` *(на сервере)* | 04:00 | mysqldump/pg_dump критичных БД, ротация 7 дней → `/root/backups/db/$DATE` (исключает ReestrBD 34G) |
| **Файловый borg-снимок** | **`server-backup.sh`** | 05:00 | Дедуплицированный снимок всех данных, retention 14 суточных + 8 недельных |

## borg-репозиторий

- Путь: `/root/backups/borg` (локально на sda3)
- Шифрование: `none` (локальный DR; нужен `BORG_UNKNOWN_UNENCRYPTED_REPO_ACCESS_IS_OK=yes`)
- Сжатие: `zstd,6`, приоритет `nice -n19 ionice -c3`, защита от наложений — `flock`

**⚠️ borg = дедупликация, НЕ full/incremental.** Каждый `borg create` хранит только изменённые блоки (инкремент по месту), но остаётся **самодостаточным полным снимком** — любой день извлекается целиком, ни от чего не завися. Отдельная «недельная полная копия» не нужна: все архивы и так полные. Недельная глубина задаётся через `--keep-weekly`, а не отдельным прогоном.

## Что в бэкапе

**Включено:** все docker volumes + `/root` (со свежими дампами БД) + `/etc`
`/application` = симлинк на volume `kad-app` (не дублируется).

**Исключено (derived/кеш, восстановимо):** `kad-cache` (18G), `kad-manticore` (17G, реиндексируется из БД), `kad-logs`, `*_logs`, `*caddy*`, `node_modules`, `*.log`, сам borg-репозиторий.

`kad-db` (38G, включая ReestrBD 34G Росреестра) берётся **файлово целиком** — полный откат «как есть».

## Восстановление

```bash
export BORG_UNKNOWN_UNENCRYPTED_REPO_ACCESS_IS_OK=yes
borg list /root/backups/borg                      # какие точки есть
borg extract /root/backups/borg::<архив> path/...  # вытащить нужный путь
# затем вернуть volume/файл на место → restart контейнера
```

БД надёжнее восстанавливать из логического дампа (`/root/backups/db/`), чем из файлового снимка живой InnoDB (crash-recovery).

## Показатели первого прогона (2026-07-11)

- Реальных данных: 73.6 GB → сжато 22.9 GB → **на диске (дедуп) 19.9 GB**
- Длительность: ~34 мин под ionice idle

## Мониторинг

```bash
ssh n 'tail /var/log/server-backup.log'
ssh n 'BORG_UNKNOWN_UNENCRYPTED_REPO_ACCESS_IS_OK=yes borg info /root/backups/borg'
```
