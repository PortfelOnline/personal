const puppeteer = require('puppeteer');

(async () => {
  const browser = await puppeteer.launch({ headless: 'new', args: ['--no-sandbox'] });
  const page = await browser.newPage();
  await page.setViewport({ width: 1440, height: 900, deviceScaleFactor: 1.5 });

  await page.goto('http://localhost:3000/api/dev/login', { waitUntil: 'domcontentloaded', timeout: 10000 });
  await new Promise(r => setTimeout(r, 800));
  await page.goto('http://localhost:3000/generator', { waitUntil: 'domcontentloaded', timeout: 10000 });
  await new Promise(r => setTimeout(r, 2500));

  // Select Facebook platform
  const platformBtns = await page.$$('button');
  for (const btn of platformBtns) {
    const text = await btn.evaluate(el => el.textContent?.trim());
    if (text?.includes('Facebook')) { await btn.click(); break; }
  }
  await new Promise(r => setTimeout(r, 300));

  // Select Feed Post format
  for (const btn of await page.$$('button')) {
    const text = await btn.evaluate(el => el.textContent?.trim());
    if (text?.includes('Feed Post')) { await btn.click(); break; }
  }
  await new Promise(r => setTimeout(r, 300));

  // Select Real Estate industry
  for (const btn of await page.$$('button')) {
    const text = await btn.evaluate(el => el.textContent?.trim());
    if (text?.includes('Real Estate')) { await btn.click(); break; }
  }
  await new Promise(r => setTimeout(r, 300));

  // Generate content
  const genBtn = await page.$('button.bg-gradient-to-r');
  await genBtn.click();
  console.log('Generating FB post...');
  // Wait until Generate button stops being disabled (content done)
  await page.waitForFunction(
    () => !document.querySelector('button.bg-gradient-to-r')?.disabled,
    { timeout: 60000 }
  );
  await new Promise(r => setTimeout(r, 1000));

  // Generate Image
  const allBtns = await page.$$('button');
  for (const btn of allBtns) {
    const text = await btn.evaluate(el => el.textContent?.trim());
    if (text?.includes('Generate Image')) { await btn.click(); break; }
  }
  console.log('Generating image (DALL-E)...');
  // Wait until the image actually appears in the DOM
  await page.waitForSelector('img[alt="Generated visual"]', { timeout: 90000 });
  console.log('Image ready!');

  // Save to Library
  const saveBtns = await page.$$('button');
  for (const btn of saveBtns) {
    const text = await btn.evaluate(el => el.textContent?.trim());
    if (text?.includes('Save Draft')) {
      await btn.click();
      console.log('Saving post...');
      await new Promise(r => setTimeout(r, 2000));
      break;
    }
  }

  // Scroll preview to top
  await page.evaluate(() => {
    document.querySelectorAll('[class*="overflow-y-auto"]').forEach(el => el.scrollTop = 0);
  });
  await new Promise(r => setTimeout(r, 600));
  await page.screenshot({ path: '/tmp/fb_post_ready.png' });
  console.log('Done!');
  await browser.close();
})().catch(e => { console.error(e.message); process.exit(1); });
