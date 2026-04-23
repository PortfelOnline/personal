# AiTrading Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a personal Telegram trading bot that executes Binance spot/futures orders via natural language, records all trades to SQLite, and displays full P&L analytics in the strategy-dashboard at /aitrading.

**Architecture:** Bot lives in `~/dev/aitrading/` (PortfelOnline/aitrading repo), writes to `~/dev/aitrading/trading.db` (SQLite). strategy-dashboard reads the same file via `better-sqlite3`. No inter-service HTTP needed.

**Tech Stack:** grammy + @grammyjs/conversations (Telegram), @anthropic-ai/sdk Claude Haiku (NLP), Node.js crypto (Binance HMAC signing), better-sqlite3 + drizzle-orm/better-sqlite3 (DB), recharts (charts), tRPC (dashboard API)

---

## Task 1: Set up aitrading repo

**Files:**
- Create: `~/dev/aitrading/package.json`
- Create: `~/dev/aitrading/tsconfig.json`
- Create: `~/dev/aitrading/.env.example`
- Create: `~/dev/aitrading/src/index.ts`

- [ ] **Step 1: Clone and set up repo**

```bash
cd ~/dev
git clone https://github.com/PortfelOnline/aitrading.git
cd aitrading
```

- [ ] **Step 2: Create package.json**

```json
{
  "name": "aitrading",
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "dev": "tsx watch src/index.ts",
    "start": "tsx src/index.ts",
    "build": "tsc"
  },
  "dependencies": {
    "grammy": "^1.31.0",
    "@grammyjs/conversations": "^2.0.0",
    "@anthropic-ai/sdk": "^0.39.0",
    "better-sqlite3": "^11.9.1",
    "drizzle-orm": "^0.44.5",
    "dotenv": "^16.5.0",
    "node-cron": "^3.0.3"
  },
  "devDependencies": {
    "@types/better-sqlite3": "^7.6.13",
    "@types/node": "^22.0.0",
    "@types/node-cron": "^3.0.11",
    "tsx": "^4.19.2",
    "typescript": "^5.7.3"
  }
}
```

Save as `package.json`, then run `npm install`.

- [ ] **Step 3: Create tsconfig.json**

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "ESNext",
    "moduleResolution": "bundler",
    "strict": true,
    "outDir": "dist",
    "rootDir": "src",
    "esModuleInterop": true
  },
  "include": ["src/**/*"]
}
```

- [ ] **Step 4: Create .env**

```
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
ANTHROPIC_API_KEY=your_anthropic_api_key
TRADING_DB_PATH=./trading.db
```

Save as `.env` and fill in real values.

- [ ] **Step 5: Create src/index.ts**

```typescript
import "dotenv/config";
import { startBot } from "./bot.js";
import { startSync } from "./sync.js";

async function main() {
  await startBot();
  startSync();
}

main().catch(console.error);
```

- [ ] **Step 6: Commit**

```bash
git add .
git commit -m "feat: init aitrading bot project"
```

---

## Task 2: SQLite database schema

**Files:**
- Create: `~/dev/aitrading/src/schema.ts`
- Create: `~/dev/aitrading/src/db.ts`

- [ ] **Step 1: Create schema.ts**

```typescript
import { integer, real, sqliteTable, text } from "drizzle-orm/sqlite-core";

export const trades = sqliteTable("trades", {
  id: integer("id").primaryKey({ autoIncrement: true }),
  symbol: text("symbol").notNull(),
  side: text("side").notNull(),              // "BUY" | "SELL"
  marketType: text("market_type").notNull(), // "SPOT" | "FUTURES"
  qty: real("qty").notNull(),
  price: real("price").notNull(),
  usdtValue: real("usdt_value").notNull(),
  leverage: integer("leverage").notNull().default(1),
  binanceOrderId: text("binance_order_id").unique(),
  pnlUsdt: real("pnl_usdt"),
  pnlPct: real("pnl_pct"),
  status: text("status").notNull().default("OPEN"),
  openedAt: integer("opened_at").notNull(),
  closedAt: integer("closed_at"),
});

export const binanceConfig = sqliteTable("binance_config", {
  id: integer("id").primaryKey({ autoIncrement: true }),
  apiKey: text("api_key").notNull(),
  apiSecret: text("api_secret").notNull(),
  testnet: integer("testnet", { mode: "boolean" }).notNull().default(false),
  createdAt: integer("created_at").notNull(),
});

export type Trade = typeof trades.$inferSelect;
export type NewTrade = typeof trades.$inferInsert;
export type BinanceConfig = typeof binanceConfig.$inferSelect;
```

- [ ] **Step 2: Create db.ts**

```typescript
import Database from "better-sqlite3";
import { drizzle } from "drizzle-orm/better-sqlite3";
import { eq, desc } from "drizzle-orm";
import { mkdirSync } from "fs";
import { dirname, resolve } from "path";
import * as schema from "./schema.js";

const DB_PATH = resolve(process.env.TRADING_DB_PATH ?? "./trading.db");
mkdirSync(dirname(DB_PATH), { recursive: true });

const sqlite = new Database(DB_PATH);
sqlite.pragma("journal_mode = WAL");
sqlite.pragma("foreign_keys = ON");

export const db = drizzle(sqlite, { schema });

// Initialize tables on startup using individual prepared statements
sqlite.prepare(`CREATE TABLE IF NOT EXISTS trades (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  symbol TEXT NOT NULL,
  side TEXT NOT NULL,
  market_type TEXT NOT NULL,
  qty REAL NOT NULL,
  price REAL NOT NULL,
  usdt_value REAL NOT NULL,
  leverage INTEGER NOT NULL DEFAULT 1,
  binance_order_id TEXT UNIQUE,
  pnl_usdt REAL,
  pnl_pct REAL,
  status TEXT NOT NULL DEFAULT 'OPEN',
  opened_at INTEGER NOT NULL,
  closed_at INTEGER
)`).run();

sqlite.prepare(`CREATE TABLE IF NOT EXISTS binance_config (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  api_key TEXT NOT NULL,
  api_secret TEXT NOT NULL,
  testnet INTEGER NOT NULL DEFAULT 0,
  created_at INTEGER NOT NULL
)`).run();

export function getConfig(): schema.BinanceConfig | undefined {
  return db.select().from(schema.binanceConfig).limit(1).all()[0];
}

export function saveConfig(apiKey: string, apiSecret: string, testnet = false) {
  db.delete(schema.binanceConfig).run();
  db.insert(schema.binanceConfig).values({
    apiKey,
    apiSecret,
    testnet,
    createdAt: Date.now(),
  }).run();
}

export function insertTrade(trade: schema.NewTrade): schema.Trade {
  return db.insert(schema.trades).values(trade).returning().all()[0];
}

export function getOpenTrades(): schema.Trade[] {
  return db.select().from(schema.trades)
    .where(eq(schema.trades.status, "OPEN"))
    .all();
}

export function getAllTrades(limit = 50): schema.Trade[] {
  return db.select().from(schema.trades)
    .orderBy(desc(schema.trades.openedAt))
    .limit(limit)
    .all();
}

export function upsertTradeByOrderId(trade: schema.NewTrade) {
  db.insert(schema.trades).values(trade)
    .onConflictDoUpdate({
      target: schema.trades.binanceOrderId,
      set: {
        price: trade.price,
        qty: trade.qty,
        usdtValue: trade.usdtValue,
        status: trade.status ?? "OPEN",
        pnlUsdt: trade.pnlUsdt,
        pnlPct: trade.pnlPct,
        closedAt: trade.closedAt,
      },
    }).run();
}
```

- [ ] **Step 3: Commit**

```bash
git add src/schema.ts src/db.ts
git commit -m "feat: sqlite schema — trades + binance_config"
```

---

## Task 3: Binance API wrapper

**Files:**
- Create: `~/dev/aitrading/src/binance.ts`

- [ ] **Step 1: Create binance.ts**

```typescript
import crypto from "crypto";
import { getConfig, saveConfig, db } from "./db.js";
import { binanceConfig as configTable } from "./schema.js";

function hmac256(data: string, secret: string): string {
  return crypto.createHmac("sha256", secret).update(data).digest("hex");
}

function baseUrl(futures: boolean, testnet: boolean): string {
  if (testnet) {
    return futures
      ? "https://testnet.binancefuture.com"
      : "https://testnet.binance.vision";
  }
  return futures ? "https://fapi.binance.com" : "https://api.binance.com";
}

async function binanceRequest(
  method: "GET" | "POST" | "DELETE",
  path: string,
  params: Record<string, string | number | boolean>,
  futures = false,
  signed = true
): Promise<any> {
  const cfg = getConfig();
  if (!cfg) throw new Error("Binance API не настроен. Запусти /start");

  const base = baseUrl(futures, cfg.testnet);
  const allParams = signed
    ? { ...params, timestamp: Date.now(), recvWindow: 5000 }
    : params;
  const qs = new URLSearchParams(
    Object.entries(allParams).map(([k, v]) => [k, String(v)])
  ).toString();

  const finalQs = signed ? `${qs}&signature=${hmac256(qs, cfg.apiSecret)}` : qs;
  const url = method === "GET" ? `${base}${path}?${finalQs}` : `${base}${path}`;

  const res = await fetch(url, {
    method,
    headers: {
      "X-MBX-APIKEY": cfg.apiKey,
      ...(method !== "GET" ? { "Content-Type": "application/x-www-form-urlencoded" } : {}),
    },
    body: method !== "GET" ? finalQs : undefined,
  });

  const data: any = await res.json();
  if (!res.ok) throw new Error(`Binance ${data.code}: ${data.msg}`);
  return data;
}

export async function testConnectivity(apiKey: string, apiSecret: string): Promise<boolean> {
  // Temporarily save creds, test, restore original if fail
  const original = getConfig();
  saveConfig(apiKey, apiSecret, false);
  try {
    await binanceRequest("GET", "/api/v3/account", {}, false, true);
    return true;
  } catch {
    db.delete(configTable).run();
    if (original) saveConfig(original.apiKey, original.apiSecret, original.testnet);
    return false;
  }
}

export async function spotBuy(symbol: string, quoteQty: number) {
  return binanceRequest("POST", "/api/v3/order", {
    symbol, side: "BUY", type: "MARKET", quoteOrderQty: quoteQty,
  });
}

export async function spotSell(symbol: string, quantity: number) {
  return binanceRequest("POST", "/api/v3/order", {
    symbol, side: "SELL", type: "MARKET", quantity,
  });
}

export async function futuresBuy(symbol: string, quantity: number, leverage = 10) {
  await binanceRequest("POST", "/fapi/v1/leverage", { symbol, leverage }, true);
  return binanceRequest("POST", "/fapi/v1/order", {
    symbol, side: "BUY", type: "MARKET", quantity,
  }, true);
}

export async function futuresSell(symbol: string, quantity: number, leverage = 10) {
  await binanceRequest("POST", "/fapi/v1/leverage", { symbol, leverage }, true);
  return binanceRequest("POST", "/fapi/v1/order", {
    symbol, side: "SELL", type: "MARKET", quantity,
  }, true);
}

export async function getPrice(symbol: string): Promise<number> {
  const data = await binanceRequest("GET", "/api/v3/ticker/price", { symbol }, false, false);
  return parseFloat(data.price);
}

export async function getSpotHistory(symbol: string, limit = 100): Promise<any[]> {
  return binanceRequest("GET", "/api/v3/myTrades", { symbol, limit }, false);
}

export async function getFuturesHistory(symbol: string, limit = 100): Promise<any[]> {
  return binanceRequest("GET", "/fapi/v1/userTrades", { symbol, limit }, true);
}

export function normalizeSymbol(raw: string): string {
  const s = raw.toUpperCase().trim();
  if (/USDT$|BUSD$|BTC$|ETH$/.test(s)) return s;
  return `${s}USDT`;
}

export const COIN_MAP: Record<string, string> = {
  биткоин: "BTC", bitcoin: "BTC", btc: "BTC",
  эфир: "ETH", ethereum: "ETH", eth: "ETH",
  солана: "SOL", solana: "SOL", sol: "SOL",
  доджкоин: "DOGE", doge: "DOGE", dogecoin: "DOGE",
  рипл: "XRP", xrp: "XRP", ripple: "XRP",
  bnb: "BNB", авакс: "AVAX", avax: "AVAX",
  ада: "ADA", ada: "ADA", cardano: "ADA",
  dot: "DOT", link: "LINK", ltc: "LTC",
  трон: "TRX", trx: "TRX", матик: "MATIC", matic: "MATIC",
};
```

- [ ] **Step 2: Commit**

```bash
git add src/binance.ts
git commit -m "feat: binance api wrapper — spot + futures market orders"
```

---

## Task 4: Claude Haiku NLP parser

**Files:**
- Create: `~/dev/aitrading/src/nlp.ts`

- [ ] **Step 1: Create nlp.ts**

```typescript
import Anthropic from "@anthropic-ai/sdk";
import { COIN_MAP } from "./binance.js";

const client = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });

export interface TradeIntent {
  action: "buy" | "sell" | null;
  asset: string | null;
  qty: number | null;
  usdt: number | null;
  market: "spot" | "futures" | null;
  leverage: number | null;
}

const NLP_SYSTEM = `You are a Binance trading intent parser. Extract trading intent from user messages in Russian or English.
Return ONLY valid JSON:
{
  "action": "buy" | "sell" | null,
  "asset": "<COIN_SYMBOL_UPPERCASE>" | null,
  "qty": <number or null>,
  "usdt": <number or null>,
  "market": "spot" | "futures" | null,
  "leverage": <number or null>
}
Rules:
- "купи"/"buy"/"лонг"/"long" → action: "buy"
- "продай"/"sell"/"шорт"/"short" → action: "sell"
- "фьючерс"/"futures"/"futures" → market: "futures"; "спот"/"spot" → market: "spot"
- Extract coin symbols: биткоин→BTC, эфир→ETH, солана→SOL, etc.
- If amount is in USDT (e.g. "на 200 USDT", "for 500$") → usdt field
- If amount is in coins (e.g. "0.01 BTC") → qty field
- Leverage: "x10", "плечо 20" → leverage field
Never return anything except the JSON object.`;

export async function parseIntent(message: string): Promise<TradeIntent> {
  const lower = message.toLowerCase();
  let detectedAsset: string | null = null;
  for (const [kw, sym] of Object.entries(COIN_MAP)) {
    if (lower.includes(kw)) { detectedAsset = sym; break; }
  }

  try {
    const resp = await client.messages.create({
      model: "claude-haiku-4-5-20251001",
      max_tokens: 150,
      system: NLP_SYSTEM,
      messages: [{ role: "user", content: message }],
    });
    const text = resp.content[0].type === "text" ? resp.content[0].text.trim() : "{}";
    const parsed = JSON.parse(text) as TradeIntent;
    if (!parsed.asset && detectedAsset) parsed.asset = detectedAsset;
    return parsed;
  } catch {
    return { action: null, asset: detectedAsset, qty: null, usdt: null, market: null, leverage: null };
  }
}

export function isTradeMessage(text: string): boolean {
  const KEYWORDS = [
    "купи", "продай", "buy", "sell", "шорт", "лонг",
    "short", "long", "открой", "закрой", "close", "open",
  ];
  const lower = text.toLowerCase();
  return KEYWORDS.some(kw => lower.includes(kw));
}
```

- [ ] **Step 2: Commit**

```bash
git add src/nlp.ts
git commit -m "feat: claude haiku nlp parser for trade intents"
```

---

## Task 5: Grammy bot + /start command

**Files:**
- Create: `~/dev/aitrading/src/handlers/start.ts`
- Create: `~/dev/aitrading/src/bot.ts`

- [ ] **Step 1: Create src/handlers/start.ts**

```typescript
import type { Conversation, ConversationFlavor } from "@grammyjs/conversations";
import type { Context } from "grammy";
import { getConfig, saveConfig } from "../db.js";
import { testConnectivity } from "../binance.js";

type MyCtx = Context & ConversationFlavor;

export async function startConversation(
  conversation: Conversation<MyCtx>,
  ctx: MyCtx
) {
  const hasConfig = !!getConfig();

  await ctx.reply(
    hasConfig
      ? "⚙️ API ключи уже настроены. Введи новый API Key для обновления (или /cancel):"
      : "👋 Добро пожаловать!\n\n📌 Нужны Binance API ключи.\nBinance → Управление API → Создать API\nПрава: Spot Trading + Futures\n\nВведи API Key:"
  );

  const keyMsg = await conversation.wait();
  const apiKey = keyMsg.message?.text?.trim() ?? "";
  if (!apiKey || apiKey.startsWith("/")) { await ctx.reply("❌ Отменено."); return; }

  await ctx.reply("Введи API Secret:");
  const secretMsg = await conversation.wait();
  const apiSecret = secretMsg.message?.text?.trim() ?? "";
  if (!apiSecret || apiSecret.startsWith("/")) { await ctx.reply("❌ Отменено."); return; }

  await ctx.reply("🔄 Проверяю подключение...");
  const ok = await testConnectivity(apiKey, apiSecret);

  if (!ok) {
    await ctx.reply("❌ Не удалось подключиться. Проверь ключи и повтори /start");
    return;
  }

  saveConfig(apiKey, apiSecret);
  await ctx.reply(
    "✅ Binance подключён!\n\n" +
    "Торгуй текстом:\n" +
    "• «купи биткоин на 100 USDT»\n" +
    "• «продай 0.01 ETH на споте»\n" +
    "• «открой шорт BTC x10 на фьючерсах»\n\n" +
    "/positions — открытые позиции\n" +
    "/stats — статистика\n" +
    "/history — история сделок\n" +
    "/sync — синхронизировать с Binance"
  );
}
```

- [ ] **Step 2: Create src/bot.ts**

```typescript
import { Bot, session } from "grammy";
import { conversations, createConversation } from "@grammyjs/conversations";
import type { ConversationFlavor } from "@grammyjs/conversations";
import type { Context } from "grammy";
import { getConfig } from "./db.js";
import { startConversation } from "./handlers/start.js";
import { tradeConversation } from "./handlers/trade.js";
import { handlePositions, handleStats, handleHistory, handleSync } from "./handlers/commands.js";
import { isTradeMessage } from "./nlp.js";

type MyCtx = Context & ConversationFlavor;

export async function startBot() {
  const token = process.env.TELEGRAM_BOT_TOKEN;
  if (!token) throw new Error("TELEGRAM_BOT_TOKEN is not set");

  const bot = new Bot<MyCtx>(token);

  bot.use(session({ initial: () => ({}) }));
  bot.use(conversations());
  bot.use(createConversation(startConversation, "start"));
  bot.use(createConversation(tradeConversation, "trade"));

  bot.command("start",     ctx => ctx.conversation.enter("start"));
  bot.command("setup",     ctx => ctx.conversation.enter("start"));
  bot.command("positions", handlePositions);
  bot.command("stats",     handleStats);
  bot.command("history",   handleHistory);
  bot.command("sync",      handleSync);

  bot.on("message:text", async ctx => {
    const text = ctx.message.text;
    if (text.startsWith("/")) return;
    if (!getConfig()) { await ctx.reply("⚠️ Сначала настрой ключи: /start"); return; }
    if (isTradeMessage(text)) {
      await ctx.conversation.enter("trade");
    } else {
      await ctx.reply("Напиши торговую команду, например: «купи биткоин на 200 USDT»");
    }
  });

  bot.catch(err => console.error("[Bot]", err));
  await bot.start({ onStart: () => console.log("[Bot] Running") });
}
```

- [ ] **Step 3: Commit**

```bash
git add src/bot.ts src/handlers/start.ts
git commit -m "feat: grammy bot + /start onboarding flow"
```

---

## Task 6: Trade conversation

**Files:**
- Create: `~/dev/aitrading/src/handlers/trade.ts`

- [ ] **Step 1: Create src/handlers/trade.ts**

```typescript
import type { Conversation, ConversationFlavor } from "@grammyjs/conversations";
import type { Context } from "grammy";
import { InlineKeyboard } from "grammy";
import { parseIntent, type TradeIntent } from "../nlp.js";
import { spotBuy, spotSell, futuresBuy, futuresSell, getPrice, normalizeSymbol } from "../binance.js";
import { insertTrade } from "../db.js";

type MyCtx = Context & ConversationFlavor;

function parseNum(text: string): number | null {
  const n = parseFloat(text.replace(",", ".").replace(/[^\d.]/g, ""));
  return isNaN(n) || n <= 0 ? null : n;
}

async function ask<T>(
  conv: Conversation<MyCtx>,
  ctx: MyCtx,
  question: string,
  parse: (t: string) => T | null
): Promise<T | null> {
  await ctx.reply(question);
  while (true) {
    const msg = await conv.wait();
    const text = msg.message?.text?.trim() ?? "";
    if (text.toLowerCase() === "/cancel") return null;
    const val = parse(text);
    if (val !== null) return val;
    await ctx.reply("Не понял, попробуй ещё (/cancel для отмены):");
  }
}

export async function tradeConversation(conv: Conversation<MyCtx>, ctx: MyCtx) {
  const text = ctx.message?.text ?? "";
  await ctx.reply("🔄 Анализирую...");
  const intent: TradeIntent = await parseIntent(text);

  // action
  if (!intent.action) {
    const side = await ask(conv, ctx,
      "Что сделать?\n1 — Купить (лонг)\n2 — Продать (шорт)",
      t => {
        const l = t.toLowerCase();
        if (l === "1" || l.includes("купи") || l.includes("buy") || l.includes("лонг")) return "buy" as const;
        if (l === "2" || l.includes("продай") || l.includes("sell") || l.includes("шорт")) return "sell" as const;
        return null;
      }
    );
    if (!side) return;
    intent.action = side;
  }

  // asset
  if (!intent.asset) {
    const asset = await ask(conv, ctx,
      "Какая монета? (BTC, ETH, SOL...)",
      t => {
        const u = t.toUpperCase().trim();
        return u.length >= 2 && u.length <= 10 ? u : null;
      }
    );
    if (!asset) return;
    intent.asset = asset;
  }

  const symbol = normalizeSymbol(intent.asset);

  // market type
  if (!intent.market) {
    const market = await ask(conv, ctx,
      "Рынок?\n1 — Спот\n2 — Фьючерс",
      t => {
        const l = t.toLowerCase();
        if (l === "1" || l.includes("спот") || l.includes("spot")) return "spot" as const;
        if (l === "2" || l.includes("фьючерс") || l.includes("futures")) return "futures" as const;
        return null;
      }
    );
    if (!market) return;
    intent.market = market;
  }

  // amount
  if (!intent.usdt && !intent.qty) {
    if (intent.action === "buy") {
      const usdt = await ask(conv, ctx, `На сколько USDT купить ${intent.asset}?`, parseNum);
      if (!usdt) return;
      intent.usdt = usdt;
    } else {
      const qty = await ask(conv, ctx, `Сколько ${intent.asset} продать?`, parseNum);
      if (!qty) return;
      intent.qty = qty;
    }
  }

  // leverage for futures
  if (intent.market === "futures" && !intent.leverage) {
    const lev = await ask(conv, ctx, "Плечо? (например 10, 20, 50):", parseNum);
    if (!lev) return;
    intent.leverage = lev;
  }

  // Get current price + confirmation
  let currentPrice: number;
  try { currentPrice = await getPrice(symbol); }
  catch { await ctx.reply(`❌ Не могу получить цену ${symbol}.`); return; }

  const approxQty = intent.usdt ? intent.usdt / currentPrice : intent.qty!;
  const kb = new InlineKeyboard()
    .text("✅ Подтвердить", "confirm")
    .text("❌ Отмена", "cancel");

  await ctx.reply(
    `🔔 *Подтверди сделку:*\n\n` +
    `• Действие: ${intent.action === "buy" ? "КУПИТЬ" : "ПРОДАТЬ"}\n` +
    `• Монета: ${intent.asset} (${symbol})\n` +
    `• Объём: ${intent.usdt ? `${intent.usdt} USDT` : `${intent.qty} ${intent.asset}`}\n` +
    `• Рынок: ${intent.market === "futures" ? `Фьючерс x${intent.leverage ?? 1}` : "Спот"}\n` +
    `• Текущая цена: $${currentPrice.toLocaleString("en-US", { maximumFractionDigits: 4 })}\n` +
    `• Ориентировочно: ~${approxQty.toFixed(6)} ${intent.asset}`,
    { parse_mode: "Markdown", reply_markup: kb }
  );

  const cbCtx = await conv.waitForCallbackQuery(["confirm", "cancel"]);
  await cbCtx.answerCallbackQuery();
  if (cbCtx.callbackQuery.data === "cancel") { await ctx.reply("❌ Отменено."); return; }

  await ctx.reply("⏳ Выполняю ордер...");

  try {
    let orderId: string;
    let fillPrice: number;
    let fillQty: number;

    if (intent.market === "spot") {
      const res = intent.action === "buy"
        ? await spotBuy(symbol, intent.usdt!)
        : await spotSell(symbol, intent.qty ?? (intent.usdt! / currentPrice));
      orderId = String(res.orderId);
      fillPrice = parseFloat(res.fills?.[0]?.price ?? String(currentPrice));
      fillQty = res.fills?.reduce((s: number, f: any) => s + parseFloat(f.qty), 0) ?? approxQty;
    } else {
      const qty = intent.qty ?? (intent.usdt! / currentPrice);
      const res = intent.action === "buy"
        ? await futuresBuy(symbol, qty, intent.leverage ?? 10)
        : await futuresSell(symbol, qty, intent.leverage ?? 10);
      orderId = String(res.orderId);
      fillPrice = parseFloat(res.avgPrice ?? String(currentPrice));
      fillQty = parseFloat(res.executedQty ?? String(qty));
    }

    const trade = insertTrade({
      symbol,
      side: intent.action === "buy" ? "BUY" : "SELL",
      marketType: intent.market === "futures" ? "FUTURES" : "SPOT",
      qty: fillQty,
      price: fillPrice,
      usdtValue: fillQty * fillPrice,
      leverage: intent.leverage ?? 1,
      binanceOrderId: orderId,
      status: "OPEN",
      openedAt: Date.now(),
    });

    const actionLabel = intent.action === "buy" ? "Куплено" : "Продано";
    await ctx.reply(
      `✅ *${actionLabel} ${fillQty.toFixed(6)} ${intent.asset}*\n\n` +
      `Цена входа: $${fillPrice.toFixed(4)}\n` +
      `Объём: $${(fillQty * fillPrice).toFixed(2)}\n` +
      `Ордер Binance: #${orderId}\n` +
      `ID в БД: #${trade.id}`,
      { parse_mode: "Markdown" }
    );
  } catch (err: any) {
    const msg = (err?.message ?? "")
      .replace("insufficient balance", "Недостаточно баланса")
      .replace("Account has insufficient balance", "Недостаточно средств")
      .replace("MIN_NOTIONAL", "Сумма слишком мала (мин. ~10 USDT)");
    await ctx.reply(`❌ Ошибка: ${msg}`);
  }
}
```

- [ ] **Step 2: Commit**

```bash
git add src/handlers/trade.ts
git commit -m "feat: trade conversation — nlp, questions, confirm, execute, record"
```

---

## Task 7: Bot commands (/positions, /stats, /history, /sync)

**Files:**
- Create: `~/dev/aitrading/src/handlers/commands.ts`

- [ ] **Step 1: Create src/handlers/commands.ts**

```typescript
import type { Context } from "grammy";
import { db, getAllTrades } from "../db.js";
import { trades } from "../schema.js";
import { desc, eq } from "drizzle-orm";
import { getPrice } from "../binance.js";
import { syncBinanceHistory } from "../sync.js";

export async function handlePositions(ctx: Context) {
  const open = db.select().from(trades).where(eq(trades.status, "OPEN")).orderBy(desc(trades.openedAt)).all();
  if (open.length === 0) { await ctx.reply("📭 Нет открытых позиций."); return; }

  const lines = ["📊 *Открытые позиции:*\n"];
  for (const t of open) {
    try {
      const cur = await getPrice(t.symbol);
      const pnl = t.side === "BUY" ? (cur - t.price) * t.qty : (t.price - cur) * t.qty;
      const pnlPct = (pnl / t.usdtValue) * 100;
      lines.push(
        `${pnl >= 0 ? "🟢" : "🔴"} *${t.symbol}* (${t.marketType})\n` +
        `  Вход: $${t.price.toFixed(4)} | Сейчас: $${cur.toFixed(4)}\n` +
        `  P&L: ${pnl >= 0 ? "+" : ""}$${pnl.toFixed(2)} (${pnlPct >= 0 ? "+" : ""}${pnlPct.toFixed(2)}%)\n`
      );
    } catch { lines.push(`⚠️ *${t.symbol}* — ошибка цены\n`); }
  }
  await ctx.reply(lines.join("\n"), { parse_mode: "Markdown" });
}

export async function handleStats(ctx: Context) {
  const all = db.select().from(trades).all();
  const closed = all.filter(t => t.status === "CLOSED");
  const open = all.filter(t => t.status === "OPEN");
  const totalPnl = closed.reduce((s, t) => s + (t.pnlUsdt ?? 0), 0);
  const wins = closed.filter(t => (t.pnlUsdt ?? 0) > 0);
  const winRate = closed.length > 0 ? (wins.length / closed.length) * 100 : 0;
  const best = closed.reduce<typeof closed[0] | null>((b, t) => !b || (t.pnlUsdt ?? 0) > (b.pnlUsdt ?? 0) ? t : b, null);
  const worst = closed.reduce<typeof closed[0] | null>((w, t) => !w || (t.pnlUsdt ?? 0) < (w.pnlUsdt ?? 0) ? t : w, null);

  await ctx.reply(
    `📈 *Статистика*\n\n` +
    `💰 Общий P&L: ${totalPnl >= 0 ? "+" : ""}$${totalPnl.toFixed(2)}\n` +
    `🎯 Win Rate: ${winRate.toFixed(1)}%\n` +
    `📊 Сделок: ${all.length} (${open.length} открытых)\n` +
    `✅ Прибыльных: ${wins.length} | ❌ Убыточных: ${closed.length - wins.length}\n` +
    (best ? `🏆 Лучшая: ${best.symbol} +$${(best.pnlUsdt ?? 0).toFixed(2)}\n` : "") +
    (worst ? `💸 Худшая: ${worst.symbol} $${(worst.pnlUsdt ?? 0).toFixed(2)}\n` : ""),
    { parse_mode: "Markdown" }
  );
}

export async function handleHistory(ctx: Context) {
  const history = getAllTrades(20);
  if (history.length === 0) { await ctx.reply("📭 История пуста."); return; }

  const lines = ["📋 *Последние 20 сделок:*\n"];
  for (const t of history) {
    const emoji = t.status === "OPEN" ? "🟡" : (t.pnlUsdt ?? 0) >= 0 ? "🟢" : "🔴";
    const pnl = t.pnlUsdt != null ? ` | ${t.pnlUsdt >= 0 ? "+" : ""}$${t.pnlUsdt.toFixed(2)}` : " | открыта";
    const date = new Date(t.openedAt).toLocaleDateString("ru-RU");
    lines.push(`${emoji} ${t.symbol} ${t.side} $${t.price.toFixed(4)} (${date})${pnl}`);
  }
  await ctx.reply(lines.join("\n"), { parse_mode: "Markdown" });
}

export async function handleSync(ctx: Context) {
  await ctx.reply("🔄 Синхронизирую с Binance...");
  try {
    const count = await syncBinanceHistory();
    await ctx.reply(`✅ Синхронизировано: ${count} записей.`);
  } catch (err: any) {
    await ctx.reply(`❌ Ошибка: ${err?.message}`);
  }
}
```

- [ ] **Step 2: Commit**

```bash
git add src/handlers/commands.ts
git commit -m "feat: bot commands /positions /stats /history /sync"
```

---

## Task 8: Auto-sync cron

**Files:**
- Create: `~/dev/aitrading/src/sync.ts`

- [ ] **Step 1: Create src/sync.ts**

```typescript
import cron from "node-cron";
import { getConfig, upsertTradeByOrderId } from "./db.js";
import { getSpotHistory, getFuturesHistory } from "./binance.js";

const SPOT_PAIRS  = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "DOGEUSDT"];
const FUTURE_PAIRS = ["BTCUSDT", "ETHUSDT", "SOLUSDT"];

export async function syncBinanceHistory(): Promise<number> {
  if (!getConfig()) return 0;
  let count = 0;

  for (const sym of SPOT_PAIRS) {
    try {
      const history = await getSpotHistory(sym, 100);
      for (const t of history) {
        upsertTradeByOrderId({
          symbol: sym,
          side: t.isBuyer ? "BUY" : "SELL",
          marketType: "SPOT",
          qty: parseFloat(t.qty),
          price: parseFloat(t.price),
          usdtValue: parseFloat(t.quoteQty),
          leverage: 1,
          binanceOrderId: String(t.id),
          status: "CLOSED",
          openedAt: t.time,
          closedAt: t.time,
        });
        count++;
      }
    } catch { /* symbol not in portfolio, skip */ }
  }

  for (const sym of FUTURE_PAIRS) {
    try {
      const history = await getFuturesHistory(sym, 100);
      for (const t of history) {
        const pnl = parseFloat(t.realizedPnl ?? "0");
        upsertTradeByOrderId({
          symbol: sym,
          side: t.side === "BUY" ? "BUY" : "SELL",
          marketType: "FUTURES",
          qty: parseFloat(t.qty),
          price: parseFloat(t.price),
          usdtValue: parseFloat(t.qty) * parseFloat(t.price),
          leverage: 1,
          binanceOrderId: `${sym}-${t.id}`,
          status: pnl !== 0 ? "CLOSED" : "OPEN",
          pnlUsdt: pnl || null,
          openedAt: t.time,
          closedAt: pnl !== 0 ? t.time : undefined,
        });
        count++;
      }
    } catch { /* skip */ }
  }

  return count;
}

export function startSync() {
  cron.schedule("*/5 * * * *", async () => {
    try {
      const n = await syncBinanceHistory();
      if (n > 0) console.log(`[Sync] ${n} trades synced`);
    } catch (err) {
      console.error("[Sync]", err);
    }
  });
  console.log("[Sync] Auto-sync started (every 5 min)");
}
```

- [ ] **Step 2: Test end-to-end locally**

```bash
cd ~/dev/aitrading
# Fill .env with real TELEGRAM_BOT_TOKEN and ANTHROPIC_API_KEY
npm run dev
# In Telegram: /start → enter testnet keys → "купи биткоин на 10 USDT"
# Expected: bot asks market type, confirms, and if testnet=true executes on testnet
```

- [ ] **Step 3: Commit**

```bash
git add src/sync.ts
git commit -m "feat: binance history auto-sync cron — every 5 min"
git push origin main
```

---

## Task 9: Dashboard — SQLite connector

**Files:**
- Modify: `strategy-dashboard/package.json` (add better-sqlite3)
- Create: `strategy-dashboard/server/trading-db.ts`

- [ ] **Step 1: Install better-sqlite3 in strategy-dashboard**

```bash
cd ~/strategy-dashboard
npm install better-sqlite3
npm install --save-dev @types/better-sqlite3
```

- [ ] **Step 2: Create server/trading-db.ts**

```typescript
import Database from "better-sqlite3";
import { drizzle } from "drizzle-orm/better-sqlite3";
import { integer, real, sqliteTable, text } from "drizzle-orm/sqlite-core";
import { desc, eq } from "drizzle-orm";
import { resolve } from "path";

// Shared SQLite file written by the bot
const TRADING_DB_PATH = process.env.TRADING_DB_PATH
  ?? resolve(process.env.HOME ?? "", "dev/aitrading/trading.db");

let _db: ReturnType<typeof drizzle> | null = null;

const trades = sqliteTable("trades", {
  id: integer("id").primaryKey({ autoIncrement: true }),
  symbol: text("symbol").notNull(),
  side: text("side").notNull(),
  marketType: text("market_type").notNull(),
  qty: real("qty").notNull(),
  price: real("price").notNull(),
  usdtValue: real("usdt_value").notNull(),
  leverage: integer("leverage").notNull().default(1),
  binanceOrderId: text("binance_order_id"),
  pnlUsdt: real("pnl_usdt"),
  pnlPct: real("pnl_pct"),
  status: text("status").notNull().default("OPEN"),
  openedAt: integer("opened_at").notNull(),
  closedAt: integer("closed_at"),
});

export type Trade = typeof trades.$inferSelect;

function getDb() {
  if (!_db) {
    try {
      const sqlite = new Database(TRADING_DB_PATH, { readonly: true, fileMustExist: true });
      _db = drizzle(sqlite, { schema: { trades } });
    } catch {
      return null;
    }
  }
  return _db;
}

export function isTradingDbAvailable(): boolean {
  return getDb() !== null;
}

export function getTrades(limit = 200): Trade[] {
  const db = getDb();
  if (!db) return [];
  return db.select().from(trades).orderBy(desc(trades.openedAt)).limit(limit).all();
}

export function getOpenTrades(): Trade[] {
  const db = getDb();
  if (!db) return [];
  return db.select().from(trades).where(eq(trades.status, "OPEN")).orderBy(desc(trades.openedAt)).all();
}

export function getTradeStats() {
  const db = getDb();
  if (!db) return null;

  const all = db.select().from(trades).all();
  const closed = all.filter(t => t.status === "CLOSED");
  const open   = all.filter(t => t.status === "OPEN");
  const totalPnl = closed.reduce((s, t) => s + (t.pnlUsdt ?? 0), 0);
  const wins = closed.filter(t => (t.pnlUsdt ?? 0) > 0);
  const winRate = closed.length > 0 ? (wins.length / closed.length) * 100 : 0;
  const bestTrade = closed.reduce<Trade | null>((b, t) =>
    !b || (t.pnlUsdt ?? -Infinity) > (b.pnlUsdt ?? -Infinity) ? t : b, null);

  const pnlByDay: Record<string, number> = {};
  for (const t of closed) {
    const day = new Date(t.openedAt).toISOString().slice(0, 10);
    pnlByDay[day] = (pnlByDay[day] ?? 0) + (t.pnlUsdt ?? 0);
  }
  let cumulative = 0;
  const pnlChart = Object.entries(pnlByDay)
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([date, pnl]) => { cumulative += pnl; return { date, pnl, cumulative }; });

  return { totalPnl, winRate, totalTrades: all.length, openCount: open.length,
           closedCount: closed.length, winsCount: wins.length, bestTrade, pnlChart };
}
```

- [ ] **Step 3: Commit**

```bash
git add server/trading-db.ts package.json package-lock.json
git commit -m "feat: trading-db — read-only sqlite connector for aitrading"
```

---

## Task 10: Dashboard — tRPC router

**Files:**
- Create: `strategy-dashboard/server/routers/aitrading.ts`
- Modify: `strategy-dashboard/server/routers.ts` (add aitradingRouter)

- [ ] **Step 1: Create server/routers/aitrading.ts**

```typescript
import { z } from "zod";
import { router, publicProcedure } from "../_core/trpc";
import { getTrades, getOpenTrades, getTradeStats, isTradingDbAvailable } from "../trading-db";

export const aitradingRouter = router({
  status: publicProcedure.query(() => ({
    available: isTradingDbAvailable(),
  })),

  stats: publicProcedure.query(() => getTradeStats()),

  openPositions: publicProcedure.query(() => getOpenTrades()),

  history: publicProcedure
    .input(z.object({
      limit:      z.number().min(1).max(500).default(100),
      symbol:     z.string().optional(),
      marketType: z.enum(["SPOT", "FUTURES"]).optional(),
    }))
    .query(({ input }) => {
      let rows = getTrades(input.limit);
      if (input.symbol)     rows = rows.filter(t => t.symbol === input.symbol!.toUpperCase());
      if (input.marketType) rows = rows.filter(t => t.marketType === input.marketType);
      return rows;
    }),
});
```

- [ ] **Step 2: Register in server/routers.ts**

At the very top of the file (before `export const appRouter`), add:

```typescript
import { aitradingRouter } from "./routers/aitrading";
```

Inside `export const appRouter = router({`, add on a new line after `backlinks: backlinksRouter,`:

```typescript
  aitrading: aitradingRouter,
```

- [ ] **Step 3: Verify TypeScript compiles**

```bash
cd ~/strategy-dashboard
npm run check
```

Expected: no errors.

- [ ] **Step 4: Commit**

```bash
git add server/routers/aitrading.ts server/routers.ts
git commit -m "feat: aitrading tRPC router — stats/positions/history"
```

---

## Task 11: Dashboard — AiTrading page

**Files:**
- Create: `strategy-dashboard/client/src/components/aitrading/StatsCards.tsx`
- Create: `strategy-dashboard/client/src/components/aitrading/PnlChart.tsx`
- Create: `strategy-dashboard/client/src/components/aitrading/OpenPositions.tsx`
- Create: `strategy-dashboard/client/src/components/aitrading/TradeHistory.tsx`
- Create: `strategy-dashboard/client/src/pages/AiTrading.tsx`

- [ ] **Step 1: Create StatsCards.tsx**

```typescript
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { TrendingUp, TrendingDown, Activity, Target } from "lucide-react";

interface Props {
  totalPnl: number;
  winRate: number;
  totalTrades: number;
  openCount: number;
}

export function StatsCards({ totalPnl, winRate, totalTrades, openCount }: Props) {
  const isPositive = totalPnl >= 0;
  const PnlIcon = isPositive ? TrendingUp : TrendingDown;
  const pnlColor = isPositive ? "text-green-600" : "text-red-600";

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium text-slate-500">Total P&L</CardTitle>
        </CardHeader>
        <CardContent>
          <div className={`text-2xl font-bold flex items-center gap-2 ${pnlColor}`}>
            <PnlIcon className="w-5 h-5" />
            {isPositive ? "+" : ""}${totalPnl.toFixed(2)}
          </div>
        </CardContent>
      </Card>
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium text-slate-500">Win Rate</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold text-slate-900 flex items-center gap-2">
            <Target className="w-5 h-5 text-blue-500" />
            {winRate.toFixed(1)}%
          </div>
        </CardContent>
      </Card>
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium text-slate-500">Всего сделок</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold text-slate-900 flex items-center gap-2">
            <Activity className="w-5 h-5 text-purple-500" />
            {totalTrades}
          </div>
        </CardContent>
      </Card>
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium text-slate-500">Открытых</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold text-slate-900">{openCount}</div>
        </CardContent>
      </Card>
    </div>
  );
}
```

- [ ] **Step 2: Create PnlChart.tsx**

```typescript
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, ReferenceLine } from "recharts";

interface Props {
  data: { date: string; cumulative: number }[];
}

export function PnlChart({ data }: Props) {
  if (data.length === 0) return (
    <Card className="mb-6">
      <CardHeader><CardTitle>P&L по времени</CardTitle></CardHeader>
      <CardContent><p className="text-slate-500 text-sm">Нет закрытых сделок для графика.</p></CardContent>
    </Card>
  );

  return (
    <Card className="mb-6">
      <CardHeader><CardTitle>Кумулятивный P&L ($)</CardTitle></CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={250}>
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
            <XAxis dataKey="date" tick={{ fontSize: 11 }} tickFormatter={d => d.slice(5)} />
            <YAxis tick={{ fontSize: 11 }} tickFormatter={v => `$${Number(v).toFixed(0)}`} />
            <Tooltip
              formatter={(v: number) => [`$${v.toFixed(2)}`, "Cumulative P&L"]}
              labelFormatter={l => `Дата: ${l}`}
            />
            <ReferenceLine y={0} stroke="#94a3b8" strokeDasharray="4 4" />
            <Line type="monotone" dataKey="cumulative" stroke="#3b82f6" strokeWidth={2} dot={false} activeDot={{ r: 4 }} />
          </LineChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
```

- [ ] **Step 3: Create OpenPositions.tsx**

```typescript
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

interface Trade { id: number; symbol: string; side: string; marketType: string; qty: number; price: number; usdtValue: number; openedAt: number; }

export function OpenPositions({ trades }: { trades: Trade[] }) {
  if (trades.length === 0) return (
    <Card className="mb-6">
      <CardHeader><CardTitle>Открытые позиции</CardTitle></CardHeader>
      <CardContent><p className="text-slate-500 text-sm">Нет открытых позиций.</p></CardContent>
    </Card>
  );

  return (
    <Card className="mb-6">
      <CardHeader><CardTitle>Открытые позиции ({trades.length})</CardTitle></CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b text-slate-500 text-left">
                {["Монета", "Рынок", "Сторона", "Кол-во", "Цена входа", "Объём", "Дата"].map(h => (
                  <th key={h} className="pb-2 pr-4">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {trades.map(t => (
                <tr key={t.id} className="border-b last:border-0 hover:bg-slate-50">
                  <td className="py-2 pr-4 font-medium">{t.symbol}</td>
                  <td className="py-2 pr-4"><Badge variant="outline">{t.marketType}</Badge></td>
                  <td className="py-2 pr-4">
                    <Badge className={t.side === "BUY" ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700"}>
                      {t.side === "BUY" ? "LONG" : "SHORT"}
                    </Badge>
                  </td>
                  <td className="py-2 pr-4 font-mono">{t.qty.toFixed(6)}</td>
                  <td className="py-2 pr-4 font-mono">${t.price.toFixed(4)}</td>
                  <td className="py-2 pr-4 font-mono">${t.usdtValue.toFixed(2)}</td>
                  <td className="py-2 text-slate-500 text-xs">{new Date(t.openedAt).toLocaleDateString("ru-RU")}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  );
}
```

- [ ] **Step 4: Create TradeHistory.tsx**

```typescript
import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

interface Trade { id: number; symbol: string; side: string; marketType: string; qty: number; price: number; usdtValue: number; pnlUsdt: number | null; status: string; openedAt: number; }

export function TradeHistory({ trades }: { trades: Trade[] }) {
  const [sym, setSym] = useState("");
  const [mkt, setMkt] = useState("all");

  const rows = trades.filter(t =>
    (!sym || t.symbol.includes(sym.toUpperCase())) &&
    (mkt === "all" || t.marketType === mkt)
  );

  return (
    <Card>
      <CardHeader>
        <CardTitle>История сделок</CardTitle>
        <div className="flex gap-2 mt-2">
          <Input placeholder="Монета (BTC...)" value={sym} onChange={e => setSym(e.target.value)} className="max-w-[180px]" />
          <Select value={mkt} onValueChange={setMkt}>
            <SelectTrigger className="max-w-[150px]"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Все рынки</SelectItem>
              <SelectItem value="SPOT">Спот</SelectItem>
              <SelectItem value="FUTURES">Фьючерс</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </CardHeader>
      <CardContent>
        {rows.length === 0
          ? <p className="text-slate-500 text-sm">Нет сделок.</p>
          : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b text-slate-500 text-left">
                    {["Монета", "Рынок", "Сторона", "Цена", "Объём", "P&L", "Статус", "Дата"].map(h => (
                      <th key={h} className="pb-2 pr-3">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {rows.map(t => {
                    const pnlColor = (t.pnlUsdt ?? 0) >= 0 ? "text-green-600" : "text-red-600";
                    return (
                      <tr key={t.id} className="border-b last:border-0 hover:bg-slate-50">
                        <td className="py-2 pr-3 font-medium">{t.symbol}</td>
                        <td className="py-2 pr-3"><Badge variant="outline" className="text-xs">{t.marketType}</Badge></td>
                        <td className="py-2 pr-3">
                          <Badge className={`text-xs ${t.side === "BUY" ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700"}`}>
                            {t.side}
                          </Badge>
                        </td>
                        <td className="py-2 pr-3 font-mono">${t.price.toFixed(4)}</td>
                        <td className="py-2 pr-3 font-mono">${t.usdtValue.toFixed(2)}</td>
                        <td className={`py-2 pr-3 font-mono ${pnlColor}`}>
                          {t.pnlUsdt != null ? `${t.pnlUsdt >= 0 ? "+" : ""}$${t.pnlUsdt.toFixed(2)}` : "—"}
                        </td>
                        <td className="py-2 pr-3">
                          <Badge className={`text-xs ${t.status === "OPEN" ? "bg-yellow-100 text-yellow-700" : "bg-slate-100 text-slate-600"}`}>
                            {t.status}
                          </Badge>
                        </td>
                        <td className="py-2 text-slate-500 text-xs">{new Date(t.openedAt).toLocaleDateString("ru-RU")}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
      </CardContent>
    </Card>
  );
}
```

- [ ] **Step 5: Create AiTrading.tsx**

```typescript
import { trpc } from "@/lib/trpc";
import DashboardLayout from "@/components/DashboardLayout";
import { Loader2, AlertCircle } from "lucide-react";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { StatsCards } from "@/components/aitrading/StatsCards";
import { PnlChart } from "@/components/aitrading/PnlChart";
import { OpenPositions } from "@/components/aitrading/OpenPositions";
import { TradeHistory } from "@/components/aitrading/TradeHistory";

export default function AiTrading() {
  const { data: status } = trpc.aitrading.status.useQuery();
  const dbOk = status?.available ?? false;

  const { data: stats, isLoading } = trpc.aitrading.stats.useQuery(
    undefined,
    { refetchInterval: 30_000, enabled: dbOk }
  );
  const { data: positions } = trpc.aitrading.openPositions.useQuery(
    undefined,
    { refetchInterval: 30_000, enabled: dbOk }
  );
  const { data: history } = trpc.aitrading.history.useQuery(
    { limit: 200 },
    { enabled: dbOk }
  );

  return (
    <DashboardLayout>
      <div className="max-w-6xl mx-auto">
        <div className="mb-8">
          <h1 className="text-4xl font-bold text-slate-900 mb-2">AiTrading</h1>
          <p className="text-slate-600">Персональная аналитика Binance через Telegram бота</p>
        </div>

        {!dbOk && (
          <Alert className="mb-6">
            <AlertCircle className="w-4 h-4" />
            <AlertDescription>
              База данных бота недоступна. Запусти бота и убедись что{" "}
              <code className="bg-slate-100 px-1 rounded text-xs">TRADING_DB_PATH</code>{" "}
              указан в .env этого дашборда.
            </AlertDescription>
          </Alert>
        )}

        {isLoading && dbOk && (
          <div className="flex justify-center py-24">
            <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
          </div>
        )}

        {stats && (
          <>
            <StatsCards
              totalPnl={stats.totalPnl}
              winRate={stats.winRate}
              totalTrades={stats.totalTrades}
              openCount={stats.openCount}
            />
            <PnlChart data={stats.pnlChart} />
          </>
        )}

        <OpenPositions trades={positions ?? []} />
        <TradeHistory trades={history ?? []} />
      </div>
    </DashboardLayout>
  );
}
```

- [ ] **Step 6: Commit**

```bash
git add client/src/pages/AiTrading.tsx client/src/components/aitrading/
git commit -m "feat: aitrading dashboard — stats cards, p&l chart, positions, history"
```

---

## Task 12: Wire navigation

**Files:**
- Modify: `strategy-dashboard/client/src/App.tsx`
- Modify: `strategy-dashboard/client/src/components/DashboardLayout.tsx`

- [ ] **Step 1: Add route in App.tsx**

In the import block add:
```typescript
import AiTrading from "@/pages/AiTrading";
```

In the `<Switch>` block before `<Route component={NotFound} />`:
```typescript
<Route path="/aitrading" component={AiTrading} />
```

- [ ] **Step 2: Add nav item in DashboardLayout.tsx**

Change the lucide-react import line (line 24) to add `CandlestickChart`:
```typescript
import { BarChart2, BookOpen, Bot, Brain, Calendar, CandlestickChart, FileText, Globe, LogOut, PanelLeft, Sparkles, TrendingUp, Users } from "lucide-react";
```

Add to `menuItems` array after the `{ icon: TrendingUp, label: "SEO Tracker", ... }` entry:
```typescript
{ icon: CandlestickChart, label: "AiTrading", path: "/aitrading" },
```

- [ ] **Step 3: Add env var to strategy-dashboard**

Add to `strategy-dashboard/.env` (or `.env.local`):
```
TRADING_DB_PATH=/Users/evgenijgrudev/dev/aitrading/trading.db
```

- [ ] **Step 4: Test end-to-end**

```bash
cd ~/strategy-dashboard
npm run dev
# Open http://localhost:3000/aitrading
# Should show "DB недоступна" until bot is running

cd ~/dev/aitrading
npm run dev
# Refresh dashboard — should now load (empty tables until trades are made)
```

Send a test message in Telegram: **«купи биткоин на 10 USDT»** (use testnet first!)
After execution, refresh the dashboard — the trade should appear in history.

- [ ] **Step 5: Final commit and push**

```bash
cd ~/strategy-dashboard
git add client/src/App.tsx client/src/components/DashboardLayout.tsx
git commit -m "feat: wire /aitrading route and nav item"
git push origin main

cd ~/dev/aitrading
git push origin main
```

---

## Quick Start Checklist (after implementation)

1. **Telegram Bot Token** → [@BotFather](https://t.me/botfather) → `/newbot`
2. **Anthropic API Key** → console.anthropic.com
3. **Binance API Keys** → Binance → API Management → Create API
   - Permissions: ✅ Read Info + ✅ Spot Trading + ✅ Futures
   - Restrict to your IP for security
4. Fill `~/dev/aitrading/.env`
5. Add `TRADING_DB_PATH=/Users/evgenijgrudev/dev/aitrading/trading.db` to strategy-dashboard env
6. `cd ~/dev/aitrading && npm run dev`
7. Telegram → `/start` → enter API keys
8. Test with small amount: **«купи BNB на 10 USDT»**
9. Open `http://localhost:3000/aitrading` — trade should appear
