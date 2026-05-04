# graphify
- **graphify** (`~/.claude/skills/graphify/SKILL.md`) — любой ввод в knowledge graph. Триггер: `/graphify`
При `/graphify` → Skill tool первым делом.

# Язык общения
- Всегда отвечать на русском. Коммиты, доки, код-ревью — всё на русском.
- Исключение: код, названия переменных/функций, тех.термины на английском.

# Репозитории
- **personal** = `~/personal` (github.com/PortfelOnline/personal) — заметки, принципы, документы
- **kadmap** = `~/kadmap` (github.com/PortfelOnline/kadmap) — kadastrmap.info

# DeepSeek Conciseness (70% rule)
- Output на 70% короче инстинкта. Удаляй воду (первый/последний абзац). Булеты > абзацы.
- TRIVIAL: 0 объяснений. LOW: 1 предложение. MEDIUM: 2-3.
- Запрещено: "Let me explain", "I will now", "В заключение". Prefer таблицы/JSON > прозы.

# Token Economy — essentials
- **Confidence STOP**: если уверен ≥0.6 → отвечай без инструментов. fact=0.65, code=0.7, partial_data+0.2.
- **Чтение**: только offset/limit (не весь файл). grep → Read. Не перечитывать то же самое.
- **Tool**: 1 за шаг (исключение: ls/pwd/cat cheap). Ошибка → STOP, не retry.
- **Cost reference**: Read~500-1K, Bash/WebFetch~1-3K, WebSearch~2-5K, graphify~0.5-1.5K, browser~3-10K tok.
- **Partial Read**: `[LIVE_SUMMARIZED]` / `[PARTIAL_FILE_DO_NOT_ASSUME_COMPLETE]` → файл не полный, не делай выводов из отсутствия данных. Если задача требует полного скана → grep → offset/limit.
- **Ответ**: не сжимать команды/параметры/пути/инструкции. Сжимать объяснения/текст/описания.
