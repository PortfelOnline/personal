import { webkit } from "playwright";
import { getCookies } from "./cookie-extractor";
import type { BacklinkPost } from "../../drizzle/schema";

export async function publishToKw(post: BacklinkPost): Promise<string> {
  const cookies = await getCookies();
  const yndxCookies = cookies.filter((c: any) =>
    c.domain.includes("yandex.ru") || c.domain.includes("yandex.com")
  );

  const browser = await webkit.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1280, height: 800 },
    userAgent: "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.3 Safari/605.1.15",
  });
  await context.addCookies(yndxCookies.map((c: any) => ({
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
    const topic = encodeURIComponent((post.anchorText ?? "кадастровый номер").substring(0, 60));
    await page.goto(`https://yandex.ru/q/search?text=${topic}`, { waitUntil: "domcontentloaded", timeout: 30000 });
    await page.waitForTimeout(2000);

    let questionUrl = "";
    const links = await page.$$('a[href*="/q/"]');
    for (const link of links.slice(0, 8)) {
      const href = await link.getAttribute("href");
      if (href && !href.includes("/q/search") && href.includes("/q/")) {
        const fullUrl = href.startsWith("http") ? href : `https://yandex.ru${href}`;
        await page.goto(fullUrl, { waitUntil: "domcontentloaded", timeout: 15000 });
        questionUrl = page.url();
        break;
      }
    }
    if (!questionUrl) throw new Error("Could not find a Yandex Q question to answer");

    const answerBtnSel = 'button[data-testid="answer-button"], a[href*="answer"], button[class*="answer"]';
    const answerBtn = await page.$(answerBtnSel);
    if (!answerBtn) throw new Error("Could not find answer button on Yandex Q");
    await answerBtn.click();
    await page.waitForTimeout(1000);

    const answerEditors = await page.$$('[contenteditable="true"]');
    const answerEditor  = answerEditors[answerEditors.length - 1];
    await answerEditor.click();
    await page.keyboard.type(post.article ?? "", { delay: 10 });
    await page.waitForTimeout(1500);

    const submitSel = 'button[type="submit"], button[data-testid="submit-answer"]';
    const submit = await page.waitForSelector(submitSel, { timeout: 10000 });
    await submit?.click();
    await page.waitForTimeout(3000);

    return questionUrl;
  } catch (err) {
    await page.screenshot({ path: `/tmp/backlinks-error-kw-${Date.now()}.png` }).catch(() => {});
    throw err;
  } finally {
    await browser.close();
  }
}
