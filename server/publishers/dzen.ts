import { webkit } from "playwright";
import { getCookies } from "./cookie-extractor";
import type { BacklinkPost } from "../../drizzle/schema";

export async function publishToDzen(post: BacklinkPost): Promise<string> {
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
    await page.goto("https://dzen.ru/editor/create-article", { waitUntil: "domcontentloaded", timeout: 40000 });
    await page.waitForTimeout(3000);

    const curUrl = page.url();
    if (curUrl.includes("passport.yandex") || curUrl.includes("id.yandex") || curUrl.includes("sso.dzen")) {
      await page.screenshot({ path: `/tmp/backlinks-error-dzen-auth-${Date.now()}.png` });
      throw new Error("Not authenticated — open dzen.ru in Safari and ensure you are logged in, then retry");
    }

    // Wait for contenteditable editor
    await page.waitForSelector('[contenteditable="true"], [data-slate-editor="true"]', { timeout: 30000 });

    const allEditors = await page.$$('[contenteditable="true"]');
    if (!allEditors.length) throw new Error("Dzen editor not found");

    const titleText = post.title ?? "Статья о кадастре";
    await allEditors[0].click();
    await page.keyboard.type(titleText, { delay: 30 });

    if (allEditors.length > 1) {
      await allEditors[1].click();
    } else {
      await page.keyboard.press("Tab");
      await page.waitForTimeout(500);
    }
    await page.keyboard.type(post.article ?? "", { delay: 10 });
    await page.waitForTimeout(2000);

    const publishBtn = await page.waitForSelector(
      'button[data-testid="publish"], button[class*="publish"], [data-action="publish"]',
      { timeout: 15000 }
    );
    if (!publishBtn) throw new Error("Publish button not found");
    await publishBtn.click();

    await page.waitForFunction(
      () => location.href.includes("dzen.ru/a/") || location.href.includes("dzen.ru/media/"),
      { timeout: 40000 }
    );

    return page.url();
  } catch (err) {
    await page.screenshot({ path: `/tmp/backlinks-error-dzen-${Date.now()}.png` }).catch(() => {});
    throw err;
  } finally {
    await browser.close();
  }
}
