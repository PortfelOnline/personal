# GMA: автоматизация контента для get-my-agent.com/en/ (2026-07-04)

Цель: регулярный контент без ручной рутины. Статьи уже на автомате (`gma-blog-nightly.ts`, cron 03:40, 2/ночь).

## Контур 1 — FB+IG, полный автомат (сервер n)

- **Скрипт**: расширить `/opt/n/apps/strategy-dashboard/scripts/gma-social.ts`
  - Чередование по дню месяца: нечётный → виральный пост (как сейчас: конкурентный майнинг, гейт ≥55, CF FLUX 1080²); чётный → **анонс свежей статьи** (последний пост WP cat 44: LLM пишет хук-тизер + ссылка `https://get-my-agent.com/en/{slug}/`, картинка = featured-обложка статьи).
  - Флаг `--announce` / `--viral` для ручного форса.
- **Cron root@n**: `0 5 * * *` UTC (= 10:30 IST, утренний пик Индии), лог `/root/logs/gma-social.log`.
- **Алерты**: при фейле — TG через бот AI Leads (`GMA_TG_BOT_TOKEN`, chat `109733868`), как в watchdog.
- **Риск**: IG publish может требовать App Review приложения `2254012428421174` на `instagram_content_publish`. Первый прогон руками; если 403 — публикуем FB-only + TG-алерт, IG чиним отдельно.

## Контур 2 — YouTube Shorts, полуавтомат (Mac, 2–3/нед)

Скрипт-сценарий, запуск по команде в Claude Code (Mac должен быть включён):

1. **Тема + метаданные**: LLM — тема (виральность-гейт ≥55) → Flow-промпт (реюз `generateFlowPrompt`, ViralCraft) + YT title/description/tags с CTA на `/en/`.
2. **Видео**: superpowers-chrome → labs.google/flow → ввод промпта → генерация → скачать MP4 (сессия Google жива, профиль персистентный).
3. **Постобработка**: ffmpeg локально — 1080×1920 + нижняя плашка (код ViralCraft `/api/video/overlay`: drawbox + drawtext, DejaVuSans-Bold).
4. **Заливка**: YouTube Studio в том же браузере (shadow DOM гочи задокументированы в памяти) → Shorts publish.
5. **Бонус**: тот же ролик → IG Reels через Graph API (`media_type=REELS`, видео-URL из WP uploads).

Fallback, если Flow UI хрупкий: Veo через Gemini API (content_factory, 3 видео/день бесплатно) + YouTube Data API upload.

## Решения

- Формат YT: вертикальные Shorts 1080×1920.
- Частота: FB+IG 1 пост/день, YT 2–3/нед.
- Заливка YT: Studio UI (без OAuth-сетапа); Data API — потом при необходимости.
- Контент FB+IG: микс виральные/анонсы статей.

## Порядок работ

1. Этап 1: gma-social.ts announce-режим → dry-run → live-тест FB+IG → cron + TG-алерт.
2. Этап 2: YT-пайплайн (метаданные-генератор → Flow UI → ffmpeg → Studio upload → IG Reels).

## Реализовано 2026-07-04 (оба этапа)

- **Этап 1 ✅**: cron `0 8 * * *` MSK на n; live-пост FB `122116748343023644` + IG `18051342902540051` (App Review не потребовался). Попутно починен nightly-баг Polylang (пост с двумя языками → категория 44→42, статьи выпадали из /en/blog-en/) + бэкфилл 3 статей и 2 обложек. 🚨 Meta-фетчеры не достают сайт за прокси: FB — бинарная загрузка, IG — weserv.
- **Этап 2 ✅**: конвейер прогнан end-to-end — YT Shorts https://youtube.com/shorts/ZRYmndaPp_Y + IG Reels `18100047650605095`. Скрипты: `gma-shorts-meta.ts`, `gma-reels.ts` (n), `~/gma-shorts/{overlay.sh,plashka.html}` (Mac). **Runbook: `~/gma-shorts/RUNBOOK.md`** — запуск по команде «сделай шорт». Плашка = HTML→headless-Chrome PNG→ffmpeg overlay (drawtext в Mac-ffmpeg отсутствует).
