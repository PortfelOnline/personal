# Graph Report - /Users/evgenijgrudev/personal  (2026-04-25)

## Corpus Check
- Corpus is ~9,286 words - fits in a single context window. You may not need a graph.

## Summary
- 67 nodes · 81 edges · 14 communities detected
- Extraction: 85% EXTRACTED · 15% INFERRED · 0% AMBIGUOUS · INFERRED: 12 edges (avg confidence: 0.8)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Config & Setup|Config & Setup]]
- [[_COMMUNITY_Data Models|Data Models]]
- [[_COMMUNITY_Auth Logic|Auth Logic]]
- [[_COMMUNITY_Scripts|Scripts]]
- [[_COMMUNITY_Utils|Utils]]
- [[_COMMUNITY_Tests|Tests]]
- [[_COMMUNITY_Docs|Docs]]
- [[_COMMUNITY_API|API]]
- [[_COMMUNITY_CLI|CLI]]
- [[_COMMUNITY_Storage|Storage]]
- [[_COMMUNITY_Events|Events]]
- [[_COMMUNITY_Helpers|Helpers]]
- [[_COMMUNITY_Types|Types]]
- [[_COMMUNITY_Entry Points|Entry Points]]

## God Nodes (most connected - your core abstractions)
1. `save()` - 12 edges
2. `init()` - 5 edges
3. `run_top_rankd()` - 5 edges
4. `main()` - 5 edges
5. `show()` - 4 edges
6. `run()` - 4 edges
7. `run()` - 4 edges
8. `create_account()` - 4 edges
9. `publish_article()` - 4 edges
10. `run()` - 4 edges

## Surprising Connections (you probably didn't know these)
- `run()` --calls--> `save()`  [INFERRED]
  /Users/evgenijgrudev/personal/backlinks/sites/disqus.py → /Users/evgenijgrudev/personal/backlinks/tracker.py
- `run()` --calls--> `save()`  [INFERRED]
  /Users/evgenijgrudev/personal/backlinks/sites/about_me.py → /Users/evgenijgrudev/personal/backlinks/tracker.py
- `run()` --calls--> `save()`  [INFERRED]
  /Users/evgenijgrudev/personal/backlinks/sites/quora.py → /Users/evgenijgrudev/personal/backlinks/tracker.py
- `run()` --calls--> `save()`  [INFERRED]
  /Users/evgenijgrudev/personal/backlinks/sites/folkd.py → /Users/evgenijgrudev/personal/backlinks/tracker.py
- `run()` --calls--> `save()`  [INFERRED]
  /Users/evgenijgrudev/personal/backlinks/sites/wikidot.py → /Users/evgenijgrudev/personal/backlinks/tracker.py

## Communities

### Community 0 - "Config & Setup"
Cohesion: 0.24
Nodes (8): Diigo — социальная закладка + профиль DA: 70, Do-Follow: YES (закладки индексиру, run(), init(), Трекер прогресса — сохраняет результаты в CSV, Создать файл с заголовками если не существует., Вывести текущий прогресс., save(), show()

### Community 1 - "Data Models"
Cohesion: 0.39
Nodes (7): api_post(), create_account(), publish_article(), Telegra.ph — публикация статьи без регистрации DA: 81, Do-Follow: Yes, Фаза 2, Создать анонимный аккаунт Telegraph., Опубликовать статью из файла, вернуть URL., run()

### Community 2 - "Auth Logic"
Cohesion: 0.43
Nodes (6): _get_done_sites(), main(), Вернуть набор уже обработанных платформ из CSV., Запустить топ-N do-follow платформ из Rankd через браузер (полу-авто)., run_site(), run_top_rankd()

### Community 3 - "Scripts"
Cohesion: 0.38
Nodes (6): NeoCities — регистрация + загрузка статьи через API DA: 83, Do-Follow: Yes, Фаза, Зарегистрировать аккаунт через браузер., Загрузить HTML страницу через API., register(), run(), upload_page()

### Community 4 - "Utils"
Cohesion: 0.47
Nodes (5): get_all_platform_urls(), main(), Scrape a single platform page and return structured data., Get all platform page URLs from the Rankd database., scrape_platform_page()

### Community 5 - "Tests"
Cohesion: 0.6
Nodes (4): get_user_id(), publish_article(), Medium.com — публикация статьи через API DA: 96, Do-Follow: YES (ссылки в тексте, run()

### Community 6 - "Docs"
Cohesion: 0.67
Nodes (3): main(), parse_rankd_text(), Parse raw text pasted from Rankd listing pages.

### Community 7 - "API"
Cohesion: 1.0
Nodes (2): main(), parse_table()

### Community 8 - "CLI"
Cohesion: 0.67
Nodes (2): Disqus — профиль с ссылкой на сайт DA: 93, Do-Follow: NO (но высокий авторитет д, run()

### Community 9 - "Storage"
Cohesion: 0.67
Nodes (2): About.me — профиль с ссылкой на сайт DA: 71, Do-Follow: YES, run()

### Community 10 - "Events"
Cohesion: 0.67
Nodes (2): Quora — профиль с ссылкой на сайт DA: 93, Do-Follow: YES (ссылки в профиле — do-, run()

### Community 11 - "Helpers"
Cohesion: 0.67
Nodes (2): Folkd.com — социальная закладка (bookmark) DA: 60, Do-Follow: YES, run()

### Community 12 - "Types"
Cohesion: 0.67
Nodes (2): Wikidot — регистрация + создание wiki-сайта со статьёй DA: 83, Do-Follow: Yes, Ф, run()

### Community 13 - "Entry Points"
Cohesion: 1.0
Nodes (1): Backlink Bot — мульти-сайтовая конфигурация Поддерживает несколько доменов. Выбо

## Knowledge Gaps
- **22 isolated node(s):** `Backlink Bot — мульти-сайтовая конфигурация Поддерживает несколько доменов. Выбо`, `Parse raw text pasted from Rankd listing pages.`, `Трекер прогресса — сохраняет результаты в CSV`, `Создать файл с заголовками если не существует.`, `Вывести текущий прогресс.` (+17 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `API`** (3 nodes): `main()`, `parse_table()`, `parse_rankd_table.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `CLI`** (3 nodes): `Disqus — профиль с ссылкой на сайт DA: 93, Do-Follow: NO (но высокий авторитет д`, `run()`, `disqus.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Storage`** (3 nodes): `About.me — профиль с ссылкой на сайт DA: 71, Do-Follow: YES`, `run()`, `about_me.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Events`** (3 nodes): `Quora — профиль с ссылкой на сайт DA: 93, Do-Follow: YES (ссылки в профиле — do-`, `run()`, `quora.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Helpers`** (3 nodes): `Folkd.com — социальная закладка (bookmark) DA: 60, Do-Follow: YES`, `run()`, `folkd.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Types`** (3 nodes): `wikidot.py`, `Wikidot — регистрация + создание wiki-сайта со статьёй DA: 83, Do-Follow: Yes, Ф`, `run()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Entry Points`** (2 nodes): `config.py`, `Backlink Bot — мульти-сайтовая конфигурация Поддерживает несколько доменов. Выбо`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `save()` connect `Config & Setup` to `Data Models`, `Auth Logic`, `Scripts`, `Tests`, `CLI`, `Storage`, `Events`, `Helpers`, `Types`?**
  _High betweenness centrality (0.528) - this node is a cross-community bridge._
- **Why does `run()` connect `Data Models` to `Config & Setup`?**
  _High betweenness centrality (0.144) - this node is a cross-community bridge._
- **Why does `run()` connect `Scripts` to `Config & Setup`?**
  _High betweenness centrality (0.127) - this node is a cross-community bridge._
- **Are the 10 inferred relationships involving `save()` (e.g. with `run_top_rankd()` and `run()`) actually correct?**
  _`save()` has 10 INFERRED edges - model-reasoned connections that need verification._
- **Are the 2 inferred relationships involving `main()` (e.g. with `init()` and `show()`) actually correct?**
  _`main()` has 2 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Backlink Bot — мульти-сайтовая конфигурация Поддерживает несколько доменов. Выбо`, `Parse raw text pasted from Rankd listing pages.`, `Трекер прогресса — сохраняет результаты в CSV` to the rest of the system?**
  _22 weakly-connected nodes found - possible documentation gaps or missing edges._