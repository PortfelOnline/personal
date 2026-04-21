# Mail.ru Cloud Backup — прогресс

## Статус: активен, ежедневно 11:00

## Конфигурация

- **Скрипт**: `~/scripts/backup_mailru.sh`
- **LaunchAgent**: `~/Library/LaunchAgents/com.user.backup-mailru.plist`
- **Логи**: `~/.backup_mailru_logs/YYYY-MM-DD.log`
- **Remote**: `mailru:Backups/current` (инкрементальный через `--backup-dir`)
- **Retention**: 30 дней (`mailru:Backups/daily/YYYY-MM-DD/`)
- **Расписание**: каждый день в 11:00 (launchd, запускается при пробуждении если Mac спал)

## Что делает

1. Проверяет сеть (ping cloud.mail.ru)
2. Пропускает если Mac простаивал > 4 часов
3. Удаляет снапшоты старше 30 дней
4. `rclone sync` → `mailru:Backups/current`, изменённые файлы уходят в `daily/YYYY-MM-DD/`
5. **Проверка целостности**: `rclone check` сравнивает хэши source vs облако, результат в лог

## Исключения

`Library/`, `Parallels/`, `node_modules/`, `.git/objects/`, `.worktrees/`,
`build/intermediates/`, `build/tmp/`, `*.vmdk`, `*.iso`, кэши браузеров и инструментов

## Исправления (2026-04-22)

- Убран `set -e` → exit code 1 от rclone (пропущенные файлы) больше не роняет скрипт
- Добавлены исключения `.worktrees/` и Android build (причина 102 ошибок в прошлом прогоне)
- Добавлена integrity check после sync
- Retention: 7 дней → 30 дней

## Последние прогоны

| Дата | Результат |
|------|-----------|
| 2026-04-20 | 18h14m, 102 ошибки (Android tmp), завершён |
| 2026-04-22 | Перезапущен с новыми исключениями. Идёт: 6% (715MB/12.2 GiB), ~3h22m ETA, ~1MB/s. caffeinate держит Mac от сна. |

## Улучшения (2026-04-22)

- Добавлено исключение `.remember/logs/**` — тысячи мелких файлов, не нужны в бекапе
- Добавлена проверка WiFi: бекап пропускается если активный интерфейс ≠ `en0` (WiFi)
- Исключены ~20 GiB регенерируемых папок: `.ollama`, `.gemini`, `.vscode`, `actions-runner x2`, `.npm-global`, `.websiteauditor`, `.serena`, `.codex`, `jdk17`, `android-sdk-tmp`, `mac_runner_watchdog_logs`
- `caffeinate -i -w <pid>` — Mac не засыпает во время прогона, после завершения отпускает автоматически
