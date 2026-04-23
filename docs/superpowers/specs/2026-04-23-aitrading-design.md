# AiTrading — Design Spec
**Date:** 2026-04-23  
**Status:** Approved

## Overview

Personal Binance trading bot accessible via Telegram with full trade analytics displayed in the strategy-dashboard. The bot executes spot and futures orders via natural language commands in Russian/English, asks clarifying questions before execution, records all trades to a shared SQLite database, and auto-pulls trade history from Binance API.

## Repositories

- **Bot:** `PortfelOnline/aitrading` — standalone Node.js/TypeScript service
- **Dashboard:** `strategy-dashboard` — new `/aitrading` page + tRPC router + shared Drizzle schema

## Architecture

```
aitrading repo (Telegram Bot)          strategy-dashboard
┌──────────────────────────┐          ┌──────────────────────┐
│ grammy (Telegram)        │          │ /aitrading React page│
│ Claude Haiku (NLP)       │  shared  │ tRPC aitrading router│
│ @binance/connector       │◄──SQLite─►│ Drizzle ORM (read)  │
│ Drizzle ORM (read+write) │          └──────────────────────┘
└──────────────────────────┘
```

Both services share a single SQLite file. The bot owns writes; the dashboard reads only.

## Database Schema (new Drizzle tables)

### `trades`
| Column | Type | Notes |
|---|---|---|
| id | integer PK | autoincrement |
| symbol | text | e.g. "BTCUSDT" |
| side | text | "BUY" or "SELL" |
| market_type | text | "SPOT" or "FUTURES" |
| qty | real | asset quantity |
| price | real | fill price |
| usdt_value | real | qty × price |
| leverage | integer | 1 for spot |
| binance_order_id | text | unique |
| pnl_usdt | real | null while open |
| pnl_pct | real | null while open |
| status | text | "OPEN" or "CLOSED" |
| opened_at | integer | unix timestamp |
| closed_at | integer | null while open |

### `binance_config`
| Column | Type | Notes |
|---|---|---|
| id | integer PK | single row |
| api_key | text | plaintext |
| api_secret | text | plaintext (local-only, personal bot) |
| testnet | integer | 0 or 1 |
| created_at | integer | unix timestamp |

## Telegram Bot

### Setup Flow (`/start`)
1. Bot asks for Binance API Key
2. Bot asks for Binance API Secret
3. Bot tests connectivity (GET /api/v3/account)
4. Stores in `binance_config`

### Trade Flow (natural language)
```
User: "купи биткоин"
Bot:  "Спот или фьючерс?"         → User: "спот"
Bot:  "На сколько USDT?"           → User: "200"
Bot:  "Подтвердить покупку BTC 
       на 200 USDT по рынку?
       💰 Текущая цена: ~95,000 $
       ✅ Да  ❌ Отмена"
       → User: ✅
Bot:  "✅ Куплено 0.00210 BTC по $95,238
       Ордер #12345678"
```

### Commands
| Command | Description |
|---|---|
| `/start` | Настройка API ключей |
| `/positions` | Открытые позиции + нереализованный P&L |
| `/stats` | Общая статистика (total P&L, win rate, count) |
| `/history` | Последние 20 сделок |
| `/sync` | Принудительная синхронизация истории с Binance |
| Свободный текст | NLP → торговая команда |

### NLP (Claude Haiku)
Prompt extracts structured intent from user message:
```json
{ "action": "buy|sell|close|cancel", "asset": "BTC|ETH|...", 
  "qty": null|number, "usdt": null|number, "market": null|"spot"|"futures" }
```
Missing fields trigger clarifying questions one by one.

### Binance Execution
- **Spot buy:** `POST /api/v3/order` — `MARKET` order, `quoteOrderQty=usdt_value`
- **Spot sell:** `POST /api/v3/order` — `MARKET` order, `quantity=qty`
- **Futures long:** `POST /fapi/v1/order` — `MARKET`, `side=BUY`
- **Futures short:** `POST /fapi/v1/order` — `MARKET`, `side=SELL`

### Auto-sync
Cron every 5 minutes: pulls `/api/v3/myTrades` (spot) + `/fapi/v1/userTrades` (futures), upserts into `trades` table, calculates P&L for closed positions.

## Dashboard `/aitrading`

### Components
1. **Stats cards row** — Total P&L (USDT), Win Rate (%), Total trades, Best trade
2. **Open Positions table** — Symbol, Side, Entry price, Current price, Unrealized P&L (%), Market type
3. **P&L Chart** — LineChart (recharts) — cumulative P&L over time by day
4. **Trade History table** — filterable by symbol/type, sortable, paginated (20/page)
5. **Sync button** — triggers `/api/aitrading/sync` to force pull from Binance

### Data flow
- Dashboard tRPC router reads from shared SQLite via Drizzle (read-only)
- Open positions: live price from Binance REST API (called server-side)
- Refreshes every 30s via TanStack Query

## Tech Stack

| Layer | Technology |
|---|---|
| Bot framework | grammy v2 |
| Binance | @binance/connector-typescript |
| NLP | Claude Haiku (claude-haiku-4-5) via Anthropic SDK |
| ORM | drizzle-orm (shared schema) |
| Database | SQLite (shared file) |
| Dashboard | React + recharts + shadcn/ui (existing) |
| API | tRPC (existing pattern) |

## File Structure

### `aitrading` repo
```
src/
  index.ts          — bot entry point
  bot.ts            — grammy bot setup + command handlers
  nlp.ts            — Claude Haiku NLP parser
  binance.ts        — Binance API wrapper (spot + futures)
  sync.ts           — auto-sync cron job
  db.ts             — Drizzle connection (points to shared SQLite)
  schema.ts         — imports shared schema
.env                — TELEGRAM_TOKEN, ANTHROPIC_API_KEY, DB_PATH
```

### `strategy-dashboard` additions
```
drizzle/
  migrations/       — new migration for trades + binance_config tables
shared/
  schema/
    aitrading.ts    — trades + binance_config table definitions
server/routers/
  aitrading.ts      — tRPC router: stats, positions, history, sync
client/src/pages/
  AiTrading.tsx     — main dashboard page
client/src/components/aitrading/
  StatsCards.tsx
  OpenPositions.tsx
  PnlChart.tsx
  TradeHistory.tsx
```

## Error Handling

- Binance API errors → bot sends human-readable error message (e.g. "Недостаточно USDT на балансе")
- NLP parse failure → bot asks to rephrase ("Не понял, попробуй: 'купи ETH на 100 USDT'")
- Network timeout → retry once, then notify user
- No API keys configured → redirect to `/start`

## Out of Scope (v1)

- Stop-loss / take-profit orders
- Multi-user support (personal bot, single API key)
- Portfolio rebalancing
- Price alerts
- Order book / limit orders (market orders only in v1)
