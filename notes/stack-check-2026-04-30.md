# Проверка стека Claude Code — 2026-04-30

## Сделано
1. Полная диагностика стека Claude Code parity
2. Сравнение отключённых плагинов с текущим стеком
3. Включён `security-guidance@claude-plugins-official`

## Результат диагностики

| Слой | Статус |
|------|--------|
| Git интеграция | ✅ GitHub MCP + PR review + авто-пуш |
| MCP серверы | ✅ Github, Playwright, Chrome, GoodMem, Graphify, Context7 |
| Плагины | 53/66 включены |
| Хуки | 15 шт — все точки входа покрыты |
| LSP | TypeScript, Python, PHP, Kotlin, ClangD |
| SEO | 14 скиллов |
| Session persistence | compact hooks + save/restore |
| DeepSeek | CLI есть, v4-flash |

## Отключённые плагины
| Плагин | Дублирует? | Решение |
|--------|-----------|---------|
| hookify | ✅ да (15 хуков) | отключён ✅ |
| security-guidance | ❌ нет | включён ✅ |
| episodic-memory | ⚠️ 80% (goodmem) | отключён ✅ |
| double-shot-latte | ❌ нет (auto-continue) | оставлен, дорогой |

## Правило для Claude
- **personal** = `~/personal` (PortfelOnline/personal)
- **kadmap** = `~/kadmap` (PortfelOnline/kadmap)
- Не путать репозитории!
