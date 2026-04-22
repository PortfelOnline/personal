import puppeteer from "puppeteer-extra";
import StealthPlugin from "puppeteer-extra-plugin-stealth";
import { execFileSync } from "child_process";
import { mkdirSync, existsSync, rmSync } from "fs";
import { homedir } from "os";
import path from "path";

puppeteer.use(StealthPlugin() as any);

const CHROME_PATH = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const SRC_PROFILE = path.join(homedir(), "Library/Application Support/Google/Chrome/Default");
const TMP_PROFILE  = "/tmp/puppeteer-dzen-profile";

async function main() {
  // (Re)create temp profile from Chrome Default
  if (existsSync(TMP_PROFILE)) {
    rmSync(TMP_PROFILE, { recursive: true });
    console.log("Removed old temp profile");
  }
  mkdirSync(TMP_PROFILE, { recursive: true });
  console.log("Copying Chrome profile (excluding caches)...");
  execFileSync("rsync", [
    "-a", "--quiet",
    "--exclude=Cache", "--exclude=Code Cache", "--exclude=GPUCache",
    "--exclude=Service Worker", "--exclude=VideoDecodeStats",
    "--exclude=Crashpad", "--exclude=BrowserMetrics",
    SRC_PROFILE + "/",
    TMP_PROFILE + "/Default/",
  ]);
  console.log("Profile copied.");

  const browser = await (puppeteer as any).launch({
    headless: true,
    executablePath: CHROME_PATH,
    userDataDir: TMP_PROFILE,
    args: [
      "--no-sandbox",
      "--disable-setuid-sandbox",
      "--profile-directory=Default",
    ],
  });

  const page = await browser.newPage();
  await page.setViewport({ width: 1280, height: 800 });

  console.log("Navigating to dzen.ru...");
  await page.goto("https://dzen.ru", { waitUntil: "domcontentloaded", timeout: 30000 });
  await new Promise(r => setTimeout(r, 3000));
  const url = page.url();
  console.log("URL:", url);
  await page.screenshot({ path: "/tmp/diag-chrome-dzen.png" });
  console.log("Screenshot: /tmp/diag-chrome-dzen.png");

  // Check login state
  const title = await page.title();
  console.log("Page title:", title);

  const bodyText = await page.evaluate(() => document.body?.innerText?.substring(0, 500));
  console.log("Body preview:", bodyText?.substring(0, 200));

  await browser.close();
}

main().catch(console.error);
