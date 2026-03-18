const puppeteer = require('puppeteer');

(async () => {
  const browser = await puppeteer.launch({ headless: 'new', args: ['--no-sandbox'] });
  const page = await browser.newPage();
  await page.setViewport({ width: 1440, height: 900, deviceScaleFactor: 1.5 });

  await page.goto('http://localhost:3000/api/dev/login', { waitUntil: 'domcontentloaded', timeout: 10000 });
  await new Promise(r => setTimeout(r, 800));
  await page.goto('http://localhost:3000/generator', { waitUntil: 'domcontentloaded', timeout: 10000 });
  await new Promise(r => setTimeout(r, 2500));

  // 1. Generate content
  const genBtn = await page.$('button.bg-gradient-to-r');
  await genBtn.click();
  console.log('Generating content...');
  await new Promise(r => setTimeout(r, 12000));

  // 2. Click Generate Image
  const allButtons = await page.$$('button');
  for (const btn of allButtons) {
    const text = await btn.evaluate(el => el.textContent?.trim());
    if (text?.includes('Generate Image')) { await btn.click(); break; }
  }
  console.log('Generating image (DALL-E ~15s)...');
  await new Promise(r => setTimeout(r, 20000));

  // 3. Scroll preview to top to see image
  await page.evaluate(() => {
    document.querySelectorAll('[class*="overflow-y-auto"]').forEach(el => el.scrollTop = 0);
  });
  await new Promise(r => setTimeout(r, 600));
  await page.screenshot({ path: '/tmp/final_with_image.png' });
  console.log('Done!');
  await browser.close();
})().catch(e => { console.error(e.message); process.exit(1); });
