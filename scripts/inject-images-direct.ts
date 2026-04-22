/**
 * Inject already-uploaded images directly into kak-snyat-obremenenie post
 * Images already in WP media: 334317, 334319, 334320
 */
import 'dotenv/config';
import axios from 'axios';

const POST_ID = 332987;
const SLUG = 'kak-snyat-obremenenie-s-ipotechnoj-kvartiry';
const SITE_URL = 'https://kadastrmap.info';
const WP_USER = 'grudeves_vf97s8yc';
const WP_PASS = process.env.WP_APP_PASSWORD_KAD ?? 'uX$8LCdpGKH9Rcd';
const AUTH = 'Basic ' + Buffer.from(`${WP_USER}:${WP_PASS}`).toString('base64');
const API = `${SITE_URL}/wp-json/wp/v2`;

const IMAGE_IDS = [334317, 334319, 334320];

async function main() {
  // Fetch current content
  const r = await axios.get(`${API}/posts/${POST_ID}?_fields=id,content,title`, {
    headers: { Authorization: AUTH },
    timeout: 20000,
  });
  let html: string = r.data.content.rendered;
  const words = html.replace(/<[^>]+>/g, ' ').split(/\s+/).filter(Boolean).length;
  console.log(`words=${words} imgs=${(html.match(/<img /g) || []).length}`);

  // Fetch image URLs from WP
  const imgBlocks: string[] = [];
  for (const id of IMAGE_IDS) {
    const ir = await axios.get(`${API}/media/${id}?_fields=id,source_url,alt_text`, {
      headers: { Authorization: AUTH },
      timeout: 10000,
    });
    const url = ir.data.source_url;
    const alt = ir.data.alt_text || SLUG;
    imgBlocks.push(
      `<figure class="wp-block-image size-large"><img src="${url}" alt="${alt}" class="wp-image-${id}" loading="lazy"/></figure>`
    );
    console.log(`img ${id}: ${url}`);
  }

  // Inject after every 3rd H2 (similar to injectImagesAfterH2s logic)
  const h2Matches = [...html.matchAll(/<h2[^>]*>[\s\S]*?<\/h2>/gi)];
  const insertPositions = [2, 5, 8].map(i => h2Matches[i]?.index).filter(Boolean) as number[];

  let offset = 0;
  insertPositions.forEach((pos, i) => {
    if (i >= imgBlocks.length) return;
    const insertAt = pos + offset;
    const after = html.indexOf('</h2>', insertAt) + 5;
    html = html.slice(0, after) + '\n' + imgBlocks[i] + '\n' + html.slice(after);
    offset += imgBlocks[i].length + 2;
  });

  // If no H2s found, prepend images
  if (insertPositions.length === 0) {
    html = imgBlocks.join('\n') + '\n' + html;
  }

  const newImgs = (html.match(/<img /g) || []).length;
  console.log(`After injection: imgs=${newImgs}`);

  // Update WP with retry
  for (let attempt = 1; attempt <= 3; attempt++) {
    try {
      await axios.post(`${API}/posts/${POST_ID}`, {
        content: html,
        featured_media: IMAGE_IDS[0],
      }, {
        headers: { Authorization: AUTH, 'Content-Type': 'application/json' },
        timeout: 30000,
      });
      console.log(`✅ Updated: ${SITE_URL}/kadastr/${SLUG}/`);
      return;
    } catch (e: any) {
      console.log(`attempt ${attempt} failed: ${e.message?.slice(0, 60)}`);
      if (attempt < 3) await new Promise(r => setTimeout(r, 5000));
    }
  }
  console.error('All retries failed');
  process.exit(1);
}

main().catch(e => { console.error(e); process.exit(1); });
