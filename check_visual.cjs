const puppeteer = require('puppeteer');

(async () => {
  const browser = await puppeteer.launch({ headless: 'new', args: ['--no-sandbox'] });
  const page = await browser.newPage();
  await page.setViewport({ width: 1440, height: 900, deviceScaleFactor: 1.5 });

  await page.goto('http://localhost:3000/api/dev/login', { waitUntil: 'domcontentloaded', timeout: 10000 });
  await new Promise(r => setTimeout(r, 800));
  await page.goto('http://localhost:3000/generator', { waitUntil: 'domcontentloaded', timeout: 10000 });
  await new Promise(r => setTimeout(r, 2000));
  await page.screenshot({ path: '/tmp/gen_loaded.png' });
  console.log('Captured: loaded state');

  // Click Generate button
  const genBtn = await page.$('button.bg-gradient-to-r');
  if (genBtn) {
    await genBtn.click();
    console.log('Clicked Generate');
    await new Promise(r => setTimeout(r, 12000)); // wait for LLM
    await page.screenshot({ path: '/tmp/gen_after_content.png' });
    console.log('Captured: after content generated');
  } else {
    console.log('Generate button not found');
  }

  await browser.close();
})().catch(e => { console.error(e.message); process.exit(1); });
