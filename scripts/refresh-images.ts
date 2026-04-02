/**
 * refresh-images.ts
 * Regenerates Flux images for already-published articles using article-specific prompts.
 * Does NOT rewrite content — only replaces images.
 */
import 'dotenv/config';
import * as wp from '../server/_core/wordpress';
import * as wordpressDb from '../server/wordpress.db';
import { findAndInjectImages } from '../server/routers/articles';

const USER_ID = 1;
const DELAY_MS = 8000; // between articles to avoid rate limits

const URLS = process.argv.slice(2).length
  ? process.argv.slice(2)
  : [
      // Default: first 20 HIGH articles from early batches (no bodyText at the time)
      'https://kadastrmap.info/kadastr/kadastrovyj-pasport/',
      'https://kadastrmap.info/kadastr/kadastrovyj-pasport-kvartiry/',
      'https://kadastrmap.info/kadastr/kadastrovyj-pasport-na-dom/',
      'https://kadastrmap.info/kadastr/kadastrovyj-pasport-na-zemelnyj-uchastok/',
      'https://kadastrmap.info/kadastr/kadastrovyj-pasport-na-zemlyu/',
      'https://kadastrmap.info/kadastr/kadastrovyj-pasport-zemelnogo-uchastka/',
      'https://kadastrmap.info/kadastr/kadastrovyj-pasport-na-kvartiru/',
      'https://kadastrmap.info/kadastr/kadastrovyj-pasport-onlajn/',
      'https://kadastrmap.info/kadastr/kadastrovyj-pasport-cherez-internet/',
      'https://kadastrmap.info/kadastr/kadastrovyj-pasport-gde-poluchit/',
      'https://kadastrmap.info/kadastr/wypiska-iz-egrn-na-kvartiru/',
      'https://kadastrmap.info/kadastr/vypiska-iz-egrn-bystro/',
      'https://kadastrmap.info/kadastr/vypiska-iz-egrn-stoimost/',
      'https://kadastrmap.info/kadastr/vypiska-iz-egrn-na-zemlyu/',
      'https://kadastrmap.info/kadastr/vypiska-iz-egrn-na-nedvizhimost/',
      'https://kadastrmap.info/kadastr/vypiska-iz-egrn-zakazat-onlajn/',
      'https://kadastrmap.info/kadastr/kadastrovaya-spravka/',
      'https://kadastrmap.info/kadastr/kadastrovaya-spravka-iz-egrn/',
      'https://kadastrmap.info/kadastr/kadastrovaya-vypiska/',
      'https://kadastrmap.info/kadastr/kadastrovaya-vypiska-na-zemlyu/',
    ];

async function sleep(ms: number) {
  return new Promise(r => setTimeout(r, ms));
}

const accounts = await wordpressDb.getUserWordpressAccounts(USER_ID);
const account = accounts[0];
if (!account) throw new Error('No WP account for userId=1');

console.log(`[refresh-images] Account: ${account.siteUrl}`);
console.log(`[refresh-images] Processing ${URLS.length} articles\n`);

let ok = 0, fail = 0;

for (const url of URLS) {
  const slug = new URL(url).pathname.replace(/\/$/, '').split('/').pop() || '';
  try {
    const post = await wp.findPostBySlug(account.siteUrl, account.username, account.appPassword, slug);
    if (!post) {
      console.log(`[${slug}] ⚠️  Not found in WP, skipping`);
      continue;
    }

    const html: string = post.content?.rendered ?? '';
    if (!html) {
      console.log(`[${slug}] ⚠️  Empty content, skipping`);
      continue;
    }

    console.log(`[${slug}] Generating Flux images...`);
    const { html: newHtml, featuredMediaId } = await findAndInjectImages(
      account.siteUrl,
      account.username,
      account.appPassword,
      slug,
      post.title?.rendered ?? slug,
      html,
      3,
    );

    await wp.updatePost(account.siteUrl, account.username, account.appPassword, post.id, {
      content: newHtml,
      ...(featuredMediaId ? { featured_media: featuredMediaId } : {}),
    });

    console.log(`[${slug}] ✅ Images refreshed → ${url}`);
    ok++;
  } catch (e: any) {
    console.error(`[${slug}] ❌ Error: ${e.message}`);
    fail++;
  }

  await sleep(DELAY_MS);
}

console.log(`\n[refresh-images] DONE: ${ok} ok, ${fail} failed`);
