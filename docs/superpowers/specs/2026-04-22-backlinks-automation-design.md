# Backlinks Automation — Design Spec
**Date:** 2026-04-22  
**Project:** strategy-dashboard  
**Target site:** kadastrmap.info  
**Approach:** Playwright + Cookie Injection + RSS endpoint for Дзен

---

## 1. Overview

Automated SEO backlink publisher that generates Russian-language articles via Groq API and publishes them to Яндекс Дзен, Spark.ru, and Яндекс.Кью — all free platforms with high Yandex trust. Articles contain natural links to kadastrmap.info priority pages identified via GSC.

New tab `/backlinks` in strategy-dashboard. Manual trigger per item + cron schedule.

---

## 2. Priority Target Pages

Hard-coded queue, round-robin per platform:

```ts
const PRIORITY_PAGES = [
  { url: '/kadastr/raspolozhenie-po-kadastrovomu-nomeru/',           anchor: 'найти участок по кадастровому номеру' },
  { url: '/kadastr/kadastrovyj-nomer-po-adresu-obekta-nedvizhimosti/', anchor: 'кадастровый номер по адресу' },
  { url: '/kadastr/proverit-kvartiru-v-rosreestre-po-adresu-onlajn/', anchor: 'проверить квартиру в росреестре' },
  { url: '/kadastr/poluchit-vypisku-egrn-po-kadastrovomu-nomeru/',    anchor: 'получить выписку ЕГРН' },
  { url: '/kadastr/proverit-obremenenie-na-nedvizhimost/',            anchor: 'проверить обременение на недвижимость' },
]
```

Each platform cycles through all 5 pages independently.

---

## 3. Database Schema

Migration `0011_backlink_posts`:

```sql
CREATE TABLE backlink_posts (
  id           SERIAL PRIMARY KEY,
  platform     TEXT NOT NULL CHECK (platform IN ('dzen', 'spark', 'kw')),
  target_url   TEXT NOT NULL,
  anchor_text  TEXT NOT NULL,
  title        TEXT,
  article      TEXT,
  status       TEXT NOT NULL DEFAULT 'pending'
               CHECK (status IN ('pending','publishing','published','failed')),
  published_url TEXT,
  published_at  TIMESTAMP,
  error_msg    TEXT,
  created_at   TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_backlink_posts_platform_status
  ON backlink_posts(platform, status);
```

---

## 4. Content Generation

### Model
- Primary: Groq `llama-3.3-70b-versatile` (fast, cheap, good Russian)
- Fallback: Fireworks `accounts/fireworks/models/llama-v3p1-70b-instruct`

### Per-platform prompts

**Дзен** — 900–1200 words, informational, H2/H3 structure:
```
System: Ты SEO-автор, пишешь полезные статьи о недвижимости и кадастре для Яндекс Дзен.
Стиль: объясняю как эксперт, без воды. Структура: заголовок, 4-6 разделов H2,
вывод. Вставь ссылку [anchor](https://kadastrmap.info{target_url}) органично
в тело текста (не в конце). Только русский язык. Без markdown-кодов и HTML.

User: Напиши статью на тему "{title}". Объём 900-1200 слов.
```

**Spark** — 600–900 words, expert column:
```
System: Ты эксперт по недвижимости, пишешь экспертную колонку на Spark.ru.
Деловой практический стиль, минимум списков, больше объяснений.
Вставь ссылку органично. Только русский язык.

User: Напиши экспертную колонку "{title}". Объём 600-900 слов.
```

**Кью** — 200–350 words, answer to real question:
```
System: Ты эксперт по кадастру, отвечаешь на вопросы на Яндекс.Кью.
Дай развёрнутый практический ответ. Упомяни kadastrmap.info органично.
Только русский язык.

User: Напиши ответ на вопрос "{question}". Объём 200-350 слов.
```

### Anchor variation (anti-Минусинск)
Rotate anchors — exact match max 20% of posts per page:
```ts
const ANCHOR_VARIANTS: Record<string, string[]> = {
  '/raspolozhenie/': [
    'найти участок по кадастровому номеру',
    'узнать расположение участка',
    'где находится участок по номеру',
    'kadastrmap.info',
    'на этом сервисе',
  ],
  // ... other pages
}
```

---

## 5. Cookie Extractor

**File:** `server/publishers/extract-cookies.py`

Reads `/Users/evgenijgrudev/Library/Cookies/Cookies.binarycookies`, extracts cookies for domains:
- `.yandex.ru`, `.yandex.com`
- `.dzen.ru`, `.sso.dzen.ru`, `.passport.dzen.ru`
- `.spark.ru` (if present)

Outputs `.safari-cookies.json` (gitignored) in Playwright format:
```json
[
  { "name": "Session_id", "value": "...", "domain": ".yandex.ru", "path": "/", "httpOnly": true, "secure": true },
  { "name": "i", "value": "...", "domain": ".yandex.ru", "path": "/", "httpOnly": true, "secure": true }
]
```

**File:** `server/publishers/cookie-extractor.ts`
- Calls `python3 extract-cookies.py` via `execFileNoThrow('python3', ['extract-cookies.py'])`
  (uses project's safe execFile utility to avoid shell injection)
- Returns parsed cookie array
- Throws if `.safari-cookies.json` is older than 6 hours (force refresh)

---

## 6. Publishers

### Common interface
```ts
interface Publisher {
  publish(post: BacklinkPost): Promise<{ url: string }>
}
```

All publishers:
1. Call `cookieExtractor.get()` to load fresh cookies
2. Launch Playwright `chromium.launch({ headless: true })`
3. `context.addCookies(cookies)`
4. Navigate, fill content, submit
5. Wait for published URL, return it
6. On error: screenshot to `/tmp/backlinks-error-{platform}-{ts}.png`, throw

### dzen.ts
```
navigate → https://dzen.ru/editor/create-article
inject cookies
wait for editor to load
type title into title input
focus body editor → paste article via clipboard (Ctrl+V)
wait 2s for paste to settle
click "Опубликовать"
wait for URL → dzen.ru/a/...
return location.href
```

### spark.ts
```
navigate → https://spark.ru/post/new
inject cookies (Яндекс OAuth if no spark session)
fill title
paste body via clipboard
click Опубликовать
return published URL
```

### kw.ts
```
navigate → https://yandex.ru/q/search?text={encoded_topic}
inject yandex.ru cookies
find first question with < 3 answers
click question → click "Ответить"
paste answer (200-350 words)
submit
return question URL
```

Note: Яндекс.Кью posts use `article` field as the question topic; generator produces a short answer, not a long article.

---

## 7. RSS Endpoint

**Route:** `GET /rss/dzen` (public Express route, not tRPC)

Returns RSS 2.0 XML of last 20 published Дзен posts:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>kadastrmap.info — Кадастр и недвижимость</title>
    <link>https://kadastrmap.info</link>
    <description>Полезные статьи о кадастре и недвижимости</description>
    <language>ru</language>
    <item>
      <title>{post.title}</title>
      <link>{post.published_url}</link>
      <description>{first 500 chars of article}</description>
      <pubDate>{post.published_at RFC2822}</pubDate>
      <guid>{post.published_url}</guid>
    </item>
  </channel>
</rss>
```

Registered in `server/routers.ts` as plain Express route (needs `res.set('Content-Type', 'application/rss+xml')`).

**One-time setup:** Дзен Studio → Источники → RSS → вставить `https://{dashboard-host}/rss/dzen`.
After that Дзен auto-imports new articles even if Playwright fails.

---

## 8. tRPC Router — backlinks.ts

```ts
backlinksRouter = {
  getQueue:    protectedProcedure → BacklinkPost[]
  getStats:    protectedProcedure → { dzen: N, spark: N, kw: N, thisWeek: N }
  generate:    protectedProcedure({ platform, targetUrl? })
               // picks next unprocessed page for platform, calls Groq, inserts pending
  publish:     protectedProcedure({ id })
               // runs publisher, updates status + published_url
  publishNext: protectedProcedure({ platform })
               // publish first pending for platform
  retry:       protectedProcedure({ id })
               // reset failed → pending
  delete:      protectedProcedure({ id })
}
```

---

## 9. Frontend — Backlinks.tsx

Route: `/backlinks`

```
Stats bar: [Дзен: 12 ✓ | Spark: 5 ✓ | Кью: 8 ✓ | Эта неделя: 3]

Toolbar:
  Platform filter: [Все | Дзен | Spark | Кью]
  [+ Генерировать]  → modal: платформа + страница
  [▶ Опубликовать все pending]

Queue table:
  # | Платформа | Целевая страница | Заголовок | Статус | Создан | Действия

Status badges:
  ● pending    (yellow)
  ⟳ publishing (blue, spinner)
  ✓ published  (green + link icon)
  ✗ failed     (red + error tooltip + Retry)

Actions per row: [Publish] [→ URL] [Retry] [Delete]

Footer: RSS URL + copy button
```

---

## 10. Scheduler

Added to `server/articleScheduler.ts`:

```ts
// Дзен: every day at 10:00 MSK
cron.schedule('0 10 * * *',   () => publishNext('dzen'),  { timezone: 'Europe/Moscow' })

// Spark: Mon/Wed/Fri at 11:00 MSK
cron.schedule('0 11 * * 1,3,5', () => publishNext('spark'), { timezone: 'Europe/Moscow' })

// Кью: Mon/Thu at 12:00 MSK
cron.schedule('0 12 * * 1,4',  () => publishNext('kw'),   { timezone: 'Europe/Moscow' })
```

`publishNext(platform)`:
1. Find first `pending` for platform
2. Set status `publishing`
3. Run publisher
4. Success → `published` + save URL
5. Failure → `failed` + save error_msg + screenshot

---

## 11. File Map

### New files
```
server/routers/backlinks.ts
server/publishers/index.ts              ← publishNext + shared logic
server/publishers/cookie-extractor.ts
server/publishers/extract-cookies.py
server/publishers/dzen.ts
server/publishers/spark.ts
server/publishers/kw.ts
server/publishers/rss.ts
drizzle/0011_backlink_posts.sql
client/src/pages/Backlinks.tsx
```

### Modified files
```
server/routers.ts          ← +backlinksRouter, +GET /rss/dzen
server/articleScheduler.ts ← +3 cron jobs
client/src/App.tsx         ← +Route /backlinks
client/src/pages/Home.tsx  ← +nav link
.gitignore                 ← +.safari-cookies.json
```

### Dependencies
```bash
pnpm add playwright node-cron
npx playwright install chromium
```

---

## 12. Error Handling

| Scenario | Handling |
|----------|----------|
| Cookie file > 6h old | Auto-refresh before publish |
| Playwright timeout | Screenshot → `/tmp/`, status=failed |
| Groq error | Retry once with Fireworks, then fail |
| RSS empty | Returns valid XML with empty channel |
| Cron publish fails | Log + continue (non-fatal) |

---

## 13. Security

- `.safari-cookies.json` — gitignored, never committed
- Cookie extractor runs locally only, not on remote server
- `execFileNoThrow('python3', ['extract-cookies.py'])` — no shell interpolation
