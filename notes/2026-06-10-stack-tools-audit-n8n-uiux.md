# Аудит 9 репо vs наш стек + установка n8n-mcp и ui-ux-pro-max

**Дата:** 2026-06-10

## Задача
Проверить 9 GitHub-репо — есть ли их функционал уже в нашем стеке Claude Code, добавить недостающее.

## Результат аудита

| # | Репо | Что делает | Статус в стеке |
|---|------|-----------|----------------|
| 1 | [thedotmack/claude-mem](https://github.com/thedotmack/claude-mem) | Персистентная память (SQLite + vector + хуки) | ✅ Дубль — `episodic-memory` plugin, `private-journal-mcp`, файловая `MEMORY.md`, `ruflo agentdb` |
| 2 | [nextlevelbuilder/ui-ux-pro-max-skill](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill) | Design-intelligence: БД 50+ UI-стилей, 97 палитр, 57 пар шрифтов, 99 UX-правил, 25 типов графиков | ⚠️→✅ **ДОБАВЛЕНО** (был только `frontend-design` + `awesome-design-md`) |
| 3 | [czlonkowski/n8n-mcp](https://github.com/czlonkowski/n8n-mcp) | MCP: 1851 нода n8n, 2352 шаблона, валидация, управление инстансом | ⚠️→✅ **ДОБАВЛЕНО** (были только n8n-skills, без MCP-сервера) |
| 4 | [kepano/obsidian-skills](https://github.com/kepano/obsidian-skills) | Skills для Obsidian (wikilinks, callouts, vault CLI) | ⚠️ Obsidian MCP (`uvx mcp-obsidian`) уже подключён; отдельные skills — не ставил |
| 5 | [HKUDS/LightRAG](https://github.com/HKUDS/LightRAG) | Lightweight RAG: knowledge graph + vector embeddings | ⚠️ Частично — `graphify` + `ruflo embeddings`. Полноценного RAG-фреймворка нет |
| 6 | [affaan-m/everything-claude-code](https://github.com/affaan-m/everything-claude-code) | Мега-харнесс: 64 агента, 261 skill, хуки | ⚠️ Пересекается — `superpowers`, `claude-seo`, `blog`, `code-review-expert`. Не ставил |
| 7 | [obra/superpowers](https://github.com/obra/superpowers) | Skill-фреймворк (brainstorm/TDD/debug/plans) | ✅ Установлено — plugin v5.0.7 + extra-path auto-update |
| 8 | [hesreallyhim/awesome-claude-code](https://github.com/hesreallyhim/awesome-claude-code) | Curated-список ресурсов CC | ✅ Установлено — refs pool (weekly pull) |
| 9 | [gsd-build/get-shit-done](https://github.com/gsd-build/get-shit-done) | Meta-prompting / spec-driven dev (архивирован → open-gsd) | ✅ Покрыто `superpowers` writing-plans + brainstorming + executing-plans |

## Что установлено

### #3 n8n-mcp (MCP-сервер, user scope)
```bash
claude mcp add n8n-mcp --scope user \
  -e MCP_MODE=stdio -e LOG_LEVEL=error -e DISABLE_CONSOLE_OUTPUT=true \
  -- npx -y n8n-mcp
```
- Режим: **documentation-only** (билд/валидация воркфлоу без живого инстанса)
- Статус: `claude mcp get n8n-mcp` → ✔ Connected
- Конфиг: `~/.claude.json`
- Полный режим (деплой в живой n8n): добавить `-e N8N_API_URL=... -e N8N_API_KEY=...`
- Первый запуск показывал «Failed to connect» — это таймаут на скачивание npx-пакета, после прогрева (`npx -y n8n-mcp --version`) поднялся.

### #2 ui-ux-pro-max (agent skill)
```bash
npm install -g uipro-cli
cd ~ && uipro init --ai claude --force   # ставит в .claude/skills/ текущей папки; из ~ это ~/.claude/skills/
```
- Нет флага `--global`; устанавливается в `.claude/` текущей директории. Запуск из `~` → `~/.claude/skills/ui-ux-pro-max/`
- Обновление: `uipro update`
- Активируется автоматически на UI/UX-запросах

## Не ставил (по решению)
- **#1, #6, #7, #8, #9** — функционал уже покрыт.
- **#4 obsidian-skills** — Obsidian MCP уже есть; отдельные skills не нужны.
- **#5 LightRAG** — только если понадобится production-RAG поверх `graphify`.
