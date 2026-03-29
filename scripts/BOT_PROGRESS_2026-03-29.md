# Bot & SEO Progress — 2026-03-29

## Яндекс-боты (167.86.116.15)

- **Кол-во ботов увеличено: 191 → 300**
  - Создано 109 новых work-директорий (`work/bot_195..300` + заполнены пробелы)
  - `orchestrator.json` обновлён: 300 ботов, все enabled, пробелов нет
  - maxConcurrent: 8, сервер: Contabo 167.86.116.15
- Загружено **104 целевых запроса** kadastrmap (update-bot-queries.ts → kadastrmap_queries.txt)
- Боты на 3-м дне прогрева (warmup_days=3), через ~6 дней перейдут на target-режим

## Статьи kadastrmap (AI rewrite)

- **Batch 4 завершён** (25 статей, 12.4 мин):
  - gde-zakazat-kadastrovyj-pasport* (4 варианта)
  - kadastrovyj-pasport* (6 вариантов)
  - obremenenie/arest страницы (page-2 Google wins)
  - poluchit/zakazat-vypisku-iz-egrn* (5 вариантов)
  - kadastrovaya-stoimost, uznat-vladeltsa, spravka-ob-obremenenii
- **Итого улучшено: 136 статей** (батчи 1–4)
- Следующие батчи: только HIGH tier (~377 статей в очереди)

## SEO позиции (Keys.so, 2026-03-28)

- Загружено 58 запросов, все Яндекс = null (не в ТОП-100)
- Google: TOP-10 — "расположение" (#8), "кад. план квартиры" (#9), "справка об обременении" (#10)
- **Критические падения**: "5707" G#1→#28, "333098" G#2→#56 — нужна переработка
- AI-упоминаний: 1 (план фикса: FAQ-схемы + answer-first структура)

## Скрипты

- `scripts/search-metrics.ts` — Google opportunity scorer (gOpportunity 0–40)
- `scripts/import-positions.ts` — парсер Keys.so таблицы
- `scripts/score-articles.ts` — enhanced scoring: slug×10 + gOpportunity
- `scripts/batch-rewrite-4.ts` — batch 4 runner
- `scripts/update-bot-queries.ts` — деплой запросов на бот-сервер
