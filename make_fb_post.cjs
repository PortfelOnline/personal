const puppeteer = require('puppeteer');

(async () => {
  const browser = await puppeteer.launch({ headless: 'new', args: ['--no-sandbox'] });
  const page = await browser.newPage();
  await page.setViewport({ width: 1440, height: 900, deviceScaleFactor: 1.5 });

  await page.goto('http://localhost:3000/api/dev/login', { waitUntil: 'domcontentloaded', timeout: 10000 });
  await new Promise(r => setTimeout(r, 800));

  // Check Meta accounts page
  await page.goto('http://localhost:3000/accounts', { waitUntil: 'domcontentloaded', timeout: 10000 });
  await new Promise(r => setTimeout(r, 1500));
  await page.screenshot({ path: '/tmp/meta_accounts.png' });
  console.log('Meta accounts page captured');

  await browser.close();
})().catch(e => { console.error(e.message); process.exit(1); });
