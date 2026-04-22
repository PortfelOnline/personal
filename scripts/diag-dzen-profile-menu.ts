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

  const browser = await webkit.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1280, height: 800 },
    userAgent: "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.3 Safari/605.1.15",
  });
  await context.addCookies(dzenCookies.map((c: any) => ({
    name: c.name, value: c.value,
    domain: c.domain.startsWith(".") ? c.domain : `.${c.domain}`,
    path: c.path || "/", expires: c.expires ?? -1,
    httpOnly: c.httpOnly ?? false, secure: c.secure ?? true,
    sameSite: (c.sameSite as any) ?? "None",
  })));

  const page = await context.newPage();
  await page.goto("https://dzen.ru", { waitUntil: "domcontentloaded", timeout: 30000 });
  await page.waitForTimeout(3000);

  // Click profile icon (top right)
  const profileIcon = await page.$('[data-testid*="user"], [aria-label*="профиль"], [aria-label*="аккаунт"], svg[class*="user"], [class*="UserIcon"], [class*="Profile"]');
  if (profileIcon) {
    console.log("Clicking profile icon...");
    await profileIcon.click();
    await page.waitForTimeout(2000);
    await page.screenshot({ path: "/tmp/dzen-profile-menu.png" });

    // Get all menu items
    const menuItems = await page.evaluate(() => {
      const items: string[] = [];
      document.querySelectorAll('a, button, [role="menuitem"]').forEach(el => {
        const text = el.textContent?.trim() || "";
        const href = (el as HTMLAnchorElement).href || "";
        if (text && text.length < 100) {
          items.push(`"${text}" → ${href.substring(0, 80)}`);
        }
      });
      return items.slice(0, 30);
    });
    console.log("Menu items after profile click:");
    menuItems.forEach(i => console.log(" ", i));
  } else {
    console.log("Profile icon not found");

    // Try clicking the rightmost icon in the header
    const icons = await page.$$('header a, header button, [class*="header"] a, [class*="Header"] button');
    console.log(`Found ${icons.length} header elements`);

    for (const icon of icons.slice(-5)) {
      const text = await icon.textContent();
      const href = await icon.getAttribute("href");
      console.log(`  Header item: "${text?.trim()?.substring(0, 30)}" → ${href}`);
    }

    // Screenshot header
    await page.screenshot({ path: "/tmp/dzen-header.png" });
  }

  // Also try navigating to known author studio URLs
  const studioUrls = [
    "https://dzen.ru/my/articles",
    "https://dzen.ru/my/stats",
    "https://dzen.ru/my",
  ];
  for (const u of studioUrls) {
    await page.goto(u, { waitUntil: "domcontentloaded", timeout: 15000 });
    await page.waitForTimeout(1500);
    const url = page.url();
    const title = await page.title();
    console.log(`\n${u} → ${url} (${title})`);
    const fname = u.replace(/[^a-z0-9]/gi, "_").substring(0, 25);
    await page.screenshot({ path: `/tmp/dzen-studio-${fname}.png` });

    // Look for create/new article button
    const creates = await page.evaluate(() => {
      const items: string[] = [];
      document.querySelectorAll('a, button').forEach(el => {
        const text = el.textContent?.trim() || "";
        const href = (el as HTMLAnchorElement).href || "";
        if (text.match(/новая|создат|напис|write|create|new|статья|публик/i) || href.match(/create|new|write/i)) {
          items.push(`"${text.substring(0, 40)}" → ${href.substring(0, 80)}`);
        }
      });
      return items;
    });
    if (creates.length) {
      console.log("  Create elements:", creates);
    }
  }

  await browser.close();
}

main().catch(console.error);
