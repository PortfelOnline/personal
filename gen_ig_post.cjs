const puppeteer = require('puppeteer');

(async () => {
  const browser = await puppeteer.launch({ headless: 'new', args: ['--no-sandbox'] });
  const page = await browser.newPage();
  await page.setViewport({ width: 1440, height: 900, deviceScaleFactor: 1.5 });

  await page.goto('http://localhost:3000/api/dev/login', { waitUntil: 'domcontentloaded', timeout: 10000 });
  await new Promise(r => setTimeout(r, 800));
  await page.goto('http://localhost:3000/generator', { waitUntil: 'domcontentloaded', timeout: 10000 });
  await new Promise(r => setTimeout(r, 2500));

  const clickBtn = async (contains) => {
    const btns = await page.$$('button');
    for (const btn of btns) {
      const text = await btn.evaluate(el => el.textContent.trim());
      if (text.includes(contains)) { await btn.click(); return true; }
    }
    console.log('NOT FOUND:', contains);
    return false;
  };

  await clickBtn('Instagram');       await new Promise(r => setTimeout(r, 400));
  await clickBtn('Real Estate');     await new Promise(r => setTimeout(r, 400));
  await clickBtn('Feed Post');       await new Promise(r => setTimeout(r, 400));
  await clickBtn('Objection Busting'); await new Promise(r => setTimeout(r, 400));

  // Generate content
  await clickBtn('Generate');
  console.log('Generating IG post...');
  // Wait until Generate button stops being disabled (content done)
  await page.waitForFunction(
    () => !document.querySelector('button.bg-gradient-to-r')?.disabled,
    { timeout: 60000 }
  );
  await new Promise(r => setTimeout(r, 1000));

  // Generate Image
  await clickBtn('Generate Image');
  console.log('Generating image...');
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

  await page.evaluate(() => {
    document.querySelectorAll('[class*="overflow-y-auto"]').forEach(el => el.scrollTop = 0);
  });
  await new Promise(r => setTimeout(r, 800));
  await page.screenshot({ path: '/tmp/ig_post_ready.png' });
  console.log('Done!');
  await browser.close();
})().catch(e => { console.error(e.message); process.exit(1); });
