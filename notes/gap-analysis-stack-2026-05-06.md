# Gap Analysis: DeepSeek Stack vs Claude Code Pro / Codex CLI / Cursor

**Дата:** 2026-05-06  
**Наш стек:** DS-proxy + claude CLI + DeepSeek API  
**Сравнение с:** Claude Code Pro, Codex CLI, Cursor IDE

---

## 1. Мы vs Claude Code Pro

### Что у Claude есть (а у нас нет через DS):

| Фича | Claude Code Pro | Наш стек (DS proxy) | Gap |
|------|----------------|-------------------|-----|
| **Prompt caching** | 90% cache hits → $0.30/M cached | 18% cache, каждый запрос полный контекст | ❌ **Критический** — платим в 10x больше |
| **Extended thinking** | Deep reasoning (опционально) | Stripped proxy — DS не поддерживает | ❌ Нет глубины |
| **Image/vision** | Нативная поддержка (Sonnet/Opus) | Через Groq Llama-4-Scout | ⚠️ Слабо |
| **MCP tools** | Полные MCP (Plugin, GitHub, Web) | Частично работает (через proxy) | ⚠️ Нестабильно |
| **Tool use quality** | Превосходно (делит на logits-шаги) | Посредст��енно (DS плохо понимает схемы) | ❌ **Критический** |
| **Plan mode** | Нативная поддержка | Нет — модель не знает режимов | ❌ Нет |
| **Code quality** | Высокая (Sonnet ~ codestral) | Средняя (flash слабее) | ⚠️ Заметно |
| **Context window** | 200K (Sonnet), 200K (Opus) | 128K (DeepSeek) | ⚠️ Меньше |
| **System prompt control** | Полный контроль | Прокси модифицирует | ⚠️ Ограничено |
| **Superpowers plugins** | Да | Да (через settings.json) | ✅ Работает |
| **WebSearch/WebFetch** | Нативные инструменты | Через MCP | ✅ Работает |
| **OAuth / подписка $20** | Все модели включены | $20 за DS API = ~6M токенов flash | ❌ $20 на DS = 1 день активной работы |

### Вывод: Claude Code Pro DE-FACTO дешевле DeepSeek при активном использовании благодаря кэшу

---

## 2. Мы vs Codex CLI (OpenAI)

### Что у Codex есть:

| Фича | Codex CLI | Наш стек | Gap |
|------|-----------|----------|-----|
| **Sandbox** | Нативная песочница для кода | Нет | ❌ |
| **Agentic loop** | Продвинутый (сам исправляет ошибки) | Базовый (через Claude Code) | ⚠️ |
| **Multi-file editing** | Нативно (понимает проекты) | Есть (через редактор) | ✅ |
| **Model choice** | GPT-4o, o3, o4-mini | DeepSeek flash/pro | ⚠️ |
| **Cost control** | Лимиты бюджета | Нет встроенного | ❌ |
| **Terminal integration** | Встроенный терминал | Внешний терминал | ⚠️ |
| **API pricing** | GPT-4o дороже | DeepSeek flash дешевле | ✅ DS дешевле за токен |

### Ключевой gap Codex: Sandbox + автоматическая обратная связь (запускает код, видит ошибки)

---

## 3. Мы vs Cursor IDE

### Что у Cursor есть:

| Фича | Cursor IDE | Наш стек | Gap |
|------|-----------|----------|-----|
| **IDE integration** | Полная VS Code интеграция | Терминал CLI | ❌ **Критический** — нет IDE |
| **Inline editing** | Tab to apply | Нет | ❌ |
| **Composer (multi-file)** | Превосходно | Ограниченно | ❌ |
| **Codebase indexing** | @codebase, сем. поиск | Нет | ❌ |
| **Agent mode** | Полный контекст проекта | Через CLAUDE.md | ⚠️ |
| **Quick fixes** | Ctrl+K, inline | Сохранить → применить | ⚠️ |
| **Context-aware** | @symbols, @files, @folders | @path в Read | ⚠️ |
| **Model choice** | Sonnet, GPT-4o, o3, etc | Только DS (через proxy) | ⚠️ |
| **Pricing** | $20/мес (Pro) | $20 DS API = 1 день | ✅ Выгоднее |

---

## 4. Что нашему стеку критически не хватает

### Priority 1: Кэширование контекста в ds-proxy ✅ FIXED 2026-05-06
**Fixed:** `_strip_cache_control` теперь СЖИМАЕТ блоки с cache_control вместо у��аления
- Системный промпт: 1,800→98 токенов (78% экономии)
- Tool results: keep first 300 + last 150 chars
- User/assistant: keep first 400-500 + last 200 chars
- **Ожидаемая экономия: 60-80% входных токенов на длинных сессиях**

### Priority 2: Модельный роутер ✅ FIXED 2026-05-06
**Fixed:** `session-start-model-router.sh` — анализирует первый запрос, выбирает модель
- Сложный (архитектура, миграции) → claude-opus-4-7
- Средний (баги, фичи) → claude-sonnet-4-20250514
- Простой (вопросы, git) → deepseek-v4-flash
- Черновики → claude-haiku-4-5-20251001
- **Алиасы:** cl-simple, cl-medium, cl-complex, cl-quick

### Priority 3: Sandbox / test loop ⚠️ Инфраструктура есть, Docker выключен
**Что есть:** Docker sandbox: `deepseek-agent/` (Dockerfile + docker-compose.yml)
- Запускает код в изолированном контейнере на порту 8766
- Автоматический feedback loop (запустить → прочитать ошибки → исправить)
- **Нужно:** запустить Docker (`docker compose up -d`)

### Priority 4: Codebase indexing
**Почему:**
- Cursor @codebase находит релевантный код
- У нас: только grep + CLAUDE.md ручное описание
- Нужен graphify интеграция с авто-контекстом

---

## 5. Реальная стоимость владения (TCO)

| Сценарий | DeepSeek | Claude Pro | Codex (o3) | Cursor |
|----------|----------|------------|------------|--------|
| Лёгкий день (20 запросов) | $0.56 | $2.40 | $1.00 | $0.67 |
| Средний день (100 запросов) | $2.80 | $5.00 | $5.00 | $1.43 |
| Тяжёлый день (500 запросов) | $14.00 | $12.00 | $25.00 | $4.29 |
| **Бездумный день (440M токенов)** | **$61.88** | $5-10* | $40+ | $10-15* |
| **Месяц активной работы** | **$150-400** | **$20** | **$200+** | **$20** |

*Claude и Cursor имеют фиксированную подписку + usage-based

**Вывод:** При тяжёлом использовании выгоднее всего:
1. **Claude Code Pro ($20/мес)** — фикс цена, все модели
2. **Cursor Pro ($20/мес)** — IDE + все модели
3. DeepSeek — только при лёгком режиме + кэше
