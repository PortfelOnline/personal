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

  // Go to main dzen.ru and look for "Write" / "Create" button
  await page.goto("https://dzen.ru", { waitUntil: "domcontentloaded", timeout: 30000 });
  await page.waitForTimeout(3000);
  await page.screenshot({ path: "/tmp/dzen-create-1-main.png" });

  // Find all links/buttons related to creating content
  const createLinks = await page.evaluate(() => {
    const items: string[] = [];
    document.querySelectorAll('a, button').forEach(el => {
      const text = el.textContent?.trim() || "";
      const href = (el as HTMLAnchorElement).href || "";
      if (
        text.match(/напис|создат|новая|статья|публик|write|create|new|post/i) ||
        href.match(/create|new|write|article|post|publish/i)
      ) {
        items.push(`[${el.tagName}] "${text.substring(0, 50)}" → ${href.substring(0, 80)}`);
      }
    });
    return items.slice(0, 20);
  });
  console.log("Create-related elements on dzen.ru:");
  createLinks.forEach(l => console.log(" ", l));

  // Try going to user profile/channel
  await page.goto("https://dzen.ru/profile", { waitUntil: "domcontentloaded", timeout: 20000 });
  await page.waitForTimeout(2000);
  console.log("\n/profile URL:", page.url());
  await page.screenshot({ path: "/tmp/dzen-create-2-profile.png" });

  // Check profile page for create button
  const profileLinks = await page.evaluate(() => {
    const items: string[] = [];
    document.querySelectorAll('a, button').forEach(el => {
      const text = el.textContent?.trim() || "";
      const href = (el as HTMLAnchorElement).href || "";
      if (
        text.match(/напис|создат|новая|статья|публик|write|create|new|post/i) ||
        href.match(/create|new|write|article|post|publish/i)
      ) {
        items.push(`[${el.tagName}] "${text.substring(0, 50)}" → ${href.substring(0, 80)}`);
      }
    });
    return items.slice(0, 20);
  });
  console.log("Create-related on /profile:");
  profileLinks.forEach(l => console.log(" ", l));

  // Try the pencil/write icon click on main page
  await page.goto("https://dzen.ru", { waitUntil: "domcontentloaded", timeout: 30000 });
  await page.waitForTimeout(3000);

  // Click the settings/write icon (top right area)
  const writeBtn = await page.$('[data-testid*="write"], [aria-label*="написать"], [aria-label*="создать"], [title*="написать"]');
  if (writeBtn) {
    console.log("\nFound write button, clicking...");
    await writeBtn.click();
    await page.waitForTimeout(2000);
    console.log("After click URL:", page.url());
    await page.screenshot({ path: "/tmp/dzen-create-3-after-click.png" });
  }

  // Check network requests for article creation endpoint
  console.log("\nChecking page source for editor URL hints...");
  const src = await page.content();
  const editorUrls = src.match(/(?:\/editor[/\w-]*|\/publish[/\w-]*|\/articles\/new[/\w-]*)/g) || [];
  const unique = [...new Set(editorUrls)].slice(0, 15);
  console.log("Editor-like URLs in HTML:", unique);

  await browser.close();
}

main().catch(console.error);
