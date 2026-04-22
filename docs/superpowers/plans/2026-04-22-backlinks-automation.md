# Backlinks Automation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `/backlinks` tab to strategy-dashboard that auto-publishes SEO articles to Яндекс Дзен, Spark.ru, and Яндекс.Кью with backlinks to kadastrmap.info priority pages, using Puppeteer + Safari cookie injection, Groq for Russian content, and a cron schedule.

**Architecture:** Puppeteer (already installed) with stealth plugin for browser automation; existing `invokeLLM()` for content generation via Groq; Drizzle MySQL table for the post queue; tRPC `backlinksRouter` for CRUD; plain Express route for RSS 2.0 at `/rss/dzen`; `backlinkScheduler.ts` with `node-cron` for timed publishing.

**Tech Stack:** Puppeteer + puppeteer-extra-plugin-stealth (existing), node-cron (to add), Drizzle ORM (MySQL), tRPC, React/wouter, Python 3 (Safari binary cookie parser)

**Spec reference:** `docs/superpowers/specs/2026-04-22-backlinks-automation-design.md`

---

## File Map

### New files
```
drizzle/0011_backlink_posts.sql          <- DB migration
server/backlinks.db.ts                   <- Drizzle CRUD for backlink_posts
server/publishers/extract-cookies.py     <- Python: parse Safari Cookies.binarycookies
server/publishers/cookie-extractor.ts    <- TS wrapper: run Python, return cookie array
server/publishers/content-generator.ts  <- Groq prompts for dzen/spark/kw content
server/publishers/dzen.ts               <- Puppeteer publisher for Dzen
server/publishers/spark.ts              <- Puppeteer publisher for Spark.ru
server/publishers/kw.ts                 <- Puppeteer publisher for Yandex Q
server/publishers/pub-index.ts          <- publishNext() shared orchestration
server/publishers/rss.ts               <- RSS 2.0 XML builder
server/routers/backlinks.ts             <- tRPC router: getQueue, generate, publish, etc.
server/backlinkScheduler.ts             <- node-cron: 3 scheduled jobs
client/src/pages/Backlinks.tsx          <- Frontend tab
```

### Modified files
```
drizzle/schema.ts              <- +backlinkPosts table definition
server/routers.ts              <- +backlinksRouter
server/_core/index.ts          <- +GET /rss/dzen route + initBacklinkScheduler()
client/src/App.tsx             <- +Route /backlinks
client/src/pages/Home.tsx      <- +nav button "Backlinks"
.gitignore                     <- +server/publishers/.safari-cookies.json
```

---

## Task 1: Install dependency + DB migration

**Files:**
- Create: `drizzle/0011_backlink_posts.sql`
- Modify: `drizzle/schema.ts`

- [ ] **Step 1: Add node-cron**

```bash
cd /Users/evgenijgrudev/strategy-dashboard
pnpm add node-cron
pnpm add -D @types/node-cron
```

Expected: `node_modules/node-cron/` appears, no errors.

- [ ] **Step 2: Write SQL migration**

Create `drizzle/0011_backlink_posts.sql`:

```sql
CREATE TABLE `backlink_posts` (
  `id` int AUTO_INCREMENT PRIMARY KEY,
  `platform` enum('dzen','spark','kw') NOT NULL,
  `target_url` varchar(512) NOT NULL,
  `anchor_text` varchar(512) NOT NULL,
  `title` varchar(512),
  `article` text,
  `status` enum('pending','publishing','published','failed') NOT NULL DEFAULT 'pending',
  `published_url` varchar(512),
  `published_at` timestamp NULL,
  `error_msg` text,
  `created_at` timestamp DEFAULT (now()) NOT NULL
);

CREATE INDEX `idx_backlink_posts_platform_status`
  ON `backlink_posts`(`platform`, `status`);
```

- [ ] **Step 3: Add Drizzle table to schema.ts**

In `drizzle/schema.ts`, append after the last `export`:

```ts
export const backlinkPosts = mysqlTable("backlink_posts", {
  id:           int("id").autoincrement().primaryKey(),
  platform:     mysqlEnum("platform", ["dzen", "spark", "kw"]).notNull(),
  targetUrl:    varchar("target_url", { length: 512 }).notNull(),
  anchorText:   varchar("anchor_text", { length: 512 }).notNull(),
  title:        varchar("title", { length: 512 }),
  article:      text("article"),
  status:       mysqlEnum("status", ["pending", "publishing", "published", "failed"]).notNull().default("pending"),
  publishedUrl: varchar("published_url", { length: 512 }),
  publishedAt:  timestamp("published_at"),
  errorMsg:     text("error_msg"),
  createdAt:    timestamp("created_at").defaultNow().notNull(),
});

export type BacklinkPost = typeof backlinkPosts.$inferSelect;
export type InsertBacklinkPost = typeof backlinkPosts.$inferInsert;
```

- [ ] **Step 4: Run migration**

```bash
cd /Users/evgenijgrudev/strategy-dashboard
npm run db:push
```

Expected: drizzle-kit generates + migrates. Table `backlink_posts` created in DB.

- [ ] **Step 5: Commit**

```bash
git add drizzle/0011_backlink_posts.sql drizzle/schema.ts package.json pnpm-lock.yaml
git commit -m "feat: add backlink_posts DB table + node-cron dep"
```

---

## Task 2: DB query layer

**Files:**
- Create: `server/backlinks.db.ts`

- [ ] **Step 1: Create backlinks.db.ts**

```ts
import { db } from "./db";
import { backlinkPosts, BacklinkPost, InsertBacklinkPost } from "../drizzle/schema";
import { eq, and, desc } from "drizzle-orm";

export async function insertBacklinkPost(data: Omit<InsertBacklinkPost, "id" | "createdAt">): Promise<number> {
  const result = await db.insert(backlinkPosts).values(data);
  return (result as any)[0].insertId as number;
}

export async function getAllBacklinkPosts(): Promise<BacklinkPost[]> {
  return db.select().from(backlinkPosts).orderBy(desc(backlinkPosts.createdAt));
}

export async function getBacklinkPost(id: number): Promise<BacklinkPost | undefined> {
  const rows = await db.select().from(backlinkPosts).where(eq(backlinkPosts.id, id)).limit(1);
  return rows[0];
}

export async function getFirstPending(platform: "dzen" | "spark" | "kw"): Promise<BacklinkPost | undefined> {
  const rows = await db.select().from(backlinkPosts)
    .where(and(eq(backlinkPosts.platform, platform), eq(backlinkPosts.status, "pending")))
    .orderBy(backlinkPosts.createdAt)
    .limit(1);
  return rows[0];
}

export async function updateBacklinkPost(
  id: number,
  data: Partial<Pick<BacklinkPost, "status" | "publishedUrl" | "publishedAt" | "errorMsg" | "title" | "article">>
): Promise<void> {
  await db.update(backlinkPosts).set(data).where(eq(backlinkPosts.id, id));
}

export async function deleteBacklinkPost(id: number): Promise<void> {
  await db.delete(backlinkPosts).where(eq(backlinkPosts.id, id));
}

export async function getStatsByPlatform(): Promise<{ dzen: number; spark: number; kw: number; thisWeek: number }> {
  const all = await db.select().from(backlinkPosts).where(eq(backlinkPosts.status, "published"));
  const weekAgo = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000);
  return {
    dzen:     all.filter(r => r.platform === "dzen").length,
    spark:    all.filter(r => r.platform === "spark").length,
    kw:       all.filter(r => r.platform === "kw").length,
    thisWeek: all.filter(r => r.publishedAt && r.publishedAt >= weekAgo).length,
  };
}

export async function getLastNPublished(platform: "dzen", limit = 20): Promise<BacklinkPost[]> {
  return db.select().from(backlinkPosts)
    .where(and(eq(backlinkPosts.platform, platform), eq(backlinkPosts.status, "published")))
    .orderBy(desc(backlinkPosts.publishedAt))
    .limit(limit);
}
```

- [ ] **Step 2: TypeScript check**

```bash
cd /Users/evgenijgrudev/strategy-dashboard
npx tsc --noEmit 2>&1 | grep "backlinks.db"
```

Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add server/backlinks.db.ts
git commit -m "feat: backlinks DB query layer"
```

---

## Task 3: Safari cookie extractor

**Files:**
- Create: `server/publishers/extract-cookies.py`
- Create: `server/publishers/cookie-extractor.ts`
- Modify: `.gitignore`

- [ ] **Step 1: Create Python cookie parser**

Create `server/publishers/extract-cookies.py`:

```python
#!/usr/bin/env python3
"""
Parse Safari Cookies.binarycookies and extract Yandex/Dzen/Spark session cookies.
Writes Puppeteer-compatible JSON to .safari-cookies.json beside this script.
"""
import struct, sys, json, os

COOKIES_FILE = os.path.expanduser("~/Library/Cookies/Cookies.binarycookies")
OUTPUT_FILE  = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".safari-cookies.json")
MAC_EPOCH_DELTA = 978307200  # seconds from Mac epoch (2001-01-01) to Unix epoch
TARGET_DOMAINS = {".yandex.ru",".yandex.com",".dzen.ru",".sso.dzen.ru",".passport.dzen.ru",".spark.ru",".spark-interfax.ru"}


def read_cstr(data, offset):
    end = data.index(b"\x00", offset)
    return data[offset:end].decode("utf-8", errors="replace")


def parse():
    with open(COOKIES_FILE, "rb") as fh:
        raw = fh.read()
    assert raw[:4] == b"cook", "Not a Cookies.binarycookies file"
    num_pages = struct.unpack_from(">I", raw, 4)[0]
    page_sizes = [struct.unpack_from(">I", raw, 8 + i*4)[0] for i in range(num_pages)]
    cookies, cursor = [], 8 + num_pages * 4
    for ps in page_sizes:
        page = raw[cursor:cursor+ps]; cursor += ps
        if page[:4] != b"\x00\x00\x01\x00": continue
        nc = struct.unpack_from("<I", page, 4)[0]
        offsets = [struct.unpack_from("<I", page, 8+i*4)[0] for i in range(nc)]
        for co in offsets:
            try:
                c = page[co:]
                flags   = struct.unpack_from("<I", c, 8)[0]
                dom_o   = struct.unpack_from("<I", c, 16)[0]
                name_o  = struct.unpack_from("<I", c, 20)[0]
                path_o  = struct.unpack_from("<I", c, 24)[0]
                val_o   = struct.unpack_from("<I", c, 28)[0]
                exp_mac = struct.unpack_from(">d", c, 40)[0]
                domain = read_cstr(c, dom_o)
                name   = read_cstr(c, name_o)
                path   = read_cstr(c, path_o)
                value  = read_cstr(c, val_o)
                if domain and not domain.startswith("."): domain = "." + domain
                cookies.append({
                    "name": name, "value": value, "domain": domain, "path": path,
                    "expires": int(exp_mac + MAC_EPOCH_DELTA),
                    "httpOnly": bool(flags & 4), "secure": bool(flags & 1), "sameSite": "Lax"
                })
            except Exception: pass
    return [c for c in cookies if any(c["domain"] == d or c["domain"].endswith(d.lstrip(".")) for d in TARGET_DOMAINS)]


if __name__ == "__main__":
    try:
        data = parse()
        with open(OUTPUT_FILE, "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)
        print(f"OK {len(data)}", file=sys.stderr)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr); sys.exit(1)
```

- [ ] **Step 2: Test the Python script**

```bash
cd /Users/evgenijgrudev/strategy-dashboard/server/publishers
python3 extract-cookies.py
# Expected stderr: "OK 14" (or similar count > 0)
python3 -c "import json; d=json.load(open('.safari-cookies.json')); print(len(d), 'cookies'); [print(c['domain'], c['name']) for c in d[:5]]"
```

If stderr says `ERROR` or cookie count is 0: check byte offset for expiry. Change `struct.unpack_from(">d", c, 40)` to offset `44` and re-test.

- [ ] **Step 3: Create TypeScript wrapper**

Create `server/publishers/cookie-extractor.ts`:

```ts
import { execFile } from "child_process";
import { promisify } from "util";
import path from "path";
import fs from "fs";

const execFileAsync = promisify(execFile);

const SCRIPT_DIR   = path.join(process.cwd(), "server", "publishers");
const SCRIPT_PATH  = path.join(SCRIPT_DIR, "extract-cookies.py");
const COOKIES_PATH = path.join(SCRIPT_DIR, ".safari-cookies.json");
const MAX_AGE_MS   = 6 * 60 * 60 * 1000; // 6 hours

export type PuppeteerCookie = {
  name:     string;
  value:    string;
  domain:   string;
  path:     string;
  expires:  number;
  httpOnly: boolean;
  secure:   boolean;
  sameSite: "Lax" | "Strict" | "None";
};

async function refresh(): Promise<void> {
  const { stderr } = await execFileAsync("python3", [SCRIPT_PATH], { cwd: SCRIPT_DIR });
  if (!String(stderr).startsWith("OK")) {
    throw new Error(`Cookie extractor failed: ${String(stderr).trim()}`);
  }
}

export async function getCookies(): Promise<PuppeteerCookie[]> {
  const stale =
    !fs.existsSync(COOKIES_PATH) ||
    Date.now() - fs.statSync(COOKIES_PATH).mtimeMs >= MAX_AGE_MS;

  if (stale) await refresh();

  return JSON.parse(fs.readFileSync(COOKIES_PATH, "utf-8")) as PuppeteerCookie[];
}
```

- [ ] **Step 4: Update .gitignore**

Append to `.gitignore`:
```
server/publishers/.safari-cookies.json
```

- [ ] **Step 5: TypeScript check**

```bash
npx tsc --noEmit 2>&1 | grep cookie
```

Expected: no errors.

- [ ] **Step 6: Commit**

```bash
git add server/publishers/extract-cookies.py server/publishers/cookie-extractor.ts .gitignore
git commit -m "feat: Safari cookie extractor (Python parser + TS wrapper)"
```

---

## Task 4: Content generator

**Files:**
- Create: `server/publishers/content-generator.ts`

- [ ] **Step 1: Create content-generator.ts**

```ts
import { invokeLLM } from "../_core/llm";

export const PRIORITY_PAGES = [
  { url: "/kadastr/raspolozhenie-po-kadastrovomu-nomeru/",             anchor: "найти участок по кадастровому номеру" },
  { url: "/kadastr/kadastrovyj-nomer-po-adresu-obekta-nedvizhimosti/", anchor: "кадастровый номер по адресу" },
  { url: "/kadastr/proverit-kvartiru-v-rosreestre-po-adresu-onlajn/",  anchor: "проверить квартиру в росреестре" },
  { url: "/kadastr/poluchit-vypisku-egrn-po-kadastrovomu-nomeru/",     anchor: "получить выписку ЕГРН" },
  { url: "/kadastr/proverit-obremenenie-na-nedvizhimost/",             anchor: "проверить обременение на недвижимость" },
] as const;

type PageEntry = typeof PRIORITY_PAGES[number];

export function pickNextPage(existingCount: number): PageEntry {
  return PRIORITY_PAGES[existingCount % PRIORITY_PAGES.length];
}

function topicForUrl(url: string): string {
  const MAP: Record<string, string> = {
    "/kadastr/raspolozhenie-po-kadastrovomu-nomeru/":             "Как найти расположение земельного участка по кадастровому номеру",
    "/kadastr/kadastrovyj-nomer-po-adresu-obekta-nedvizhimosti/": "Как узнать кадастровый номер объекта недвижимости по адресу",
    "/kadastr/proverit-kvartiru-v-rosreestre-po-adresu-onlajn/":  "Как проверить квартиру в росреестре по адресу онлайн",
    "/kadastr/poluchit-vypisku-egrn-po-kadastrovomu-nomeru/":     "Как получить выписку из ЕГРН по кадастровому номеру",
    "/kadastr/proverit-obremenenie-na-nedvizhimost/":             "Как проверить обременение на недвижимость онлайн",
  };
  return MAP[url] ?? "Кадастровая информация по недвижимости";
}

function questionForUrl(url: string): string {
  const MAP: Record<string, string> = {
    "/kadastr/raspolozhenie-po-kadastrovomu-nomeru/":             "Как найти участок по кадастровому номеру?",
    "/kadastr/kadastrovyj-nomer-po-adresu-obekta-nedvizhimosti/": "Как узнать кадастровый номер квартиры по адресу?",
    "/kadastr/proverit-kvartiru-v-rosreestre-po-adresu-onlajn/":  "Как проверить квартиру через Росреестр онлайн?",
    "/kadastr/poluchit-vypisku-egrn-po-kadastrovomu-nomeru/":     "Где получить выписку из ЕГРН быстро?",
    "/kadastr/proverit-obremenenie-na-nedvizhimost/":             "Как узнать есть ли обременение на недвижимость?",
  };
  return MAP[url] ?? "Как проверить недвижимость онлайн?";
}

async function callLLM(system: string, user: string): Promise<string> {
  const resp = await invokeLLM({
    model:     "llama-3.3-70b-versatile",
    maxTokens: 3000,
    messages:  [{ role: "system", content: system }, { role: "user", content: user }],
  });
  return typeof resp.choices[0]?.message.content === "string" ? resp.choices[0].message.content : "{}";
}

function parseJson(raw: string): any {
  try { return JSON.parse(raw.replace(/^```json\s*|\s*```$/g, "").trim()); } catch { return null; }
}

export async function generateDzenArticle(targetUrl: string, anchor: string): Promise<{ title: string; article: string }> {
  const link  = `[${anchor}](https://kadastrmap.info${targetUrl})`;
  const topic = topicForUrl(targetUrl);
  const system = `Ты SEO-автор, пишешь полезные статьи о недвижимости и кадастре для Яндекс Дзен. Стиль: объясняю как эксперт, без воды. Структура: заголовок, 4-6 разделов H2, вывод. Вставь ссылку ${link} органично в тело текста (не в конце). Только русский язык. Без markdown-кодов и HTML.`;
  const user   = `Напиши статью на тему "${topic}". Объём 900-1200 слов. Верни JSON: {"title":"...","article":"..."}`;
  const raw    = await callLLM(system, user);
  const json   = parseJson(raw);
  return { title: json?.title ?? topic, article: json?.article ?? raw };
}

export async function generateSparkArticle(targetUrl: string, anchor: string): Promise<{ title: string; article: string }> {
  const link  = `[${anchor}](https://kadastrmap.info${targetUrl})`;
  const topic = topicForUrl(targetUrl);
  const system = `Ты эксперт по недвижимости, пишешь экспертную колонку на Spark.ru. Деловой практический стиль, минимум списков, больше объяснений. Вставь ссылку ${link} органично. Только русский язык.`;
  const user   = `Напиши экспертную колонку "${topic}". Объём 600-900 слов. Верни JSON: {"title":"...","article":"..."}`;
  const raw    = await callLLM(system, user);
  const json   = parseJson(raw);
  return { title: json?.title ?? topic, article: json?.article ?? raw };
}

export async function generateKwAnswer(targetUrl: string, _anchor: string): Promise<{ question: string; article: string }> {
  const link     = `https://kadastrmap.info${targetUrl}`;
  const question = questionForUrl(targetUrl);
  const system   = `Ты эксперт по кадастру, отвечаешь на вопросы на Яндекс.Кью. Дай развёрнутый практический ответ. Упомяни ${link} органично. Только русский язык.`;
  const user     = `Напиши ответ на вопрос "${question}". Объём 200-350 слов. Верни JSON: {"answer":"..."}`;
  const raw      = await callLLM(system, user);
  const json     = parseJson(raw);
  return { question, article: json?.answer ?? raw };
}
```

- [ ] **Step 2: TypeScript check**

```bash
npx tsc --noEmit 2>&1 | grep content-generator
```

Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add server/publishers/content-generator.ts
git commit -m "feat: backlinks content generator (Groq prompts for Dzen/Spark/Kw)"
```

---

## Task 5: Puppeteer publishers

**Files:**
- Create: `server/publishers/dzen.ts`
- Create: `server/publishers/spark.ts`
- Create: `server/publishers/kw.ts`

Text is injected via `page.focus()` + `page.keyboard.type()` which uses CDP `Input.insertText` — instant regardless of article length.

> Selectors must be verified against live editors. On any error, a screenshot is saved to `/tmp/backlinks-error-{platform}-{ts}.png`.

- [ ] **Step 1: Create dzen.ts**

```ts
import puppeteer from "puppeteer-extra";
import StealthPlugin from "puppeteer-extra-plugin-stealth";
import { getCookies } from "./cookie-extractor";
import type { BacklinkPost } from "../../drizzle/schema";

puppeteer.use(StealthPlugin());

export async function publishToDzen(post: BacklinkPost): Promise<string> {
  const cookies = await getCookies();
  const dzenCookies = cookies.filter(c =>
    c.domain.includes("dzen.ru") || c.domain.includes("yandex.ru") || c.domain.includes("yandex.com")
  );

  const browser = await puppeteer.launch({ headless: true, args: ["--no-sandbox", "--disable-setuid-sandbox"] });
  const page    = await browser.newPage();

  try {
    await page.setViewport({ width: 1280, height: 800 });
    await page.setCookie(...dzenCookies.map(c => ({
      name: c.name, value: c.value, domain: c.domain, path: c.path,
      expires: c.expires, httpOnly: c.httpOnly, secure: c.secure, sameSite: c.sameSite as any,
    })));

    await page.goto("https://dzen.ru/editor/create-article", { waitUntil: "networkidle2", timeout: 30000 });

    // Wait for editor
    await page.waitForSelector('[contenteditable="true"], [data-slate-editor="true"]', { timeout: 20000 });

    // Fill title — Dzen editor renders title as first contenteditable block
    const titleText  = post.title ?? "Статья о кадастре";
    const allEditors = await page.$$('[contenteditable="true"]');
    await allEditors[0].click();
    await page.keyboard.type(titleText);

    // Move to body (second contenteditable or Tab key)
    if (allEditors.length > 1) {
      await allEditors[1].click();
    } else {
      await page.keyboard.press("Tab");
    }
    await page.keyboard.type(post.article ?? "");
    await new Promise(r => setTimeout(r, 2000));

    // Click publish
    const publishBtn = await page.waitForSelector(
      'button[data-testid="publish"], button[class*="publish"], [data-action="publish"]',
      { timeout: 10000 }
    );
    await publishBtn?.click();

    // Wait for URL to contain /a/ (published article slug)
    await page.waitForFunction(
      () => location.href.includes("dzen.ru/a/"),
      { timeout: 30000 }
    );

    return page.url();
  } catch (err) {
    await page.screenshot({ path: `/tmp/backlinks-error-dzen-${Date.now()}.png` }).catch(() => {});
    throw err;
  } finally {
    await browser.close();
  }
}
```

- [ ] **Step 2: Create spark.ts**

```ts
import puppeteer from "puppeteer-extra";
import StealthPlugin from "puppeteer-extra-plugin-stealth";
import { getCookies } from "./cookie-extractor";
import type { BacklinkPost } from "../../drizzle/schema";

puppeteer.use(StealthPlugin());

export async function publishToSpark(post: BacklinkPost): Promise<string> {
  const cookies = await getCookies();
  const sparkCookies = cookies.filter(c =>
    c.domain.includes("yandex.ru") || c.domain.includes("yandex.com") || c.domain.includes("spark.ru")
  );

  const browser = await puppeteer.launch({ headless: true, args: ["--no-sandbox", "--disable-setuid-sandbox"] });
  const page    = await browser.newPage();

  try {
    await page.setViewport({ width: 1280, height: 800 });
    await page.setCookie(...sparkCookies.map(c => ({
      name: c.name, value: c.value, domain: c.domain, path: c.path,
      expires: c.expires, httpOnly: c.httpOnly, secure: c.secure, sameSite: c.sameSite as any,
    })));

    await page.goto("https://spark.ru/post/new", { waitUntil: "networkidle2", timeout: 30000 });

    if (page.url().includes("passport.yandex")) {
      throw new Error("Spark session expired — re-login in Safari to refresh Yandex session cookies");
    }

    // Title input
    const titleSel = 'input[name="title"], input[placeholder*="аголов"]';
    await page.waitForSelector(titleSel, { timeout: 15000 });
    await page.click(titleSel);
    await page.keyboard.type(post.title ?? "Статья об объектах недвижимости");

    // Body
    const allEditors = await page.$$('[contenteditable="true"]');
    const bodyEditor  = allEditors[allEditors.length - 1];
    await bodyEditor.click();
    await page.keyboard.type(post.article ?? "");
    await new Promise(r => setTimeout(r, 2000));

    // Publish
    const publishBtn = await page.waitForSelector('button[type="submit"], button[class*="submit"]', { timeout: 10000 });
    await publishBtn?.click();
    await page.waitForNavigation({ waitUntil: "networkidle2", timeout: 30000 });

    return page.url();
  } catch (err) {
    await page.screenshot({ path: `/tmp/backlinks-error-spark-${Date.now()}.png` }).catch(() => {});
    throw err;
  } finally {
    await browser.close();
  }
}
```

- [ ] **Step 3: Create kw.ts**

```ts
import puppeteer from "puppeteer-extra";
import StealthPlugin from "puppeteer-extra-plugin-stealth";
import { getCookies } from "./cookie-extractor";
import type { BacklinkPost } from "../../drizzle/schema";

puppeteer.use(StealthPlugin());

// Yandex Q (formerly Яндекс.Кью) lives at yandex.ru/q/
export async function publishToKw(post: BacklinkPost): Promise<string> {
  const cookies = await getCookies();
  const yndxCookies = cookies.filter(c =>
    c.domain.includes("yandex.ru") || c.domain.includes("yandex.com")
  );

  const browser = await puppeteer.launch({ headless: true, args: ["--no-sandbox", "--disable-setuid-sandbox"] });
  const page    = await browser.newPage();

  try {
    await page.setViewport({ width: 1280, height: 800 });
    await page.setCookie(...yndxCookies.map(c => ({
      name: c.name, value: c.value, domain: c.domain, path: c.path,
      expires: c.expires, httpOnly: c.httpOnly, secure: c.secure, sameSite: c.sameSite as any,
    })));

    // Search for relevant questions using the anchor as topic
    const topic = encodeURIComponent(post.anchorText.substring(0, 60));
    await page.goto(`https://yandex.ru/q/search?text=${topic}`, { waitUntil: "networkidle2", timeout: 30000 });

    // Find a question link and click it
    let questionUrl = page.url();
    const links = await page.$$('a[href*="/q/"]');
    for (const link of links.slice(0, 8)) {
      const href = await link.getProperty("href").then(h => h.jsonValue<string>());
      if (!href.includes("/q/search") && href.includes("/q/")) {
        await page.goto(href, { waitUntil: "networkidle2", timeout: 10000 }).catch(() => {});
        questionUrl = page.url();
        break;
      }
    }

    // Click the answer button
    const answerBtnSel = 'button[data-testid="answer-button"], a[href*="answer"], button[class*="answer"]';
    const answerBtn = await page.$(answerBtnSel);
    if (!answerBtn) throw new Error("Could not find answer button on Yandex Q");
    await answerBtn.click();
    await new Promise(r => setTimeout(r, 1000));

    // Type answer in the editor
    const answerEditors = await page.$$('[contenteditable="true"]');
    const answerEditor  = answerEditors[answerEditors.length - 1];
    await answerEditor.click();
    await page.keyboard.type(post.article ?? "");
    await new Promise(r => setTimeout(r, 1500));

    // Submit
    const submitSel = 'button[type="submit"], button[data-testid="submit-answer"]';
    const submit = await page.waitForSelector(submitSel, { timeout: 10000 });
    await submit?.click();
    await new Promise(r => setTimeout(r, 3000));

    return questionUrl;
  } catch (err) {
    await page.screenshot({ path: `/tmp/backlinks-error-kw-${Date.now()}.png` }).catch(() => {});
    throw err;
  } finally {
    await browser.close();
  }
}
```

- [ ] **Step 4: TypeScript check**

```bash
npx tsc --noEmit 2>&1 | grep "publishers/"
```

Expected: no errors. If `puppeteer-extra` types are missing add `// @ts-ignore` above the import.

- [ ] **Step 5: Commit**

```bash
git add server/publishers/dzen.ts server/publishers/spark.ts server/publishers/kw.ts
git commit -m "feat: Puppeteer publishers for Dzen, Spark, Yandex-Q"
```

---

## Task 6: Publishers orchestrator + RSS

**Files:**
- Create: `server/publishers/pub-index.ts`
- Create: `server/publishers/rss.ts`

- [ ] **Step 1: Create pub-index.ts**

```ts
import { getFirstPending, updateBacklinkPost, insertBacklinkPost, getAllBacklinkPosts } from "../backlinks.db";
import { generateDzenArticle, generateSparkArticle, generateKwAnswer, PRIORITY_PAGES, pickNextPage } from "./content-generator";
import { publishToDzen } from "./dzen";
import { publishToSpark } from "./spark";
import { publishToKw } from "./kw";
import type { BacklinkPost } from "../../drizzle/schema";

export type Platform = "dzen" | "spark" | "kw";

export async function generateAndQueue(platform: Platform, targetUrl?: string): Promise<number> {
  const all          = await getAllBacklinkPosts();
  const platformCount = all.filter(p => p.platform === platform).length;

  let page = pickNextPage(platformCount);
  if (targetUrl) {
    const found = PRIORITY_PAGES.find(p => p.url === targetUrl);
    if (found) page = found;
  }

  let title:   string;
  let article: string;

  if (platform === "dzen") {
    const r = await generateDzenArticle(page.url, page.anchor);
    title = r.title; article = r.article;
  } else if (platform === "spark") {
    const r = await generateSparkArticle(page.url, page.anchor);
    title = r.title; article = r.article;
  } else {
    const r = await generateKwAnswer(page.url, page.anchor);
    title = r.question; article = r.article;
  }

  return insertBacklinkPost({ platform, targetUrl: page.url, anchorText: page.anchor, title, article, status: "pending" });
}

export async function publishPost(post: BacklinkPost): Promise<void> {
  await updateBacklinkPost(post.id, { status: "publishing" });
  try {
    let publishedUrl: string;
    if (post.platform === "dzen")  publishedUrl = await publishToDzen(post);
    else if (post.platform === "spark") publishedUrl = await publishToSpark(post);
    else                                publishedUrl = await publishToKw(post);

    await updateBacklinkPost(post.id, { status: "published", publishedUrl, publishedAt: new Date() });
    console.log(`[Backlinks] Published ${post.platform} id=${post.id} -> ${publishedUrl}`);
  } catch (err: any) {
    await updateBacklinkPost(post.id, { status: "failed", errorMsg: err.message ?? String(err) });
    console.error(`[Backlinks] FAILED ${post.platform} id=${post.id}:`, err.message);
    throw err;
  }
}

export async function publishNext(platform: Platform): Promise<void> {
  const post = await getFirstPending(platform);
  if (!post) { console.log(`[Backlinks] No pending posts for ${platform}`); return; }
  await publishPost(post);
}
```

- [ ] **Step 2: Create rss.ts**

```ts
import type { BacklinkPost } from "../../drizzle/schema";

function escXml(s: string): string {
  return s.replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;");
}

export function buildRssFeed(posts: BacklinkPost[]): string {
  const items = posts
    .filter(p => p.publishedUrl && p.publishedAt)
    .map(p => `    <item>
      <title>${escXml(p.title ?? "")}</title>
      <link>${escXml(p.publishedUrl!)}</link>
      <description>${escXml((p.article ?? "").substring(0, 500))}</description>
      <pubDate>${p.publishedAt!.toUTCString()}</pubDate>
      <guid>${escXml(p.publishedUrl!)}</guid>
    </item>`)
    .join("\n");

  return `<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>kadastrmap.info — Кадастр и недвижимость</title>
    <link>https://kadastrmap.info</link>
    <description>Полезные статьи о кадастре и недвижимости</description>
    <language>ru</language>
${items}
  </channel>
</rss>`;
}
```

- [ ] **Step 3: TypeScript check**

```bash
npx tsc --noEmit 2>&1 | grep "pub-index\|rss"
```

Expected: no errors.

- [ ] **Step 4: Commit**

```bash
git add server/publishers/pub-index.ts server/publishers/rss.ts
git commit -m "feat: publishNext orchestrator + RSS builder"
```

---

## Task 7: tRPC backlinks router

**Files:**
- Create: `server/routers/backlinks.ts`

- [ ] **Step 1: Create backlinks.ts router**

```ts
import { router, protectedProcedure } from "../_core/trpc";
import { z } from "zod";
import { TRPCError } from "@trpc/server";
import {
  getAllBacklinkPosts, getBacklinkPost, updateBacklinkPost,
  deleteBacklinkPost, getStatsByPlatform, getFirstPending,
} from "../backlinks.db";
import { publishPost, publishNext, generateAndQueue } from "../publishers/pub-index";
import { PRIORITY_PAGES } from "../publishers/content-generator";

const PLATFORM = z.enum(["dzen", "spark", "kw"]);

export const backlinksRouter = router({
  getQueue: protectedProcedure
    .query(() => getAllBacklinkPosts()),

  getStats: protectedProcedure
    .query(() => getStatsByPlatform()),

  generate: protectedProcedure
    .input(z.object({ platform: PLATFORM, targetUrl: z.string().optional() }))
    .mutation(async ({ input }) => {
      if (input.targetUrl && !PRIORITY_PAGES.find(p => p.url === input.targetUrl)) {
        throw new TRPCError({ code: "BAD_REQUEST", message: "Unknown target URL" });
      }
      const id = await generateAndQueue(input.platform, input.targetUrl);
      return { id };
    }),

  publish: protectedProcedure
    .input(z.object({ id: z.number() }))
    .mutation(async ({ input }) => {
      const post = await getBacklinkPost(input.id);
      if (!post) throw new TRPCError({ code: "NOT_FOUND" });
      if (post.status === "publishing" || post.status === "published") {
        throw new TRPCError({ code: "BAD_REQUEST", message: `Post already ${post.status}` });
      }
      await updateBacklinkPost(post.id, { status: "pending" });
      await publishPost({ ...post, status: "pending" });
      return { ok: true };
    }),

  publishNext: protectedProcedure
    .input(z.object({ platform: PLATFORM }))
    .mutation(async ({ input }) => {
      await publishNext(input.platform);
      return { ok: true };
    }),

  retry: protectedProcedure
    .input(z.object({ id: z.number() }))
    .mutation(async ({ input }) => {
      const post = await getBacklinkPost(input.id);
      if (!post) throw new TRPCError({ code: "NOT_FOUND" });
      await updateBacklinkPost(post.id, { status: "pending", errorMsg: undefined as any });
      return { ok: true };
    }),

  delete: protectedProcedure
    .input(z.object({ id: z.number() }))
    .mutation(async ({ input }) => {
      await deleteBacklinkPost(input.id);
      return { ok: true };
    }),
});
```

- [ ] **Step 2: TypeScript check**

```bash
npx tsc --noEmit 2>&1 | grep "routers/backlinks"
```

Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add server/routers/backlinks.ts
git commit -m "feat: backlinksRouter (tRPC) — generate, publish, retry, delete, stats"
```

---

## Task 8: Frontend — Backlinks.tsx

**Files:**
- Create: `client/src/pages/Backlinks.tsx`

- [ ] **Step 1: Create Backlinks.tsx**

```tsx
import { useState } from "react";
import { trpc } from "@/_core/trpc";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { toast } from "sonner";

type Platform = "dzen" | "spark" | "kw";
const PL_LABEL: Record<Platform, string> = { dzen: "Дзен", spark: "Spark", kw: "Кью" };
const STATUS_CLS: Record<string, string> = {
  pending:    "bg-yellow-100 text-yellow-800",
  publishing: "bg-blue-100 text-blue-800",
  published:  "bg-green-100 text-green-800",
  failed:     "bg-red-100 text-red-800",
};

export default function Backlinks() {
  const [filterPl, setFilterPl]   = useState<string>("all");
  const [genPl, setGenPl]         = useState<Platform>("dzen");
  const [busy, setBusy]           = useState(false);

  const { data: queue, refetch } = trpc.backlinks.getQueue.useQuery();
  const { data: stats }          = trpc.backlinks.getStats.useQuery();

  const genMut    = trpc.backlinks.generate.useMutation();
  const pubMut    = trpc.backlinks.publish.useMutation();
  const retryMut  = trpc.backlinks.retry.useMutation();
  const delMut    = trpc.backlinks.delete.useMutation();
  const pubNext   = trpc.backlinks.publishNext.useMutation();

  const wrap = async (fn: () => Promise<unknown>, msg: string) => {
    setBusy(true);
    try { await fn(); toast.success(msg); refetch(); }
    catch (e: any) { toast.error(e.message ?? "Ошибка"); }
    finally { setBusy(false); }
  };

  const filtered = (queue ?? []).filter(p => filterPl === "all" || p.platform === filterPl);
  const rssUrl   = `${window.location.origin}/rss/dzen`;

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b px-6 py-4 flex items-center gap-4">
        <h1 className="text-2xl font-bold">Backlinks — kadastrmap.info</h1>
      </header>

      <div className="p-6 max-w-6xl mx-auto space-y-6">
        {/* Stats */}
        <div className="grid grid-cols-4 gap-4">
          {(["dzen","spark","kw"] as Platform[]).map(p => (
            <div key={p} className="bg-white rounded-lg border p-4 text-center">
              <div className="text-2xl font-bold">{stats?.[p] ?? 0}</div>
              <div className="text-sm text-gray-500">{PL_LABEL[p]} опубл.</div>
            </div>
          ))}
          <div className="bg-white rounded-lg border p-4 text-center">
            <div className="text-2xl font-bold">{stats?.thisWeek ?? 0}</div>
            <div className="text-sm text-gray-500">Эта неделя</div>
          </div>
        </div>

        {/* Toolbar */}
        <div className="flex gap-3 flex-wrap items-center">
          <Select value={filterPl} onValueChange={setFilterPl}>
            <SelectTrigger className="w-28"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Все</SelectItem>
              {(["dzen","spark","kw"] as Platform[]).map(p => <SelectItem key={p} value={p}>{PL_LABEL[p]}</SelectItem>)}
            </SelectContent>
          </Select>

          <Select value={genPl} onValueChange={v => setGenPl(v as Platform)}>
            <SelectTrigger className="w-28"><SelectValue /></SelectTrigger>
            <SelectContent>
              {(["dzen","spark","kw"] as Platform[]).map(p => <SelectItem key={p} value={p}>{PL_LABEL[p]}</SelectItem>)}
            </SelectContent>
          </Select>
          <Button disabled={busy} onClick={() => wrap(() => genMut.mutateAsync({ platform: genPl }), "Сгенерировано")}>
            + Генерировать
          </Button>

          <div className="ml-auto flex gap-2">
            {(["dzen","spark","kw"] as Platform[]).map(p => (
              <Button key={p} size="sm" variant="outline" disabled={busy}
                onClick={() => wrap(() => pubNext.mutateAsync({ platform: p }), `${PL_LABEL[p]} опубликован`)}>
                ▶ {PL_LABEL[p]}
              </Button>
            ))}
          </div>
        </div>

        {/* Queue table */}
        <div className="bg-white rounded-lg border overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b">
              <tr className="text-left">
                {["#","Платформа","Целевая страница","Заголовок","Статус","Создан","Действия"].map(h => (
                  <th key={h} className="px-4 py-3 font-medium">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y">
              {filtered.map(post => (
                <tr key={post.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 text-gray-500">{post.id}</td>
                  <td className="px-4 py-3 font-medium">{PL_LABEL[post.platform as Platform]}</td>
                  <td className="px-4 py-3 text-xs text-gray-500 max-w-[160px] truncate" title={post.targetUrl}>{post.targetUrl}</td>
                  <td className="px-4 py-3 max-w-[200px] truncate" title={post.title ?? ""}>{post.title ?? "—"}</td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-0.5 rounded text-xs font-medium ${STATUS_CLS[post.status] ?? ""}`} title={post.errorMsg ?? ""}>
                      {post.status}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-gray-500 text-xs">{new Date(post.createdAt).toLocaleDateString("ru-RU")}</td>
                  <td className="px-4 py-3">
                    <div className="flex gap-1">
                      {(post.status === "pending" || post.status === "failed") && (
                        <Button size="sm" variant="outline" onClick={() => wrap(() => pubMut.mutateAsync({ id: post.id }), "Опубликовано")}>
                          Publish
                        </Button>
                      )}
                      {post.publishedUrl && (
                        <a href={post.publishedUrl} target="_blank" rel="noopener noreferrer" className="text-blue-500 hover:underline text-xs leading-9 px-1">→ URL</a>
                      )}
                      {post.status === "failed" && (
                        <Button size="sm" variant="ghost" onClick={() => wrap(() => retryMut.mutateAsync({ id: post.id }), "Сброшено")}>Retry</Button>
                      )}
                      <Button size="sm" variant="ghost" className="text-red-400"
                        onClick={() => wrap(() => delMut.mutateAsync({ id: post.id }), "Удалено")}>✕</Button>
                    </div>
                  </td>
                </tr>
              ))}
              {filtered.length === 0 && (
                <tr><td colSpan={7} className="px-4 py-8 text-center text-gray-400">Нет постов</td></tr>
              )}
            </tbody>
          </table>
        </div>

        {/* RSS link */}
        <div className="flex items-center gap-3 text-sm text-gray-500">
          <span>RSS для Дзен:</span>
          <code className="bg-gray-100 px-2 py-1 rounded text-xs">{rssUrl}</code>
          <Button size="sm" variant="ghost"
            onClick={() => { navigator.clipboard.writeText(rssUrl); toast.success("Скопировано"); }}>
            Копировать
          </Button>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: TypeScript check**

```bash
npx tsc --noEmit 2>&1 | grep Backlinks
```

Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add client/src/pages/Backlinks.tsx
git commit -m "feat: Backlinks.tsx — queue table, stats, generate/publish actions"
```

---

## Task 9: Wire everything up

**Files:**
- Modify: `server/routers.ts`
- Modify: `server/_core/index.ts`
- Create: `server/backlinkScheduler.ts`
- Modify: `client/src/App.tsx`
- Modify: `client/src/pages/Home.tsx`

- [ ] **Step 1: Register backlinksRouter in server/routers.ts**

Add import at the top of `server/routers.ts`:
```ts
import { backlinksRouter } from "./routers/backlinks";
```

Inside `appRouter = router({...})`, after `articles: articlesRouter,` add:
```ts
  backlinks: backlinksRouter,
```

- [ ] **Step 2: Add RSS route + scheduler init to server/_core/index.ts**

Add imports at the top of `server/_core/index.ts`:
```ts
import { getLastNPublished } from "../backlinks.db";
import { buildRssFeed } from "../publishers/rss";
import { initBacklinkScheduler } from "../backlinkScheduler";
```

Add RSS route BEFORE `registerOAuthRoutes(app)` (line ~92):
```ts
  app.get("/rss/dzen", async (_req, res) => {
    try {
      const posts = await getLastNPublished("dzen", 20);
      res.set("Content-Type", "application/rss+xml; charset=utf-8");
      res.send(buildRssFeed(posts));
    } catch {
      res.status(500).send("RSS error");
    }
  });
```

In `server.listen(port, () => {...})` callback, after `initContentScheduler()`:
```ts
    initBacklinkScheduler();
```

- [ ] **Step 3: Create backlinkScheduler.ts**

```ts
import cron from "node-cron";
import { publishNext } from "./publishers/pub-index";

let initialized = false;

export function initBacklinkScheduler(): void {
  if (initialized) return;
  initialized = true;

  // Дзен: every day at 10:00 MSK
  cron.schedule("0 10 * * *", async () => {
    console.log("[BacklinkScheduler] publishNext dzen");
    await publishNext("dzen").catch(err => console.error("[BacklinkScheduler] dzen:", err));
  }, { timezone: "Europe/Moscow" });

  // Spark: Mon/Wed/Fri at 11:00 MSK
  cron.schedule("0 11 * * 1,3,5", async () => {
    console.log("[BacklinkScheduler] publishNext spark");
    await publishNext("spark").catch(err => console.error("[BacklinkScheduler] spark:", err));
  }, { timezone: "Europe/Moscow" });

  // Yandex Q: Mon/Thu at 12:00 MSK
  cron.schedule("0 12 * * 1,4", async () => {
    console.log("[BacklinkScheduler] publishNext kw");
    await publishNext("kw").catch(err => console.error("[BacklinkScheduler] kw:", err));
  }, { timezone: "Europe/Moscow" });

  console.log("[BacklinkScheduler] Initialized — Дзен daily 10:00 MSK, Spark MWF 11:00, Q Mon/Thu 12:00");
}
```

- [ ] **Step 4: Add route in App.tsx**

In `client/src/App.tsx`:

Add import:
```ts
import Backlinks from "@/pages/Backlinks";
```

In `<Switch>`, after the `/seo-tracker` route:
```tsx
<Route path="/backlinks" component={Backlinks} />
```

- [ ] **Step 5: Add nav button in Home.tsx**

In `client/src/pages/Home.tsx`, in the nav buttons section, after the Статьи button:
```tsx
<Button
  onClick={() => navigate('/backlinks')}
  className="bg-white text-blue-600 hover:bg-blue-50 font-semibold"
>
  Backlinks
</Button>
```

- [ ] **Step 6: Full TypeScript check**

```bash
cd /Users/evgenijgrudev/strategy-dashboard
npx tsc --noEmit 2>&1
```

Expected: zero errors. Fix any that appear (usually import path mismatches).

- [ ] **Step 7: Smoke test**

```bash
npm run dev
```

1. Open `http://localhost:3000` → click "Backlinks" → stats bar shows (all zeros is correct)
2. Select Дзен, click "+ Генерировать" → row appears with `pending` status (content generation takes ~5-10s)
3. Click "Publish" on a pending row → status changes to `publishing`, then `published` or `failed`
4. If `failed`, check `/tmp/backlinks-error-dzen-*.png` to see what the editor looked like
5. Visit `http://localhost:3000/rss/dzen` → valid XML returned (empty channel if no published posts yet)

- [ ] **Step 8: One-time RSS setup in Дзен Studio (manual)**

After first Дзен article is successfully published:
1. Go to `https://dzen.ru/profile/editor/studio`
2. Navigate to Источники → RSS
3. Enter: `https://{your-dashboard-host}/rss/dzen`
4. Дзен will auto-import new articles on a schedule even if Playwright fails

- [ ] **Step 9: Commit**

```bash
git add server/routers.ts server/_core/index.ts server/backlinkScheduler.ts client/src/App.tsx client/src/pages/Home.tsx
git commit -m "feat: wire backlinks — RSS route, cron scheduler, router, nav link"
```

---

## Post-Implementation Checklist

- [ ] Cookie extractor returns > 5 cookies: `python3 server/publishers/extract-cookies.py`
- [ ] Generate + queue works via UI: click "+ Генерировать" and verify DB row
- [ ] Manual publish works: click "Publish" and check for screenshot in `/tmp/` on failure
- [ ] RSS endpoint returns valid XML: `curl http://localhost:3000/rss/dzen`
- [ ] Register RSS in Дзен Studio (one-time manual step above)

## Known Risks

| Risk | Mitigation |
|------|-----------|
| Dzen/Spark/Кью DOM structure changes | Screenshot saved at `/tmp/backlinks-error-{platform}-{ts}.png` — inspect and update selectors in publisher files |
| Safari cookies expire | Re-login to Yandex/Дзен in Safari → extractor auto-refreshes on next publish |
| Puppeteer `keyboard.type()` rejected by contenteditable | Fall back to CDP `Input.insertText` via `page.keyboard.sendCharacter()` loop, or switch to headless=false for debugging |
| Spark.ru OAuth redirect | Fresh Yandex login in Safari refreshes `.yandex.ru` session cookies used by Spark |
| Yandex Q selector mismatch | Navigate manually in browser, DevTools to find current answer button selector, update `kw.ts` |
