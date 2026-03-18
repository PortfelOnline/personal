const puppeteer = require('puppeteer');

(async () => {
  const browser = await puppeteer.launch({ headless: 'new', args: ['--no-sandbox'] });
  const page = await browser.newPage();
  await page.setViewport({ width: 1440, height: 900, deviceScaleFactor: 1.5 });

  page.on('console', msg => { if (msg.type() === 'error') console.log('BROWSER ERR:', msg.text()); });

  await page.goto('http://localhost:3000/api/dev/login', { waitUntil: 'domcontentloaded', timeout: 10000 });
  await new Promise(r => setTimeout(r, 800));
  await page.goto('http://localhost:3000/generator', { waitUntil: 'domcontentloaded', timeout: 10000 });
  await new Promise(r => setTimeout(r, 2000));

  const genBtn = await page.$('button.bg-gradient-to-r');
  await genBtn.click();
  await new Promise(r => setTimeout(r, 12000)); // wait for content

  // Click "Generate Image" button (violet text)
  const allButtons = await page.$$('button');
  let genImgBtn = null;
  for (const btn of allButtons) {
    const text = await btn.evaluate(el => el.textContent?.trim());
    if (text?.includes('Generate Image')) { genImgBtn = btn; break; }
  }

  if (genImgBtn) {
    console.log('Found Generate Image button, clicking...');
    await genImgBtn.click();
    await new Promise(r => setTimeout(r, 20000)); // wait for DALL-E
    await page.evaluate(() => {
      document.querySelectorAll('[class*="overflow-y-auto"]').forEach(el => el.scrollTop = 0);
    });
    await new Promise(r => setTimeout(r, 500));
    await page.screenshot({ path: '/tmp/gen_with_image.png' });
    console.log('Captured: after image generated');
  } else {
    console.log('Generate Image button not found');
  }

  await browser.close();
})().catch(e => { console.error(e.message); process.exit(1); });
