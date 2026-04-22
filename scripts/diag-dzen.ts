import puppeteer from "puppeteer-extra";
import StealthPlugin from "puppeteer-extra-plugin-stealth";
import { readFileSync } from "fs";
import { resolve } from "path";

puppeteer.use(StealthPlugin() as any);

async function main() {
  // Load env
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
  console.log(`Loaded ${dzenCookies.length} Dzen/Yandex cookies`);

  const browser = await (puppeteer as any).launch({
    headless: true,
    executablePath: "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    args: ["--no-sandbox", "--disable-setuid-sandbox"],
  });
  const page = await browser.newPage();
  await page.setViewport({ width: 1280, height: 800 });

  await page.setCookie(...dzenCookies.map((c: any) => ({
    name: c.name, value: c.value, domain: c.domain, path: c.path,
    expires: c.expires, httpOnly: c.httpOnly, secure: c.secure,
  })));

  // Go to dzen.ru main page first
  console.log("Navigating to dzen.ru...");
  await page.goto("https://dzen.ru", { waitUntil: "domcontentloaded", timeout: 30000 });
  const url1 = page.url();
  console.log("URL after dzen.ru:", url1);
  await page.screenshot({ path: "/tmp/diag-dzen-main.png" });
  console.log("Screenshot: /tmp/diag-dzen-main.png");

  // Check if logged in
  const loginLink = await page.$('a[href*="passport.yandex"], [data-stat="login"], [class*="Login"]');
  console.log("Login button visible?", !!loginLink);

  // Check user avatar / profile button
  const avatar = await page.$('[class*="Avatar"], [class*="avatar"], [class*="user-pic"], [aria-label*="Профиль"]');
  console.log("User profile/avatar found?", !!avatar);

  // Try editor URL
  console.log("\nNavigating to editor...");
  await page.goto("https://dzen.ru/editor", { waitUntil: "networkidle2", timeout: 20000 });
  const url2 = page.url();
  console.log("URL after /editor:", url2);
  await page.screenshot({ path: "/tmp/diag-dzen-editor.png" });
  console.log("Screenshot: /tmp/diag-dzen-editor.png");

  await new Promise(r => setTimeout(r, 3000));
  await browser.close();
}

main().catch(console.error);
