# Graph Report - personal  (2026-05-01)

## Corpus Check
- 24 files · ~158,814 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 439 nodes · 717 edges · 104 communities detected
- Extraction: 74% EXTRACTED · 26% INFERRED · 0% AMBIGUOUS · INFERRED: 189 edges (avg confidence: 0.75)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Community 0|Community 0]]
- [[_COMMUNITY_Community 1|Community 1]]
- [[_COMMUNITY_Community 2|Community 2]]
- [[_COMMUNITY_Community 3|Community 3]]
- [[_COMMUNITY_Community 4|Community 4]]
- [[_COMMUNITY_Community 5|Community 5]]
- [[_COMMUNITY_Community 6|Community 6]]
- [[_COMMUNITY_Community 7|Community 7]]
- [[_COMMUNITY_Community 8|Community 8]]
- [[_COMMUNITY_Community 9|Community 9]]
- [[_COMMUNITY_Community 11|Community 11]]
- [[_COMMUNITY_Community 15|Community 15]]
- [[_COMMUNITY_Community 16|Community 16]]
- [[_COMMUNITY_Community 17|Community 17]]
- [[_COMMUNITY_Community 18|Community 18]]
- [[_COMMUNITY_Community 19|Community 19]]
- [[_COMMUNITY_Community 20|Community 20]]
- [[_COMMUNITY_Community 21|Community 21]]
- [[_COMMUNITY_Community 22|Community 22]]
- [[_COMMUNITY_Community 23|Community 23]]
- [[_COMMUNITY_Community 24|Community 24]]
- [[_COMMUNITY_Community 25|Community 25]]
- [[_COMMUNITY_Community 26|Community 26]]
- [[_COMMUNITY_Community 27|Community 27]]
- [[_COMMUNITY_Community 28|Community 28]]
- [[_COMMUNITY_Community 29|Community 29]]
- [[_COMMUNITY_Community 30|Community 30]]
- [[_COMMUNITY_Community 31|Community 31]]
- [[_COMMUNITY_Community 32|Community 32]]
- [[_COMMUNITY_Community 33|Community 33]]
- [[_COMMUNITY_Community 34|Community 34]]
- [[_COMMUNITY_Community 35|Community 35]]
- [[_COMMUNITY_Community 36|Community 36]]
- [[_COMMUNITY_Community 37|Community 37]]
- [[_COMMUNITY_Community 38|Community 38]]
- [[_COMMUNITY_Community 39|Community 39]]
- [[_COMMUNITY_Community 40|Community 40]]
- [[_COMMUNITY_Community 41|Community 41]]
- [[_COMMUNITY_Community 42|Community 42]]
- [[_COMMUNITY_Community 43|Community 43]]
- [[_COMMUNITY_Community 44|Community 44]]
- [[_COMMUNITY_Community 45|Community 45]]
- [[_COMMUNITY_Community 46|Community 46]]
- [[_COMMUNITY_Community 47|Community 47]]
- [[_COMMUNITY_Community 48|Community 48]]
- [[_COMMUNITY_Community 49|Community 49]]
- [[_COMMUNITY_Community 50|Community 50]]
- [[_COMMUNITY_Community 51|Community 51]]
- [[_COMMUNITY_Community 52|Community 52]]
- [[_COMMUNITY_Community 53|Community 53]]
- [[_COMMUNITY_Community 54|Community 54]]
- [[_COMMUNITY_Community 55|Community 55]]
- [[_COMMUNITY_Community 56|Community 56]]
- [[_COMMUNITY_Community 57|Community 57]]
- [[_COMMUNITY_Community 58|Community 58]]
- [[_COMMUNITY_Community 59|Community 59]]
- [[_COMMUNITY_Community 60|Community 60]]
- [[_COMMUNITY_Community 61|Community 61]]
- [[_COMMUNITY_Community 62|Community 62]]
- [[_COMMUNITY_Community 63|Community 63]]
- [[_COMMUNITY_Community 64|Community 64]]
- [[_COMMUNITY_Community 65|Community 65]]
- [[_COMMUNITY_Community 66|Community 66]]
- [[_COMMUNITY_Community 67|Community 67]]
- [[_COMMUNITY_Community 68|Community 68]]
- [[_COMMUNITY_Community 69|Community 69]]
- [[_COMMUNITY_Community 70|Community 70]]
- [[_COMMUNITY_Community 71|Community 71]]
- [[_COMMUNITY_Community 72|Community 72]]
- [[_COMMUNITY_Community 73|Community 73]]
- [[_COMMUNITY_Community 74|Community 74]]
- [[_COMMUNITY_Community 75|Community 75]]
- [[_COMMUNITY_Community 76|Community 76]]
- [[_COMMUNITY_Community 77|Community 77]]
- [[_COMMUNITY_Community 78|Community 78]]
- [[_COMMUNITY_Community 79|Community 79]]
- [[_COMMUNITY_Community 80|Community 80]]
- [[_COMMUNITY_Community 81|Community 81]]
- [[_COMMUNITY_Community 82|Community 82]]
- [[_COMMUNITY_Community 83|Community 83]]
- [[_COMMUNITY_Community 84|Community 84]]
- [[_COMMUNITY_Community 85|Community 85]]
- [[_COMMUNITY_Community 86|Community 86]]
- [[_COMMUNITY_Community 87|Community 87]]
- [[_COMMUNITY_Community 88|Community 88]]
- [[_COMMUNITY_Community 89|Community 89]]
- [[_COMMUNITY_Community 90|Community 90]]
- [[_COMMUNITY_Community 91|Community 91]]
- [[_COMMUNITY_Community 92|Community 92]]
- [[_COMMUNITY_Community 93|Community 93]]
- [[_COMMUNITY_Community 94|Community 94]]
- [[_COMMUNITY_Community 95|Community 95]]
- [[_COMMUNITY_Community 96|Community 96]]
- [[_COMMUNITY_Community 97|Community 97]]
- [[_COMMUNITY_Community 98|Community 98]]
- [[_COMMUNITY_Community 99|Community 99]]
- [[_COMMUNITY_Community 100|Community 100]]
- [[_COMMUNITY_Community 101|Community 101]]
- [[_COMMUNITY_Community 102|Community 102]]
- [[_COMMUNITY_Community 103|Community 103]]
- [[_COMMUNITY_Community 104|Community 104]]
- [[_COMMUNITY_Community 105|Community 105]]
- [[_COMMUNITY_Community 106|Community 106]]
- [[_COMMUNITY_Community 107|Community 107]]

## God Nodes (most connected - your core abstractions)
1. `SessionManager` - 43 edges
2. `log()` - 25 edges
3. `handle_chat()` - 22 edges
4. `handle_chat_stream()` - 18 edges
5. `fix_request()` - 17 edges
6. `save()` - 16 edges
7. `Session` - 12 edges
8. `Handler` - 12 edges
9. `chat()` - 12 edges
10. `_path_from_params()` - 11 edges

## Surprising Connections (you probably didn't know these)
- `_ocr_describe()` --calls--> `run()`  [INFERRED]
  claude-code-setup/ds-proxy.py → backlinks/sites/wikidot.py
- `handle_chat()` --calls--> `save()`  [INFERRED]
  claude-code-setup/deepseek-agent/agent.py → backlinks/tracker.py
- `handle_chat_stream()` --calls--> `save()`  [INFERRED]
  claude-code-setup/deepseek-agent/agent.py → backlinks/tracker.py
- `SessionManager` --uses--> `Streaming call with tool support.`  [INFERRED]
  claude-code-setup/deepseek-agent/session_manager.py → claude-code-setup/deepseek-agent/agent.py
- `SessionManager` --uses--> `Hash-based key to identify a pending dangerous operation.`  [INFERRED]
  claude-code-setup/deepseek-agent/session_manager.py → claude-code-setup/deepseek-agent/agent.py

## Communities

### Community 0 - "Community 0"
Cohesion: 0.06
Nodes (72): _alert(), _auto_memory_extract(), _check_auth(), check_services(), _create_api_key(), _cron_on_trigger(), _docker_api(), _filter_domains() (+64 more)

### Community 1 - "Community 1"
Cohesion: 0.05
Nodes (44): _auto_route(), _build_auto_prompt(), _check_budget(), _classify_task(), _filter_tools(), handle_chat(), handle_chat_stream(), Handler (+36 more)

### Community 2 - "Community 2"
Cohesion: 0.06
Nodes (49): _api_call_with_tools(), Call DeepSeek API with tool calling support. Returns full message object., _api_call(), _api_key(), audit_plugins(), audit_usage(), calculate_cost(), chat() (+41 more)

### Community 3 - "Community 3"
Cohesion: 0.07
Nodes (46): BaseHTTPRequestHandler, _compact_json_text(), _compress_content(), _count_tokens(), _dedup_consecutive_results(), _describe_image(), fix_request(), _groq_describe() (+38 more)

### Community 4 - "Community 4"
Cohesion: 0.06
Nodes (32): About.me — профиль с ссылкой на сайт DA: 71, Do-Follow: YES, run(), _shutdown_handler(), Diigo — социальная закладка + профиль DA: 70, Do-Follow: YES (закладки индексиру, run(), Disqus — профиль с ссылкой на сайт DA: 93, Do-Follow: NO (но высокий авторитет д, run(), Folkd.com — социальная закладка (bookmark) DA: 60, Do-Follow: YES (+24 more)

### Community 5 - "Community 5"
Cohesion: 0.15
Nodes (13): _api_call_with_tools_stream(), init_mcp(), Initialize MCP servers and merge their tools., Streaming call with tool support., main(), parse_rankd_text(), Parse raw text pasted from Rankd listing pages., get_all_platform_urls() (+5 more)

### Community 6 - "Community 6"
Cohesion: 0.18
Nodes (16): classify_error(), extract_patterns(), generate_learned_patterns(), get_fix_for_cause(), get_fix_for_error(), index_to_goodmem(), main(), parse_transcript() (+8 more)

### Community 7 - "Community 7"
Cohesion: 0.38
Nodes (6): NeoCities — регистрация + загрузка статьи через API DA: 83, Do-Follow: Yes, Фаза, Зарегистрировать аккаунт через браузер., Загрузить HTML страницу через API., register(), run(), upload_page()

### Community 8 - "Community 8"
Cohesion: 0.6
Nodes (4): get_user_id(), publish_article(), Medium.com — публикация статьи через API DA: 96, Do-Follow: YES (ссылки в тексте, run()

### Community 9 - "Community 9"
Cohesion: 1.0
Nodes (2): main(), parse_table()

### Community 11 - "Community 11"
Cohesion: 1.0
Nodes (1): Backlink Bot — мульти-сайтовая конфигурация Поддерживает несколько доменов. Выбо

### Community 15 - "Community 15"
Cohesion: 1.0
Nodes (1): Список доступных моделей.

### Community 16 - "Community 16"
Cohesion: 1.0
Nodes (1): Список доступных моделей.

### Community 17 - "Community 17"
Cohesion: 1.0
Nodes (1): Lazy-загрузка tiktoken encoding.     Падает молча если tiktoken не установлен —

### Community 18 - "Community 18"
Cohesion: 1.0
Nodes (1): Оценка числа токенов через tiktoken (cl100k_base).     DeepSeek V4 использует то

### Community 19 - "Community 19"
Cohesion: 1.0
Nodes (1): Сумма токенов во всех сообщениях.

### Community 20 - "Community 20"
Cohesion: 1.0
Nodes (1): 12,345,678 → формат с разделителями.

### Community 21 - "Community 21"
Cohesion: 1.0
Nodes (1): Расчёт стоимости запроса в USD по ценам DeepSeek.

### Community 22 - "Community 22"
Cohesion: 1.0
Nodes (1): Логирует каждый API-вызов в JSONL-файл.     Файл: ~/.local/var/deepseek-usage.js

### Community 23 - "Community 23"
Cohesion: 1.0
Nodes (1): Итоги за всё время из существующего лога.

### Community 24 - "Community 24"
Cohesion: 1.0
Nodes (1): Не запрашивать больше токенов, чем влезет в контекст 64K.     Пример: промпт 50K

### Community 25 - "Community 25"
Cohesion: 1.0
Nodes (1): Предупреждения если промпт/система выходят за разумные пределы.

### Community 26 - "Community 26"
Cohesion: 1.0
Nodes (1): Низкоуровневый вызов DeepSeek Chat API.      Отличия от исходной версии:     - d

### Community 27 - "Community 27"
Cohesion: 1.0
Nodes (1): Вызов DeepSeek (не streaming).      Args:         prompt: текст запроса

### Community 28 - "Community 28"
Cohesion: 1.0
Nodes (1): Streaming вызов DeepSeek.      DeepSeek в streaming-режиме шлёт usage     в фина

### Community 29 - "Community 29"
Cohesion: 1.0
Nodes (1): Сводка по расходу из JSONL-лога.

### Community 30 - "Community 30"
Cohesion: 1.0
Nodes (1): Список доступных моделей.

### Community 31 - "Community 31"
Cohesion: 1.0
Nodes (1): Daily maintenance: clean logs, check disk, AI summary.

### Community 32 - "Community 32"
Cohesion: 1.0
Nodes (1): Weekly: update reference repos + graphify graphs.

### Community 33 - "Community 33"
Cohesion: 1.0
Nodes (1): Token count via tiktoken cl100k_base (shared by Claude & DeepSeek BPE).

### Community 34 - "Community 34"
Cohesion: 1.0
Nodes (1): Drop oldest non-system messages to fit DeepSeek's 128K window.

### Community 35 - "Community 35"
Cohesion: 1.0
Nodes (1): Token count for a message including format overhead (~5 tok/msg).

### Community 36 - "Community 36"
Cohesion: 1.0
Nodes (1): Try Groq vision → OCR → fallback placeholder.

### Community 37 - "Community 37"
Cohesion: 1.0
Nodes (1): Recursively replace image/document blocks with text (в т.ч. внутри tool_result).

### Community 38 - "Community 38"
Cohesion: 1.0
Nodes (1): Strip trailing spaces per line + edges. Zero-risk — no content modification beyo

### Community 39 - "Community 39"
Cohesion: 1.0
Nodes (1): True if message is exclusively tool_result/tool_use blocks.

### Community 40 - "Community 40"
Cohesion: 1.0
Nodes (1): Adaptive truncation: only when total budget exceeded, never below TOOL_RESULT_MA

### Community 41 - "Community 41"
Cohesion: 1.0
Nodes (1): Remove empty tool_result and text blocks. Zero risk — empty blocks carry no info

### Community 42 - "Community 42"
Cohesion: 1.0
Nodes (1): Merge adjacent text blocks into one. Zero risk — preserves all content.

### Community 43 - "Community 43"
Cohesion: 1.0
Nodes (1): Extract text from a tool_result block for comparison.

### Community 44 - "Community 44"
Cohesion: 1.0
Nodes (1): Strip boilerplate/hedging from tool descriptions. Zero-risk: preserves all seman

### Community 45 - "Community 45"
Cohesion: 1.0
Nodes (1): Strip markdown code fences from tool results. Zero-risk: only strips standard fe

### Community 46 - "Community 46"
Cohesion: 1.0
Nodes (1): Compact pretty-printed JSON. Zero risk — identical data, fewer tokens.

### Community 47 - "Community 47"
Cohesion: 1.0
Nodes (1): Remove cache_control from all blocks (DeepSeek doesn't support Anthropic caching

### Community 48 - "Community 48"
Cohesion: 1.0
Nodes (1): Remove id/type from messages — DeepSeek ignores them (zero-risk).

### Community 49 - "Community 49"
Cohesion: 1.0
Nodes (1): Normalize whitespace, fix images, strip thinking, smart-truncate context.

### Community 50 - "Community 50"
Cohesion: 1.0
Nodes (1): Log token consumption to stderr (observability, not optimisation).

### Community 51 - "Community 51"
Cohesion: 1.0
Nodes (1): Token count for a message including format overhead (~5 tok/msg).

### Community 52 - "Community 52"
Cohesion: 1.0
Nodes (1): Try Groq vision → OCR → fallback placeholder.

### Community 53 - "Community 53"
Cohesion: 1.0
Nodes (1): Recursively replace image/document blocks with text (в т.ч. внутри tool_result).

### Community 54 - "Community 54"
Cohesion: 1.0
Nodes (1): True if message is exclusively tool_result/tool_use blocks.

### Community 55 - "Community 55"
Cohesion: 1.0
Nodes (1): Strip ANSI codes only — no [Step N/M] removal (risk: model references step numbe

### Community 56 - "Community 56"
Cohesion: 1.0
Nodes (1): True if message is exclusively tool_result/tool_use blocks.

### Community 57 - "Community 57"
Cohesion: 1.0
Nodes (1): Adaptive truncation: only when total budget exceeded, never below TOOL_RESULT_MA

### Community 58 - "Community 58"
Cohesion: 1.0
Nodes (1): Remove empty tool_result and text blocks. Zero risk — empty blocks carry no info

### Community 59 - "Community 59"
Cohesion: 1.0
Nodes (1): Extract text from a tool_result block for comparison.

### Community 60 - "Community 60"
Cohesion: 1.0
Nodes (1): Drop consecutive tool_result blocks with identical text. Zero-risk: identical co

### Community 61 - "Community 61"
Cohesion: 1.0
Nodes (1): Strip boilerplate/hedging from tool descriptions. Zero-risk: preserves all seman

### Community 62 - "Community 62"
Cohesion: 1.0
Nodes (1): Strip markdown code fences from tool results. Zero-risk: only strips standard fe

### Community 63 - "Community 63"
Cohesion: 1.0
Nodes (1): Compact pretty-printed JSON. Zero risk — identical data, fewer tokens.

### Community 64 - "Community 64"
Cohesion: 1.0
Nodes (1): Remove cache_control from all blocks (DeepSeek doesn't support Anthropic caching

### Community 65 - "Community 65"
Cohesion: 1.0
Nodes (1): Remove id/type from messages — DeepSeek ignores them (zero-risk).

### Community 66 - "Community 66"
Cohesion: 1.0
Nodes (1): Normalize whitespace, fix images, strip thinking, smart-truncate context.

### Community 67 - "Community 67"
Cohesion: 1.0
Nodes (1): Log token consumption to stderr (observability, not optimisation).

### Community 68 - "Community 68"
Cohesion: 1.0
Nodes (1): Drop consecutive tool_result blocks with identical text. Low risk — identical co

### Community 69 - "Community 69"
Cohesion: 1.0
Nodes (1): Strip boilerplate/hedging from tool descriptions. Zero risk — preserves all sema

### Community 70 - "Community 70"
Cohesion: 1.0
Nodes (1): Strip markdown code fences from tool results. Lets _compact_json_text work on fe

### Community 71 - "Community 71"
Cohesion: 1.0
Nodes (1): Compact pretty-printed JSON. Zero risk — identical data, fewer tokens.

### Community 72 - "Community 72"
Cohesion: 1.0
Nodes (1): Remove cache_control from all blocks (DeepSeek doesn't support Anthropic caching

### Community 73 - "Community 73"
Cohesion: 1.0
Nodes (1): Remove id/type from messages — DeepSeek ignores them (zero-risk).

### Community 74 - "Community 74"
Cohesion: 1.0
Nodes (1): Normalize whitespace, fix images, strip thinking, smart-truncate context.

### Community 75 - "Community 75"
Cohesion: 1.0
Nodes (1): Log token consumption to stderr (observability, not optimisation).

### Community 76 - "Community 76"
Cohesion: 1.0
Nodes (1): Describe image via Groq vision API.

### Community 77 - "Community 77"
Cohesion: 1.0
Nodes (1): Token count for a message including format overhead (~5 tok/msg).

### Community 78 - "Community 78"
Cohesion: 1.0
Nodes (1): Try Groq vision → OCR → fallback placeholder.

### Community 79 - "Community 79"
Cohesion: 1.0
Nodes (1): Recursively replace image blocks with text descriptions (в т.ч. внутри tool_resu

### Community 80 - "Community 80"
Cohesion: 1.0
Nodes (1): Compress 3+ newlines → 2, strip trailing spaces per line, strip edges.

### Community 81 - "Community 81"
Cohesion: 1.0
Nodes (1): True if message is exclusively tool_result/tool_use blocks.

### Community 82 - "Community 82"
Cohesion: 1.0
Nodes (1): Truncate tool_result content to TOOL_RESULT_MAX_TOKENS (mutates in-place).

### Community 83 - "Community 83"
Cohesion: 1.0
Nodes (1): Remove cache_control from all blocks (DeepSeek doesn't support Anthropic caching

### Community 84 - "Community 84"
Cohesion: 1.0
Nodes (1): Normalize whitespace, fix images, strip thinking, smart-truncate context.

### Community 85 - "Community 85"
Cohesion: 1.0
Nodes (1): Describe image via Groq vision API.

### Community 86 - "Community 86"
Cohesion: 1.0
Nodes (1): OCR image via tesseract.

### Community 87 - "Community 87"
Cohesion: 1.0
Nodes (1): Token count via tiktoken cl100k_base (shared by Claude & DeepSeek BPE).

### Community 88 - "Community 88"
Cohesion: 1.0
Nodes (1): Drop oldest non-system messages to fit DeepSeek's 128K window.

### Community 89 - "Community 89"
Cohesion: 1.0
Nodes (1): Token count for a message including format overhead (~5 tok/msg).

### Community 90 - "Community 90"
Cohesion: 1.0
Nodes (1): Try Groq vision → OCR → fallback placeholder.

### Community 91 - "Community 91"
Cohesion: 1.0
Nodes (1): Recursively replace image blocks with text descriptions (в т.ч. внутри tool_resu

### Community 92 - "Community 92"
Cohesion: 1.0
Nodes (1): Compress 3+ newlines → 2, strip trailing spaces per line, strip edges.

### Community 93 - "Community 93"
Cohesion: 1.0
Nodes (1): Normalize whitespace, fix images, strip thinking, smart-truncate context.

### Community 94 - "Community 94"
Cohesion: 1.0
Nodes (1): Fix images (vision/OCR), strip thinking, truncate context for DeepSeek.

### Community 95 - "Community 95"
Cohesion: 1.0
Nodes (1): Try Groq vision → OCR → fallback placeholder.

### Community 96 - "Community 96"
Cohesion: 1.0
Nodes (1): Recursively replace image blocks with text descriptions (в т.ч. внутри tool_resu

### Community 97 - "Community 97"
Cohesion: 1.0
Nodes (1): Fix images (vision/OCR), strip thinking, truncate context for DeepSeek.

### Community 98 - "Community 98"
Cohesion: 1.0
Nodes (1): Try Groq vision → OCR → fallback placeholder.

### Community 99 - "Community 99"
Cohesion: 1.0
Nodes (1): Fix images (vision/OCR), strip thinking, truncate context for DeepSeek.

### Community 100 - "Community 100"
Cohesion: 1.0
Nodes (1): Token count for a message including format overhead (~5 tok/msg).

### Community 101 - "Community 101"
Cohesion: 1.0
Nodes (1): Try Groq vision → OCR → fallback placeholder.

### Community 102 - "Community 102"
Cohesion: 1.0
Nodes (1): Fix images (vision/OCR), strip thinking, truncate context for DeepSeek.

### Community 103 - "Community 103"
Cohesion: 1.0
Nodes (1): Toka estimate — ~4 chars/token, conservative for CJK/emoji.

### Community 104 - "Community 104"
Cohesion: 1.0
Nodes (1): Drop oldest non-system messages to fit DeepSeek's 128K window.

### Community 105 - "Community 105"
Cohesion: 1.0
Nodes (1): Try Groq vision → OCR → fallback placeholder.

### Community 106 - "Community 106"
Cohesion: 1.0
Nodes (1): Strip images and fix thinking blocks.

### Community 107 - "Community 107"
Cohesion: 1.0
Nodes (1): Forward SSE stream, unfiltered.

## Knowledge Gaps
- **175 isolated node(s):** `Describe image via Groq vision API.`, `OCR image via tesseract.`, `Token count via tiktoken cl100k_base (shared by Claude & DeepSeek BPE).`, `Role-weighted truncation: compress content first, then drop tool-only, then newe`, `Try Groq vision → OCR → fallback placeholder.` (+170 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Community 9`** (3 nodes): `parse_rankd_table.py`, `main()`, `parse_table()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 11`** (2 nodes): `config.py`, `Backlink Bot — мульти-сайтовая конфигурация Поддерживает несколько доменов. Выбо`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 15`** (1 nodes): `Список доступных моделей.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 16`** (1 nodes): `Список доступных моделей.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 17`** (1 nodes): `Lazy-загрузка tiktoken encoding.     Падает молча если tiktoken не установлен —`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 18`** (1 nodes): `Оценка числа токенов через tiktoken (cl100k_base).     DeepSeek V4 использует то`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 19`** (1 nodes): `Сумма токенов во всех сообщениях.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 20`** (1 nodes): `12,345,678 → формат с разделителями.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 21`** (1 nodes): `Расчёт стоимости запроса в USD по ценам DeepSeek.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 22`** (1 nodes): `Логирует каждый API-вызов в JSONL-файл.     Файл: ~/.local/var/deepseek-usage.js`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 23`** (1 nodes): `Итоги за всё время из существующего лога.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 24`** (1 nodes): `Не запрашивать больше токенов, чем влезет в контекст 64K.     Пример: промпт 50K`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 25`** (1 nodes): `Предупреждения если промпт/система выходят за разумные пределы.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 26`** (1 nodes): `Низкоуровневый вызов DeepSeek Chat API.      Отличия от исходной версии:     - d`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 27`** (1 nodes): `Вызов DeepSeek (не streaming).      Args:         prompt: текст запроса`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 28`** (1 nodes): `Streaming вызов DeepSeek.      DeepSeek в streaming-режиме шлёт usage     в фина`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 29`** (1 nodes): `Сводка по расходу из JSONL-лога.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 30`** (1 nodes): `Список доступных моделей.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 31`** (1 nodes): `Daily maintenance: clean logs, check disk, AI summary.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 32`** (1 nodes): `Weekly: update reference repos + graphify graphs.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 33`** (1 nodes): `Token count via tiktoken cl100k_base (shared by Claude & DeepSeek BPE).`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 34`** (1 nodes): `Drop oldest non-system messages to fit DeepSeek's 128K window.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 35`** (1 nodes): `Token count for a message including format overhead (~5 tok/msg).`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 36`** (1 nodes): `Try Groq vision → OCR → fallback placeholder.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 37`** (1 nodes): `Recursively replace image/document blocks with text (в т.ч. внутри tool_result).`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 38`** (1 nodes): `Strip trailing spaces per line + edges. Zero-risk — no content modification beyo`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 39`** (1 nodes): `True if message is exclusively tool_result/tool_use blocks.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 40`** (1 nodes): `Adaptive truncation: only when total budget exceeded, never below TOOL_RESULT_MA`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 41`** (1 nodes): `Remove empty tool_result and text blocks. Zero risk — empty blocks carry no info`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 42`** (1 nodes): `Merge adjacent text blocks into one. Zero risk — preserves all content.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 43`** (1 nodes): `Extract text from a tool_result block for comparison.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 44`** (1 nodes): `Strip boilerplate/hedging from tool descriptions. Zero-risk: preserves all seman`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 45`** (1 nodes): `Strip markdown code fences from tool results. Zero-risk: only strips standard fe`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 46`** (1 nodes): `Compact pretty-printed JSON. Zero risk — identical data, fewer tokens.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 47`** (1 nodes): `Remove cache_control from all blocks (DeepSeek doesn't support Anthropic caching`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 48`** (1 nodes): `Remove id/type from messages — DeepSeek ignores them (zero-risk).`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 49`** (1 nodes): `Normalize whitespace, fix images, strip thinking, smart-truncate context.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 50`** (1 nodes): `Log token consumption to stderr (observability, not optimisation).`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 51`** (1 nodes): `Token count for a message including format overhead (~5 tok/msg).`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 52`** (1 nodes): `Try Groq vision → OCR → fallback placeholder.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 53`** (1 nodes): `Recursively replace image/document blocks with text (в т.ч. внутри tool_result).`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 54`** (1 nodes): `True if message is exclusively tool_result/tool_use blocks.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 55`** (1 nodes): `Strip ANSI codes only — no [Step N/M] removal (risk: model references step numbe`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 56`** (1 nodes): `True if message is exclusively tool_result/tool_use blocks.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 57`** (1 nodes): `Adaptive truncation: only when total budget exceeded, never below TOOL_RESULT_MA`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 58`** (1 nodes): `Remove empty tool_result and text blocks. Zero risk — empty blocks carry no info`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 59`** (1 nodes): `Extract text from a tool_result block for comparison.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 60`** (1 nodes): `Drop consecutive tool_result blocks with identical text. Zero-risk: identical co`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 61`** (1 nodes): `Strip boilerplate/hedging from tool descriptions. Zero-risk: preserves all seman`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 62`** (1 nodes): `Strip markdown code fences from tool results. Zero-risk: only strips standard fe`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 63`** (1 nodes): `Compact pretty-printed JSON. Zero risk — identical data, fewer tokens.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 64`** (1 nodes): `Remove cache_control from all blocks (DeepSeek doesn't support Anthropic caching`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 65`** (1 nodes): `Remove id/type from messages — DeepSeek ignores them (zero-risk).`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 66`** (1 nodes): `Normalize whitespace, fix images, strip thinking, smart-truncate context.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 67`** (1 nodes): `Log token consumption to stderr (observability, not optimisation).`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 68`** (1 nodes): `Drop consecutive tool_result blocks with identical text. Low risk — identical co`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 69`** (1 nodes): `Strip boilerplate/hedging from tool descriptions. Zero risk — preserves all sema`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 70`** (1 nodes): `Strip markdown code fences from tool results. Lets _compact_json_text work on fe`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 71`** (1 nodes): `Compact pretty-printed JSON. Zero risk — identical data, fewer tokens.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 72`** (1 nodes): `Remove cache_control from all blocks (DeepSeek doesn't support Anthropic caching`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 73`** (1 nodes): `Remove id/type from messages — DeepSeek ignores them (zero-risk).`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 74`** (1 nodes): `Normalize whitespace, fix images, strip thinking, smart-truncate context.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 75`** (1 nodes): `Log token consumption to stderr (observability, not optimisation).`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 76`** (1 nodes): `Describe image via Groq vision API.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 77`** (1 nodes): `Token count for a message including format overhead (~5 tok/msg).`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 78`** (1 nodes): `Try Groq vision → OCR → fallback placeholder.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 79`** (1 nodes): `Recursively replace image blocks with text descriptions (в т.ч. внутри tool_resu`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 80`** (1 nodes): `Compress 3+ newlines → 2, strip trailing spaces per line, strip edges.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 81`** (1 nodes): `True if message is exclusively tool_result/tool_use blocks.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 82`** (1 nodes): `Truncate tool_result content to TOOL_RESULT_MAX_TOKENS (mutates in-place).`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 83`** (1 nodes): `Remove cache_control from all blocks (DeepSeek doesn't support Anthropic caching`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 84`** (1 nodes): `Normalize whitespace, fix images, strip thinking, smart-truncate context.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 85`** (1 nodes): `Describe image via Groq vision API.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 86`** (1 nodes): `OCR image via tesseract.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 87`** (1 nodes): `Token count via tiktoken cl100k_base (shared by Claude & DeepSeek BPE).`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 88`** (1 nodes): `Drop oldest non-system messages to fit DeepSeek's 128K window.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 89`** (1 nodes): `Token count for a message including format overhead (~5 tok/msg).`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 90`** (1 nodes): `Try Groq vision → OCR → fallback placeholder.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 91`** (1 nodes): `Recursively replace image blocks with text descriptions (в т.ч. внутри tool_resu`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 92`** (1 nodes): `Compress 3+ newlines → 2, strip trailing spaces per line, strip edges.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 93`** (1 nodes): `Normalize whitespace, fix images, strip thinking, smart-truncate context.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 94`** (1 nodes): `Fix images (vision/OCR), strip thinking, truncate context for DeepSeek.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 95`** (1 nodes): `Try Groq vision → OCR → fallback placeholder.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 96`** (1 nodes): `Recursively replace image blocks with text descriptions (в т.ч. внутри tool_resu`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 97`** (1 nodes): `Fix images (vision/OCR), strip thinking, truncate context for DeepSeek.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 98`** (1 nodes): `Try Groq vision → OCR → fallback placeholder.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 99`** (1 nodes): `Fix images (vision/OCR), strip thinking, truncate context for DeepSeek.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 100`** (1 nodes): `Token count for a message including format overhead (~5 tok/msg).`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 101`** (1 nodes): `Try Groq vision → OCR → fallback placeholder.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 102`** (1 nodes): `Fix images (vision/OCR), strip thinking, truncate context for DeepSeek.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 103`** (1 nodes): `Toka estimate — ~4 chars/token, conservative for CJK/emoji.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 104`** (1 nodes): `Drop oldest non-system messages to fit DeepSeek's 128K window.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 105`** (1 nodes): `Try Groq vision → OCR → fallback placeholder.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 106`** (1 nodes): `Strip images and fix thinking blocks.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 107`** (1 nodes): `Forward SSE stream, unfiltered.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `SessionManager` connect `Community 1` to `Community 0`, `Community 2`, `Community 5`?**
  _High betweenness centrality (0.085) - this node is a cross-community bridge._
- **Why does `save()` connect `Community 4` to `Community 8`, `Community 1`, `Community 7`?**
  _High betweenness centrality (0.081) - this node is a cross-community bridge._
- **Why does `handle_chat()` connect `Community 1` to `Community 0`, `Community 2`, `Community 4`, `Community 5`?**
  _High betweenness centrality (0.040) - this node is a cross-community bridge._
- **Are the 30 inferred relationships involving `SessionManager` (e.g. with `Handler` and `Streaming call with tool support.`) actually correct?**
  _`SessionManager` has 30 INFERRED edges - model-reasoned connections that need verification._
- **Are the 8 inferred relationships involving `handle_chat()` (e.g. with `.get()` and `.create()`) actually correct?**
  _`handle_chat()` has 8 INFERRED edges - model-reasoned connections that need verification._
- **Are the 7 inferred relationships involving `handle_chat_stream()` (e.g. with `.get()` and `.create()`) actually correct?**
  _`handle_chat_stream()` has 7 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Describe image via Groq vision API.`, `OCR image via tesseract.`, `Token count via tiktoken cl100k_base (shared by Claude & DeepSeek BPE).` to the rest of the system?**
  _175 weakly-connected nodes found - possible documentation gaps or missing edges._