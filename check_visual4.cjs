const puppeteer = require('puppeteer');

(async () => {
  const browser = await puppeteer.launch({ headless: 'new', args: ['--no-sandbox'] });
  const page = await browser.newPage();
  await page.setViewport({ width: 1440, height: 900, deviceScaleFactor: 1.5 });

  await page.goto('http://localhost:3000/api/dev/login', { waitUntil: 'domcontentloaded', timeout: 10000 });
  await new Promise(r => setTimeout(r, 800));
  await page.goto('http://localhost:3000/generator', { waitUntil: 'domcontentloaded', timeout: 10000 });
  await new Promise(r => setTimeout(r, 2000));

  const genBtn = await page.$('button.bg-gradient-to-r');
  await genBtn.click();
  await new Promise(r => setTimeout(r, 12000));

  const allButtons = await page.$$('button');
  for (const btn of allButtons) {
    const text = await btn.evaluate(el => el.textContent?.trim());
    if (text?.includes('Generate Image')) { await btn.click(); break; }
  }

  await new Promise(r => setTimeout(r, 20000));

  // Scroll preview panel mid-way to see image
  await page.evaluate(() => {
    const scrollables = document.querySelectorAll('[class*="overflow-y-auto"]');
    scrollables.forEach(el => { el.scrollTop = 600; }); // scroll to middle
  });
  await new Promise(r => setTimeout(r, 500));
  await page.screenshot({ path: '/tmp/gen_image_visible.png' });
  console.log('Done');

  await browser.close();
})().catch(e => { console.error(e.message); process.exit(1); });
