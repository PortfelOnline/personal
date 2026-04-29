# Graph Report - personal  (2026-04-29)

## Corpus Check
- 18 files · ~137,445 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 153 nodes · 177 edges · 37 communities detected
- Extraction: 93% EXTRACTED · 7% INFERRED · 0% AMBIGUOUS · INFERRED: 13 edges (avg confidence: 0.8)
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
- [[_COMMUNITY_Community 10|Community 10]]
- [[_COMMUNITY_Community 11|Community 11]]
- [[_COMMUNITY_Community 12|Community 12]]
- [[_COMMUNITY_Community 13|Community 13]]
- [[_COMMUNITY_Community 14|Community 14]]
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

## God Nodes (most connected - your core abstractions)
1. `save()` - 12 edges
2. `fix_request()` - 9 edges
3. `ProxyHandler` - 7 edges
4. `Handler` - 6 edges
5. `main()` - 6 edges
6. `_truncate_messages()` - 5 edges
7. `_msg_tokens()` - 5 edges
8. `_describe_image()` - 5 edges
9. `nightly_cleanup()` - 5 edges
10. `log()` - 5 edges

## Surprising Connections (you probably didn't know these)
- `_ocr_describe()` --calls--> `run()`  [INFERRED]
  claude-code-setup/ds-proxy.py → backlinks/sites/wikidot.py
- `save()` --calls--> `run()`  [INFERRED]
  backlinks/tracker.py → backlinks/sites/diigo.py
- `save()` --calls--> `run()`  [INFERRED]
  backlinks/tracker.py → backlinks/sites/medium.py
- `save()` --calls--> `run()`  [INFERRED]
  backlinks/tracker.py → backlinks/sites/disqus.py
- `save()` --calls--> `run()`  [INFERRED]
  backlinks/tracker.py → backlinks/sites/about_me.py

## Communities

### Community 0 - "Community 0"
Cohesion: 0.09
Nodes (22): About.me — профиль с ссылкой на сайт DA: 71, Do-Follow: YES, run(), Disqus — профиль с ссылкой на сайт DA: 93, Do-Follow: NO (но высокий авторитет д, run(), Folkd.com — социальная закладка (bookmark) DA: 60, Do-Follow: YES, run(), _get_done_sites(), main() (+14 more)

### Community 1 - "Community 1"
Cohesion: 0.12
Nodes (24): _count_tokens(), _describe_image(), fix_request(), _groq_describe(), _is_tool_only(), _msg_tokens(), _normalize_text(), _ocr_describe() (+16 more)

### Community 2 - "Community 2"
Cohesion: 0.18
Nodes (16): classify_error(), extract_patterns(), generate_learned_patterns(), get_fix_for_cause(), get_fix_for_error(), index_to_goodmem(), main(), parse_transcript() (+8 more)

### Community 3 - "Community 3"
Cohesion: 0.24
Nodes (9): _alert(), Handler, log(), nightly_cleanup(), Daily maintenance: clean logs, check disk, AI summary., Weekly: update reference repos + graphify graphs., run(), weekly_refs_update() (+1 more)

### Community 4 - "Community 4"
Cohesion: 0.39
Nodes (7): api_post(), create_account(), publish_article(), Telegra.ph — публикация статьи без регистрации DA: 81, Do-Follow: Yes, Фаза 2, Создать анонимный аккаунт Telegraph., Опубликовать статью из файла, вернуть URL., run()

### Community 5 - "Community 5"
Cohesion: 0.38
Nodes (6): NeoCities — регистрация + загрузка статьи через API DA: 83, Do-Follow: Yes, Фаза, Зарегистрировать аккаунт через браузер., Загрузить HTML страницу через API., register(), run(), upload_page()

### Community 6 - "Community 6"
Cohesion: 0.53
Nodes (1): ProxyHandler

### Community 7 - "Community 7"
Cohesion: 0.47
Nodes (5): get_all_platform_urls(), main(), Scrape a single platform page and return structured data., Get all platform page URLs from the Rankd database., scrape_platform_page()

### Community 8 - "Community 8"
Cohesion: 0.6
Nodes (4): get_user_id(), publish_article(), Medium.com — публикация статьи через API DA: 96, Do-Follow: YES (ссылки в тексте, run()

### Community 9 - "Community 9"
Cohesion: 0.67
Nodes (3): main(), parse_rankd_text(), Parse raw text pasted from Rankd listing pages.

### Community 10 - "Community 10"
Cohesion: 1.0
Nodes (2): main(), parse_table()

### Community 11 - "Community 11"
Cohesion: 0.67
Nodes (2): Diigo — социальная закладка + профиль DA: 70, Do-Follow: YES (закладки индексиру, run()

### Community 12 - "Community 12"
Cohesion: 1.0
Nodes (1): Backlink Bot — мульти-сайтовая конфигурация Поддерживает несколько доменов. Выбо

### Community 13 - "Community 13"
Cohesion: 1.0
Nodes (1): Describe image via Groq vision API.

### Community 14 - "Community 14"
Cohesion: 1.0
Nodes (1): OCR image via tesseract.

### Community 15 - "Community 15"
Cohesion: 1.0
Nodes (1): Token count via tiktoken cl100k_base (shared by Claude & DeepSeek BPE).

### Community 16 - "Community 16"
Cohesion: 1.0
Nodes (1): Drop oldest non-system messages to fit DeepSeek's 128K window.

### Community 17 - "Community 17"
Cohesion: 1.0
Nodes (1): Token count for a message including format overhead (~5 tok/msg).

### Community 18 - "Community 18"
Cohesion: 1.0
Nodes (1): Try Groq vision → OCR → fallback placeholder.

### Community 19 - "Community 19"
Cohesion: 1.0
Nodes (1): Recursively replace image blocks with text descriptions (в т.ч. внутри tool_resu

### Community 20 - "Community 20"
Cohesion: 1.0
Nodes (1): Compress 3+ newlines → 2, strip trailing spaces per line, strip edges.

### Community 21 - "Community 21"
Cohesion: 1.0
Nodes (1): True if message is exclusively tool_result/tool_use blocks.

### Community 22 - "Community 22"
Cohesion: 1.0
Nodes (1): Normalize whitespace, fix images, strip thinking, smart-truncate context.

### Community 23 - "Community 23"
Cohesion: 1.0
Nodes (1): Fix images (vision/OCR), strip thinking, truncate context for DeepSeek.

### Community 24 - "Community 24"
Cohesion: 1.0
Nodes (1): Try Groq vision → OCR → fallback placeholder.

### Community 25 - "Community 25"
Cohesion: 1.0
Nodes (1): Recursively replace image blocks with text descriptions (в т.ч. внутри tool_resu

### Community 26 - "Community 26"
Cohesion: 1.0
Nodes (1): Fix images (vision/OCR), strip thinking, truncate context for DeepSeek.

### Community 27 - "Community 27"
Cohesion: 1.0
Nodes (1): Try Groq vision → OCR → fallback placeholder.

### Community 28 - "Community 28"
Cohesion: 1.0
Nodes (1): Fix images (vision/OCR), strip thinking, truncate context for DeepSeek.

### Community 29 - "Community 29"
Cohesion: 1.0
Nodes (1): Token count for a message including format overhead (~5 tok/msg).

### Community 30 - "Community 30"
Cohesion: 1.0
Nodes (1): Try Groq vision → OCR → fallback placeholder.

### Community 31 - "Community 31"
Cohesion: 1.0
Nodes (1): Fix images (vision/OCR), strip thinking, truncate context for DeepSeek.

### Community 32 - "Community 32"
Cohesion: 1.0
Nodes (1): Toka estimate — ~4 chars/token, conservative for CJK/emoji.

### Community 33 - "Community 33"
Cohesion: 1.0
Nodes (1): Drop oldest non-system messages to fit DeepSeek's 128K window.

### Community 34 - "Community 34"
Cohesion: 1.0
Nodes (1): Try Groq vision → OCR → fallback placeholder.

### Community 35 - "Community 35"
Cohesion: 1.0
Nodes (1): Strip images and fix thinking blocks.

### Community 36 - "Community 36"
Cohesion: 1.0
Nodes (1): Forward SSE stream, unfiltered.

## Knowledge Gaps
- **67 isolated node(s):** `Describe image via Groq vision API.`, `OCR image via tesseract.`, `Token count via tiktoken cl100k_base (shared by Claude & DeepSeek BPE).`, `Drop oldest non-system messages to fit DeepSeek's 128K window.`, `Token count for a message including format overhead (~5 tok/msg).` (+62 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Community 6`** (6 nodes): `ProxyHandler`, `.do_GET()`, `.do_HEAD()`, `.do_PATCH()`, `.do_POST()`, `._proxy()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 10`** (3 nodes): `parse_rankd_table.py`, `main()`, `parse_table()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 11`** (3 nodes): `diigo.py`, `Diigo — социальная закладка + профиль DA: 70, Do-Follow: YES (закладки индексиру`, `run()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 12`** (2 nodes): `config.py`, `Backlink Bot — мульти-сайтовая конфигурация Поддерживает несколько доменов. Выбо`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 13`** (1 nodes): `Describe image via Groq vision API.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 14`** (1 nodes): `OCR image via tesseract.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 15`** (1 nodes): `Token count via tiktoken cl100k_base (shared by Claude & DeepSeek BPE).`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 16`** (1 nodes): `Drop oldest non-system messages to fit DeepSeek's 128K window.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 17`** (1 nodes): `Token count for a message including format overhead (~5 tok/msg).`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 18`** (1 nodes): `Try Groq vision → OCR → fallback placeholder.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 19`** (1 nodes): `Recursively replace image blocks with text descriptions (в т.ч. внутри tool_resu`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 20`** (1 nodes): `Compress 3+ newlines → 2, strip trailing spaces per line, strip edges.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 21`** (1 nodes): `True if message is exclusively tool_result/tool_use blocks.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 22`** (1 nodes): `Normalize whitespace, fix images, strip thinking, smart-truncate context.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 23`** (1 nodes): `Fix images (vision/OCR), strip thinking, truncate context for DeepSeek.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 24`** (1 nodes): `Try Groq vision → OCR → fallback placeholder.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 25`** (1 nodes): `Recursively replace image blocks with text descriptions (в т.ч. внутри tool_resu`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 26`** (1 nodes): `Fix images (vision/OCR), strip thinking, truncate context for DeepSeek.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 27`** (1 nodes): `Try Groq vision → OCR → fallback placeholder.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 28`** (1 nodes): `Fix images (vision/OCR), strip thinking, truncate context for DeepSeek.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 29`** (1 nodes): `Token count for a message including format overhead (~5 tok/msg).`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 30`** (1 nodes): `Try Groq vision → OCR → fallback placeholder.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 31`** (1 nodes): `Fix images (vision/OCR), strip thinking, truncate context for DeepSeek.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 32`** (1 nodes): `Toka estimate — ~4 chars/token, conservative for CJK/emoji.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 33`** (1 nodes): `Drop oldest non-system messages to fit DeepSeek's 128K window.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 34`** (1 nodes): `Try Groq vision → OCR → fallback placeholder.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 35`** (1 nodes): `Strip images and fix thinking blocks.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 36`** (1 nodes): `Forward SSE stream, unfiltered.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `save()` connect `Community 0` to `Community 8`, `Community 11`, `Community 4`, `Community 5`?**
  _High betweenness centrality (0.287) - this node is a cross-community bridge._
- **Why does `run()` connect `Community 0` to `Community 1`?**
  _High betweenness centrality (0.209) - this node is a cross-community bridge._
- **Why does `_ocr_describe()` connect `Community 1` to `Community 0`?**
  _High betweenness centrality (0.203) - this node is a cross-community bridge._
- **Are the 10 inferred relationships involving `save()` (e.g. with `run_top_rankd()` and `run()`) actually correct?**
  _`save()` has 10 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Describe image via Groq vision API.`, `OCR image via tesseract.`, `Token count via tiktoken cl100k_base (shared by Claude & DeepSeek BPE).` to the rest of the system?**
  _67 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Community 0` be split into smaller, more focused modules?**
  _Cohesion score 0.09 - nodes in this community are weakly interconnected._
- **Should `Community 1` be split into smaller, more focused modules?**
  _Cohesion score 0.12 - nodes in this community are weakly interconnected._