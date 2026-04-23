# Backup сервера n → Mail.ru Cloud

## Статус: настроен 2026-04-23, первый прогон запущен

## Архитектура бекапов

```
kad (5.42.109.72)  ──rsync──►  n (167.86.116.15)  ──rclone WebDAV──►  Mail.ru Cloud
                                     /backups/kad/                    mailru:Backups/server-n/
```

---

## kad → n (уже работало, верифицировано 2026-04-23)

**Скрипты на kad:**

| Скрипт | Cron | Назначение |
|---|---|---|
| `/root/backup_to_n.sh` | `30 4 * * *` (UTC) | app + www + configs → tar.gz → rsync |
| `/root/db_backup_full.sh` | `0 2 * * 0` (воскресенье) | Full dump всех DB, rosreestr 4 чанка по 50M rows |
| `/root/db_backup_incremental.sh` | `0 2 * * 1-6` (пн–сб) | Incremental: активные таблицы (admin_*, ReestrBD active) |

**Структура на n:**
```
/backups/kad/
  YYYY-MM-DD/          ← файловые бекапы (7 дней rolling)
    app_DATE.tar.gz      5.5 GB
    www_DATE.tar.gz      4.8 GB
    configs_DATE.tar.gz  340 KB
  db/
    full/YYYY-MM-DD/   ← полные DB (4 воскресенья)
      full_ReestrBD_notrosreestr_DATE.sql.gz   875 MB
      full_rosreestr_chunk1..4_DATE.sql.gz     ~7.4 GB total
      full_admin_*.sql.gz
    incremental/YYYY-MM-DD/  ← ежедн. (7 дней rolling)
      inc_admin_*.sql.gz
      inc_ReestrBD_active_DATE.sql.gz
```

**Integrity check 2026-04-23:**
- Файлы (22 апр): ✅ app 5.5G / www 4.8G / configs 340K — все OK
- DB full (19 апр): ✅ 8/8 файлов, 8.1 GB — все OK
- DB incremental (сегодня): ✅ 4/4 файлов — все OK

---

## n → Mail.ru Cloud (настроено 2026-04-23)

**Скрипт:** `/root/scripts/backup_mailru.sh`  
**Cron:** `0 3 * * *` (03:00 UTC ежедневно)  
**Remote:** `mailru:Backups/server-n/`  
**Retention:** 30 дней (daily snapshots)  
**Auth:** rclone WebDAV, конфиг `~/.config/rclone/rclone.conf`

**Что синхронизируется:**

| Источник | Dest в облаке | Исключения |
|---|---|---|
| `/opt/n/apps/get-my-agent-admin` | `get-my-agent-admin/` | `node_modules/`, `dist/`, `.next/` |
| `/home/public_html/get-my-agent.com` | `wordpress/` | `wp-content/cache/`, большие uploads |
| `/root/bot-dashboard` | `bot-dashboard/` | `node_modules/`, `dist/` |
| `/root/yandex_bot` | `yandex_bot/` | `work/` (22GB), `venv/`, `logs/`, `outputs/` |
| `/root/scripts` | `scripts/` | — |
| DB дампы (at runtime) | `daily/DATE/db-dumps/` | PostgreSQL all + MySQL testbrainskill |

**Инкрементальность:** `--backup-dir mailru:Backups/server-n/daily/DATE/` — изменённые/удалённые файлы уходят в дейли-снапшот, `current/` всегда актуален.

**Первый прогон:** запущен 2026-04-23 06:46 UTC в screen (`backup_mailru`), статус — идёт.

---

## Полная матрица coverage

| Данные | kad→n | n→Mail.ru | Retention |
|---|---|---|---|
| Код `/application/` | ✅ daily | ✅ — | 7 дней на n |
| БД rosreestr (150M rows) | ✅ weekly full | ❌ >500MB лимит | 4 недели на n |
| БД активные таблицы | ✅ daily | ✅ дамп | 7 дней на n / 30 дней в cloud |
| get-my-agent код | — | ✅ daily | 30 дней |
| WordPress | — | ✅ daily | 30 дней |
| yandex_bot код+конфиг | — | ✅ daily | 30 дней |

**Важно:** rosreestr (8+ GB) не идёт в Mail.ru из-за `--max-size 500M` и WebDAV timeout. Хранится только на n (4 недели).
