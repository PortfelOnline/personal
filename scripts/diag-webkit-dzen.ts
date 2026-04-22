import { webkit } from "playwright";
import { readFileSync } from "fs";
import { resolve } from "path";

async function main() {
  const raw = [".env.local", ".env"].flatMap(f => {
    try { return readFileSync(resolve(process.cwd(), f), "utf-8").split("\n"); } catch { return []; }
  });
  const env: Record<string, string> = {};
  for (const line of raw) {
    const m = line.match(/^([A-Z_][A-Z0-9_]*)=(.*)$/);
    if (m) env[m[1]] = m[2].replace(/^['"]|['"]$/g, "");
  }
  process.env.DATABASE_URL = process.env.DATABASE_URL ?? env["DATABASE_URL"];

  const { getCookies } = await import("../server/publishers/cookie-extractor");
  const cookies = await getCookies();
  const dzenCookies = cookies.filter((c: any) =>
    c.domain.includes("dzen.ru") || c.domain.includes("yandex.ru") || c.domain.includes("yandex.com")
  );
  console.log(`Loaded ${dzenCookies.length} cookies`);

  const browser = await webkit.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1280, height: 800 },
    userAgent: "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.3 Safari/605.1.15",
  });
  await context.addCookies(dzenCookies.map((c: any) => ({
    name: c.name,
    value: c.value,
    domain: c.domain.startsWith(".") ? c.domain : `.${c.domain}`,
    path: c.path || "/",
    expires: c.expires ?? -1,
    httpOnly: c.httpOnly ?? false,
    secure: c.secure ?? true,
    sameSite: (c.sameSite as any) ?? "None",
  })));

  const page = await context.newPage();

  // 1. Go to dzen.ru main page
  console.log("\n=== dzen.ru main ===");
  await page.goto("https://dzen.ru", { waitUntil: "domcontentloaded", timeout: 30000 });
  await page.waitForTimeout(3000);
  console.log("URL:", page.url());
  await page.screenshot({ path: "/tmp/webkit-dzen-main.png" });

  // Check if logged in
  const isLoggedIn = await page.evaluate(() => {
    // Look for user avatar / profile link indicating logged in state
    const selectors = [
      '[class*="user-avatar"]',
      '[class*="userAvatar"]',
      '[data-testid*="user"]',
      '[aria-label*="профиль"]',
      '[aria-label*="Профиль"]',
      'img[alt*="аватар"]',
    ];
    for (const sel of selectors) {
      if (document.querySelector(sel)) return `logged-in (found: ${sel})`;
    }
    // Check for login/register button
    const loginBtns = document.querySelectorAll('a[href*="passport"], button[class*="login"], a[class*="login"]');
    return loginBtns.length ? `NOT logged in (found ${loginBtns.length} login buttons)` : "unknown";
  });
  console.log("Login state:", isLoggedIn);

  // 2. Try different editor URLs
  const editorUrls = [
    "https://dzen.ru/editor",
    "https://dzen.ru/editor/create",
    "https://dzen.ru/profile/editor/articles/create",
    "https://studio.dzen.ru/",
  ];

  for (const url of editorUrls) {
    console.log(`\n=== ${url} ===`);
    try {
      await page.goto(url, { waitUntil: "domcontentloaded", timeout: 15000 });
      await page.waitForTimeout(2000);
      console.log("Final URL:", page.url());
      console.log("Title:", await page.title());
      const fname = url.replace(/[^a-z0-9]/gi, "_").substring(0, 30);
      await page.screenshot({ path: `/tmp/webkit-dzen-${fname}.png` });
    } catch (e: any) {
      console.log("Error:", e.message.substring(0, 100));
    }
  }

  await browser.close();
}

main().catch(console.error);
