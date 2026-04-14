# Scripts

## claude_paste_daemon.sh

Автоматически вставляет Claude OAuth токен при `/login`.

**Проблема:** В iTerm2 Cmd+V не работает в поле `Paste code here if prompted >` — 
токен содержит `#`, который обрезает вставку.

**Решение:** Демон следит за буфером обмена. Как только там появляется строка вида 
`TOKEN#TOKEN` (80+ символов с `#`), он находит iTerm2-окно с login-промптом и 
вставляет автоматически.

**Установка:**
```bash
bash ~/personal/scripts/claude_paste_daemon.sh &
```
Автозапуск уже добавлен в `~/.zshrc`.

**Зависимости:** iTerm2, macOS AppleScript
