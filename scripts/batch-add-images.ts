/**
 * Batch image assignment for 33 articles missing featured images.
 * Strategy: 1) WP media library  2) Pexels with Groq-generated English query
 */
import 'dotenv/config';
import * as wp from '../server/_core/wordpress';
import * as wordpressDb from '../server/wordpress.db';
import Groq from 'groq-sdk';

const groq = new Groq({ apiKey: process.env.BUILT_IN_FORGE_API_KEY });
const PEXELS_KEY = process.env.PEXELS_API_KEY ?? '';

async function searchPexels(query: string, limit = 5) {
  if (!PEXELS_KEY) return [];
  try {
    const params = new URLSearchParams({ query, per_page: String(limit) });
    const resp = await fetch(`https://api.pexels.com/v1/search?${params}`, {
      headers: { Authorization: PEXELS_KEY },
    });
    if (!resp.ok) return [];
    const data = await resp.json() as any;
    return (data?.photos ?? []).map((p: any, i: number) => ({
      id: -(1000 + i + 1),
      url: p.src?.large2x || p.src?.large || p.src?.original,
      alt: p.alt || query,
    })).filter((m: any) => m.url);
  } catch { return []; }
}

/** Download Pexels image locally, upload buffer directly to WP REST API */
async function uploadPexelsToWp(
  siteUrl: string, username: string, appPassword: string,
  imageUrl: string, filename: string,
): Promise<{ id: number }> {
  // Download with Pexels Authorization header
  const imgResp = await fetch(imageUrl, { headers: { Authorization: PEXELS_KEY } });
  if (!imgResp.ok) throw new Error(`Pexels download HTTP ${imgResp.status}`);
  const buffer = Buffer.from(await imgResp.arrayBuffer());

  const ext = filename.match(/\.(jpe?g|png|webp)$/i)?.[1]?.toLowerCase() ?? 'jpg';
  const mime = ext === 'png' ? 'image/png' : ext === 'webp' ? 'image/webp' : 'image/jpeg';

  const auth = 'Basic ' + Buffer.from(`${username}:${appPassword}`).toString('base64');
  const uploadResp = await fetch(`${siteUrl}/wp-json/wp/v2/media`, {
    method: 'POST',
    headers: {
      Authorization: auth,
      'Content-Disposition': `attachment; filename="${filename}"`,
      'Content-Type': mime,
    },
    body: buffer,
  });
  if (!uploadResp.ok) {
    const txt = await uploadResp.text();
    throw new Error(`WP upload HTTP ${uploadResp.status}: ${txt.slice(0, 200)}`);
  }
  const media = await uploadResp.json() as any;
  return { id: media.id };
}

// Retry 1 failed article
const SLUGS_NO_IMAGE = [
  { slug: 'kadastrovaya-spravka-onlajn', title: 'Кадастровая справка онлайн' },
];

async function getPexelsQuery(title: string): Promise<string> {
  const res = await groq.chat.completions.create({
    model: 'llama-3.3-70b-versatile',
    messages: [{
      role: 'user',
      content: `Russian real estate/cadastral article: "${title}".
Write ONE short English Pexels photo search query (3-5 words max) that would find a relevant, professional, photorealistic photo for this article.
Focus on: property documents, real estate, official papers, apartments, land maps, government offices.
Return ONLY the query, nothing else.`
    }],
    max_tokens: 30,
    temperature: 0.3,
  });
  return res.choices[0].message.content?.trim().replace(/["'.]/g, '') ?? 'real estate documents';
}

async function processArticle(
  item: { slug: string; title: string },
  idx: number,
  siteUrl: string, username: string, appPassword: string,
): Promise<void> {
  console.log(`\n[${idx + 1}/${SLUGS_NO_IMAGE.length}] ${item.slug}`);

  const post = await wp.findPostBySlug(siteUrl, username, appPassword, item.slug).catch(() => null);
  if (!post) { console.log('  ✗ Post not found in WP'); return; }

  // 1. Try WP media library first
  const keywords = item.title.split(/\s+/).filter(w => w.length > 3).slice(0, 3).join(' ');
  const libraryImages = await wp.searchMedia(siteUrl, username, appPassword, keywords, 5).catch(() => []);

  if (libraryImages.length > 0) {
    await wp.updatePost(siteUrl, username, appPassword, post.id, { featured_media: libraryImages[0].id });
    console.log(`  ✓ WP library: id=${libraryImages[0].id} "${libraryImages[0].title}"`);
    return;
  }

  // 2. Pexels with Groq-generated English query
  const pexelsQuery = await getPexelsQuery(item.title);
  console.log(`  → Pexels query: "${pexelsQuery}"`);

  const pexelsImages = await searchPexels(pexelsQuery, 5);
  if (pexelsImages.length === 0) { console.log('  ✗ No Pexels results'); return; }

  const best = pexelsImages[0];
  const ext = best.url.match(/\.(jpe?g|png|webp)/i)?.[1] ?? 'jpg';
  const filename = `featured-${item.slug}.${ext}`;

  try {
    const uploaded = await uploadPexelsToWp(siteUrl, username, appPassword, best.url, filename);
    await wp.updatePost(siteUrl, username, appPassword, post.id, { featured_media: uploaded.id });
    console.log(`  ✓ Pexels → WP id=${uploaded.id} query="${pexelsQuery}"`);
  } catch (e: any) {
    console.warn(`  ✗ Upload failed: ${e?.message}`);
  }
}

// Get WP credentials for userId=1
const accounts = await wordpressDb.getUserWordpressAccounts(1);
const account = accounts[0];
if (!account) { console.error('[batch-images] No WP account for userId=1'); process.exit(1); }
const { siteUrl, username, appPassword } = account;

// Run sequentially to avoid rate limits
const start = Date.now();
console.log(`[batch-images] Processing ${SLUGS_NO_IMAGE.length} articles missing featured images`);
console.log(`[batch-images] WP: ${siteUrl}`);

for (let i = 0; i < SLUGS_NO_IMAGE.length; i++) {
  await processArticle(SLUGS_NO_IMAGE[i], i, siteUrl, username, appPassword);
  // Small delay between articles
  if (i < SLUGS_NO_IMAGE.length - 1) await new Promise(r => setTimeout(r, 1000));
}

const mins = ((Date.now() - start) / 60000).toFixed(1);
console.log(`\n[batch-images] DONE in ${mins} min`);
