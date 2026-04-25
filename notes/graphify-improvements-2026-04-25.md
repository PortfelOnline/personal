# Graphify Improvements — 2026-04-25 (сессия 2)

## Итог: 15 проектов, полная автоматизация

### Все графы

| Проект | Узлы | Рёбра | Путь |
|--------|------|-------|------|
| personal | 67 | 81 | `~/personal/graphify-out/` |
| aitrading | 42 | 88 | `~/dev/aitrading/graphify-out/` |
| github-connect-hub | 96 | 37 | `~/kadmap/_repos/github-connect-hub/graphify-out/` |
| aiwaiter | 248 | 263 | `~/dev/aiwaiter/graphify-out/` |
| localai | 103 | 150 | `~/localai/localai/graphify-out/` |
| n8n_1 | 715 | 1670 | `~/n8n_1/n8n_1/graphify-out/` |
| **kadmap** | **1754** | **3332** | `~/kadmap/graphify-out/` |
| kadmap/scripts | 67 | 45 | `~/kadmap/scripts/graphify-out/` |
| strategy/server | 385 | 670 | `~/strategy-dashboard/server/graphify-out/` |
| strategy/scripts | 215 | 149 | `~/strategy-dashboard/scripts/graphify-out/` |
| strategy/client | 354 | 293 | `~/strategy-dashboard/client/graphify-out/` |
| **strategy/merged** | **954** | **1112** | `~/strategy-dashboard/graphify-out/merged-graph.json` |
| **audioceh** | **1477** | **2450** | `~/audioceh/graphify-out/` |
| yoga | 4 | 3 | `~/dev/yoga/graphify-out/` |
| oficiant-pro | 6 | 8 | `~/dev/oficiant-pro/graphify-out/` |

### Что сделано в этой сессии

**1. Git hooks (post-commit)**
- 11/11 git roots — граф пересобирается после каждого `git commit`
- audioceh: кастомный hook с субдиректорийным pipeline
- Установлено через `graphify hook install`

**2. kadmap главный проект**
- Графифицированы: `reestr/` (283 файла) + `src/` + `scripts/` + root PHP
- Исключён WordPress (wp-* директории)
- God nodes: `Utility` (117 рёбер), `RosreestrBase` (82), `DB` (73), `OrderProcessing` (63)
- Кастомный pipeline в cron и в post-commit hook

**3. strategy-dashboard merged graph**
- `graphify merge-graphs` объединил server+scripts+client
- 954N / 1112E — видны cross-boundary связи
- Файл: `~/strategy-dashboard/graphify-out/merged-graph.json`

**4. save-result feedback loop**
- `gfy-save()` добавлен в `~/.zshrc`
- Memory засеяна: audioceh (mass edit), strategy-dashboard (rewriteArticle)
- При повторных запросах граф учитывает прошлые ответы

**5. yoga + oficiant-pro**
- Клонированы из GitHub (приватные репо PortfelOnline)
- yoga: 2 markdown файла (Nha Trang yoga studio)
- oficiant-pro: Figma plugin (code.js + manifest.json)
- Оба: claude hook + git hook + gitignore + cron

**6. update-refs.sh → update-graphify.sh**
- Был разрыв: скрипты не были связаны
- Исправлено: `update-refs.sh` теперь вызывает `update-graphify.sh` в секции 4

**7. Улучшения из сессии 1 (доделаны)**
- `graphify install` — skill обновлён до v0.5.0, warning пропал
- audioceh: 100 именованных community labels (Agoo Blog CMS, Product Mass Edit, Megamenu...)
- 14/14 проектов с PreToolUse hook (query-before-read)
- 13/13 проектов с .gitignore для graph.json/graph.html

### Архитектура автоматизации

```
git commit
  └─→ .git/hooks/post-commit
        └─→ graphify update . (AST rebuild, без LLM)

каждый понедельник 09:00 (launchd: com.local.refs.update)
  └─→ update-refs.sh
        ├─→ git pull (pool + extra.list repos)
        ├─→ pip install --upgrade graphifyy
        └─→ update-graphify.sh
              ├─→ graphify update . (стандартные проекты)
              ├─→ audioceh: кастомный Python pipeline (4 субдиректории)
              └─→ kadmap: кастомный Python pipeline (reestr/ без WordPress)

gclone() — новый проект клонируется с автоматическим graphify . в фоне
gfy()    — алиас для graphify в текущей директории
gfy-save() — сохранить результат в graphify-out/memory/
```

### Команды для работы

```bash
# Запрос к графу (вместо чтения файлов)
cd ~/audioceh && graphify query "mass edit"
cd ~/kadmap    && graphify query "как работает кеш"
cd ~/strategy-dashboard && graphify query "flux images" --graph graphify-out/merged-graph.json

# Путь между концепциями
cd ~/kadmap && graphify path "RosreestrBase" "OrderController"

# Объяснение узла
cd ~/audioceh && graphify explain "ControllerEditorsProductEdit"

# Сохранить полезный ответ в memory
gfy-save "вопрос" "ответ" NodeA NodeB

# Обновить граф вручную
cd ~/kadmap && graphify update .
```
