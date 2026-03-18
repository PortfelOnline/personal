const puppeteer = require('puppeteer');

(async () => {
  const browser = await puppeteer.launch({ headless: 'new', args: ['--no-sandbox'] });
  const page = await browser.newPage();
  await page.setViewport({ width: 1440, height: 900, deviceScaleFactor: 1.5 });

  await page.goto('http://localhost:3000/api/dev/login', { waitUntil: 'domcontentloaded', timeout: 10000 });
  await new Promise(r => setTimeout(r, 800));
  await page.goto('http://localhost:3000/generator', { waitUntil: 'domcontentloaded', timeout: 10000 });
  await new Promise(r => setTimeout(r, 2000));

  // Click Generate button
  const genBtn = await page.$('button.bg-gradient-to-r');
  if (genBtn) {
    await genBtn.click();
    await new Promise(r => setTimeout(r, 12000));

    // Scroll the preview panel down to see the buttons
    await page.evaluate(() => {
      const cardContent = document.querySelectorAll('[class*="overflow-y-auto"]');
      cardContent.forEach(el => el.scrollTop = el.scrollHeight);
    });
    await new Promise(r => setTimeout(r, 500));
    await page.screenshot({ path: '/tmp/gen_scrolled.png', fullPage: false });
    console.log('Captured: preview scrolled down');
  }

  await browser.close();
})().catch(e => { console.error(e.message); process.exit(1); });
