import { webkit } from "playwright";
import { getCookies } from "./cookie-extractor";
import type { BacklinkPost } from "../../drizzle/schema";

export async function publishToSpark(post: BacklinkPost): Promise<string> {
  const cookies = await getCookies();
  const sparkCookies = cookies.filter((c: any) =>
    c.domain.includes("yandex.ru") || c.domain.includes("yandex.com") || c.domain.includes("spark.ru")
  );

  const browser = await webkit.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1280, height: 800 },
    userAgent: "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.3 Safari/605.1.15",
  });
  await context.addCookies(sparkCookies.map((c: any) => ({
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
  try {
    await page.goto("https://spark.ru/post/new", { waitUntil: "domcontentloaded", timeout: 30000 });
    await page.waitForTimeout(2000);

    if (page.url().includes("passport.yandex") || page.url().includes("id.yandex")) {
      throw new Error("Spark session expired — log in to Yandex in Safari and retry");
    }

    const titleSel = 'input[name="title"], input[placeholder*="аголов"]';
    await page.waitForSelector(titleSel, { timeout: 15000 });
    await page.click(titleSel);
    await page.keyboard.type(post.title ?? "Статья об объектах недвижимости", { delay: 30 });

    const allEditors = await page.$$('[contenteditable="true"]');
    const bodyEditor  = allEditors[allEditors.length - 1];
    await bodyEditor.click();
    await page.keyboard.type(post.article ?? "", { delay: 10 });
    await page.waitForTimeout(2000);

    const publishBtn = await page.waitForSelector('button[type="submit"], button[class*="submit"]', { timeout: 10000 });
    await publishBtn?.click();
    await page.waitForURL("**/spark.ru/**", { timeout: 30000 });

    return page.url();
  } catch (err) {
    await page.screenshot({ path: `/tmp/backlinks-error-spark-${Date.now()}.png` }).catch(() => {});
    throw err;
  } finally {
    await browser.close();
  }
}
