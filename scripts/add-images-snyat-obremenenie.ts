/**
 * Add FLUX images to kak-snyat-obremenenie-s-ipotechnoj-kvartiry
 * Content is good (3806 words, 10 FAQ) — only missing images
 */
import 'dotenv/config';
import axios from 'axios';
import { findAndInjectImages } from '../server/routers/articles';

const SLUG = 'kak-snyat-obremenenie-s-ipotechnoj-kvartiry';
const POST_ID = 332987;
const SITE_URL = 'https://kadastrmap.info';
const WP_USER = 'grudeves_vf97s8yc';
const WP_PASS = process.env.WP_APP_PASSWORD_KAD ?? 'uX$8LCdpGKH9Rcd';
const AUTH = 'Basic ' + Buffer.from(`${WP_USER}:${WP_PASS}`).toString('base64');
const API = `${SITE_URL}/wp-json/wp/v2`;

async function main() {
  console.log(`[img] Adding images to ${SLUG} (id=${POST_ID})`);

  const r = await axios.get(`${API}/posts/${POST_ID}?_fields=id,title,content`, {
    headers: { Authorization: AUTH },
  });
  const title: string = r.data.title.rendered;
  const html: string = r.data.content.rendered;
  const words = html.replace(/<[^>]+>/g, ' ').split(/\s+/).filter(Boolean).length;
  console.log(`[img] title="${title}" words=${words} imgs=${(html.match(/<img /g) || []).length}`);

  const { html: updatedHtml, featuredMediaId } = await findAndInjectImages(
    SITE_URL, WP_USER, WP_PASS, SLUG, title, html, 6,
  );
  const newImgs = (updatedHtml.match(/<img /g) || []).length;
  console.log(`[img] After: images=${newImgs} featuredMediaId=${featuredMediaId}`);

  if (newImgs === 0) {
    console.log('[img] No images generated, skipping WP update');
    return;
  }

  await axios.post(`${API}/posts/${POST_ID}`, {
    content: updatedHtml,
    ...(featuredMediaId ? { featured_media: featuredMediaId } : {}),
  }, {
    headers: { Authorization: AUTH, 'Content-Type': 'application/json' },
  });
  console.log(`✅ Updated: ${SITE_URL}/kadastr/${SLUG}/`);
}

main().catch(e => { console.error(e); process.exit(1); });
