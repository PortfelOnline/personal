const puppeteer = require('puppeteer');
(async () => {
  const browser = await puppeteer.launch({ headless: 'new', args: ['--no-sandbox'] });
  const page = await browser.newPage();
  await page.setViewport({ width: 1440, height: 900, deviceScaleFactor: 1.5 });
  await page.goto('http://localhost:3000/api/dev/login', { waitUntil: 'domcontentloaded', timeout: 10000 });
  await new Promise(r => setTimeout(r, 800));
  await page.goto('http://localhost:3000/generator', { waitUntil: 'domcontentloaded', timeout: 10000 });
  await new Promise(r => setTimeout(r, 3000));

  const btns = await page.$$('button');
  for (const btn of btns) {
    const text = await btn.evaluate(el => el.textContent.trim());
    if (text && text.length < 60) console.log('BTN:', JSON.stringify(text));
  }

  await page.screenshot({ path: '/tmp/generator_state.png' });
  await browser.close();
})().catch(e => { console.error(e.message); process.exit(1); });
