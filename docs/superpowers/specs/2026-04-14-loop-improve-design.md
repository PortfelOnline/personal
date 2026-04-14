# loop-improve: Continuous Article Improvement Loop

**Date:** 2026-04-14  
**Goal:** Infinite 24/7 loop that improves kadastrmap.info articles to beat top-3 in Google + Yandex.

## Architecture

Single script: `scripts/loop-improve.ts`  
State file: `scripts/loop-state.json` (persists across restarts)

## Priority Queue

Each round, all 1612 published posts are fetched from WP API and scored:

```
score = freq_boost × commercial_weight × gap_penalty

freq_boost     = freq from positions.json match (slug ↔ query), default 1
commercial_weight:
  HIGH (3) — заказ/выписка/справка/zakazat/spravka/poluchit
  MED  (2) — проверить/обременение/арест/залог/собственник
  LOW  (1) — всё остальное
  SKIP (0) — карта/karta/besplatno/gosuslugi/mfc → пропускать

gap_penalty = max(google_gap, yandex_gap)
  google_gap  = positions.json google pos, fallback 50
  yandex_gap  = positions.json yandex pos, fallback 50
```

Articles with `lastImproved < 30 days ago` are skipped entirely (cooldown).

## Per-Article Logic

```
1. Parse our article → wordCount, faqCount, h2Count (от WP API, быстро)
2. extractKeyword(title) → keyword
3. fetchGoogleSerp(keyword) + fetchYandexSerp(keyword) [параллельно, cached]
4. findOurPos(googleSerp) → googlePos
5. findOurPos(yandexSerp) → yandexPos
6. fetchCompetitorArticles(mergedSerp, 3) → top3 metrics
7. Compute need_rewrite:
   - googlePos > 3 AND googlePos != null  → true
   - yandexPos > 3 AND yandexPos != null  → true
   - our.words < top1.words × 0.9         → true
   - our.faqCount < top1.faqCount         → true
   - both positions null (not ranked)      → true (rewrite)
   - ALL thresholds met                   → false (SKIP)
8. If need_rewrite → rewriteArticle(userId, url) [existing function]
9. Save state: { lastChecked, lastImproved?, skipReason?, googlePos, yandexPos }
10. Cooldown 5s between articles
```

## State File Format

```json
{
  "https://kadastrmap.info/kadastr/slug/": {
    "lastChecked": "2026-04-14T10:00:00Z",
    "lastImproved": "2026-04-14T10:00:00Z",
    "googlePos": 7,
    "yandexPos": 12,
    "skipReason": null
  }
}
```

## Loop Structure

```
Round N:
  1. Fetch all posts from WP API
  2. Score + sort (exclude cooldown articles)
  3. Process each article (check → skip or rewrite)
  4. Log round summary
  5. If all articles on cooldown → sleep 1h, then start next round
  6. Else → start next round immediately (cooldown articles naturally filtered)
```

## Logging

```
[loop] === Round 1 started — 1612 posts, 847 eligible ===
[loop] [1/847] кадастровый паспорт на квартиру | G:36 Y:54 | 2100w/8faq → REWRITE
[loop] [2/847] расположение по кадастровому номеру | G:7 Y:null | 4200w/14faq → SKIP (G top-3, metrics ok)
[loop] [3/847] как снять обременение | G:null Y:null | 1800w/5faq → REWRITE
[loop] === Round 1 done — rewritten: 312, skipped: 535, errors: 0 — 4h 12m ===
```

## Graceful Shutdown

`SIGINT` / `SIGTERM` → sets `stopped=true` → finishes current article → saves state → exits.

## Usage

```bash
# Start
nohup npx tsx scripts/loop-improve.ts >> /tmp/loop-improve.log 2>&1 &

# Monitor
tail -f /tmp/loop-improve.log

# Stop gracefully
kill -SIGINT <pid>
```

## Key Decisions

- **No separate audit step** — SERP is fetched once, used for both position check AND rewrite context
- **30-day cooldown** — prevents over-churning articles that were recently improved
- **SKIP (score=0) articles** — карта/karta/besplatno never rewritten (no commercial intent)
- **positions.json boost** — articles with known high-freq queries get priority in each round
- **Reuses `rewriteArticle()`** — all rewrite logic stays in one place
