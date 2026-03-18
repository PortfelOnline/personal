const puppeteer = require('puppeteer');

const pages = [
  { path: '/generator', name: 'generator' },
  { path: '/library', name: 'library' },
  { path: '/analytics', name: 'analytics' },
  { path: '/calendar', name: 'calendar' },
  { path: '/accounts', name: 'accounts' },
  { path: '/wordpress', name: 'wordpress' },
];

(async () => {
  const browser = await puppeteer.launch({ headless: 'new', args: ['--no-sandbox'] });
  const page = await browser.newPage();
  await page.setViewport({ width: 1440, height: 900, deviceScaleFactor: 1.5 });

  await page.goto('http://localhost:3000/api/dev/login', { waitUntil: 'domcontentloaded', timeout: 10000 });
  await new Promise(r => setTimeout(r, 1000));

  for (const { path, name } of pages) {
    try {
      await page.goto('http://localhost:3000' + path, { waitUntil: 'domcontentloaded', timeout: 10000 });
      await new Promise(r => setTimeout(r, 1500));
      await page.screenshot({ path: `/tmp/page_${name}.png`, fullPage: false });
      console.log('captured:', name);
    } catch (e) {
      console.error('failed:', name, e.message.slice(0, 100));
      try { await page.screenshot({ path: `/tmp/page_${name}_error.png`, fullPage: false }); } catch {}
    }
  }

  await browser.close();
})().catch(e => { console.error(e.message); process.exit(1); });
