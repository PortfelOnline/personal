/**
 * Internal linking agent — injects cross-links between kadastrmap.info articles.
 *
 * Strategy:
 *  - Fetch all posts from WP
 *  - For each article with < 4 internal links, find phrases matching other articles
 *  - Inject up to 5 new internal links (first occurrence, not inside existing <a> tags)
 *  - Update via WP API
 *
 * Anchor texts are exact key phrases that match the target article's main topic.
 * Internal links have no rel="nofollow" — full PageRank transfer.
 */
import 'dotenv/config';
import axios from 'axios';
import https from 'https';

const SITE = 'https://kadastrmap.info';
const API = `${SITE}/wp-json/wp/v2`;
const AUTH = 'Basic ' + Buffer.from('grudeves_vf97s8yc:uX$8LCdpGKH9Rcd').toString('base64');
const agent = new https.Agent({ rejectUnauthorized: false });

const headers = { Authorization: AUTH };

// ── Target articles + their anchor phrases ────────────────────────────────────
// Phrases are in order of preference (first match wins per article)
const LINK_MAP: { url: string; anchors: string[] }[] = [
  {
    url: `${SITE}/kadastr/kadastrovyj-pasport-na-kvartiru/`,
    anchors: ['кадастровый паспорт на квартиру', 'кадастровый паспорт квартиры', 'кадастровый паспорт'],
  },
  {
    url: `${SITE}/kadastr/proverit-kvartiru-na-obremenenie-onlajn/`,
    anchors: ['проверить квартиру на обременение', 'проверка обременения', 'обременение квартиры онлайн'],
  },
  {
    url: `${SITE}/kadastr/kak-uznat-vladeltsa-kvartiry-po-adresu-zakonnye-sposoby-i-vypiska/`,
    anchors: ['узнать владельца квартиры по адресу', 'кто владелец квартиры', 'собственника по адресу'],
  },
  {
    url: `${SITE}/kadastr/raspolozhenie-po-kadastrovomu-nomeru/`,
    anchors: ['расположение по кадастровому номеру', 'найти объект по кадастровому номеру', 'кадастровый номер участка'],
  },
  {
    url: `${SITE}/kadastr/kak-proverit-sobstvennika-po-kadastrovomu-nomeru-onlajn/`,
    anchors: ['проверить собственника по кадастровому номеру', 'проверка собственника', 'собственник по кадастровому номеру'],
  },
  {
    url: `${SITE}/kadastr/zakazat-kadastrovuyu-vypisku-onlajn-tsena-sposoby-polucheniya/`,
    anchors: ['заказать кадастровую выписку онлайн', 'кадастровую выписку онлайн', 'кадастровая выписка'],
  },
  {
    url: `${SITE}/kadastr/kak-uznat-nalozhen-li-arest-na-kvartiru/`,
    anchors: ['наложен ли арест на квартиру', 'проверить арест квартиры', 'арест на квартиру'],
  },
  {
    url: `${SITE}/kadastr/kak-uznat-kvartira-v-zaloge-ili-net/`,
    anchors: ['квартира в залоге', 'узнать залог на квартиру', 'квартира в залоге или нет'],
  },
  {
    url: `${SITE}/kadastr/kadastrovaya-stoimost-nedvizhimosti-v-rosreestre-kak-uznat/`,
    anchors: ['кадастровая стоимость недвижимости', 'кадастровая стоимость объекта', 'кадастровую стоимость'],
  },
  {
    url: `${SITE}/kadastr/chto-nuzhno-znat-o-kadastrovyh-vypiskah/`,
    anchors: ['выписка ЕГРН', 'получить выписку ЕГРН', 'выписка из ЕГРН'],
  },
  {
    url: `${SITE}/kadastr/zakazat-spravku-ob-obremenenii-nedvizhimosti-v-moskve-poshagovoe-rukovodstvo/`,
    anchors: ['справка об обременении', 'справка обременение', 'обременение недвижимости'],
  },
  {
    url: `${SITE}/kadastr/situatsionnyj-plan-dlya-stroitelstva-doma-poryadok-i-dokumenty/`,
    anchors: ['ситуационный план для строительства', 'ситуационный план дома'],
  },
  {
    url: `${SITE}/kadastr/kadastrovaya-publichnaya-karta-so-sputnika/`,
    anchors: ['кадастровая карта со спутника', 'публичная кадастровая карта со спутника'],
  },
];

// ── Helpers ────────────────────────────────────────────────────────────────────

/** Strip HTML tags, return plain text (for checking phrase presence) */
function stripHtml(html: string): string {
  return html.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ');
}

/** Count existing internal links in HTML */
function countInternalLinks(html: string): number {
  return (html.match(/href="https:\/\/kadastrmap\.info\//g) || []).length;
}

/**
 * Inject a link into HTML for the first occurrence of `phrase` that is NOT
 * already inside an <a> tag or a heading (h1-h6).
 * Returns modified HTML or null if phrase not found / already linked.
 */
function injectLink(html: string, phrase: string, url: string): string | null {
  const lowerPhrase = phrase.toLowerCase();
  const lowerHtml = html.toLowerCase();

  // Quick check: phrase must appear in plain text at all
  if (!stripHtml(html).toLowerCase().includes(lowerPhrase)) return null;

  // Find all occurrences in raw HTML (case-insensitive)
  let searchFrom = 0;
  while (searchFrom < html.length) {
    const pos = lowerHtml.indexOf(lowerPhrase, searchFrom);
    if (pos === -1) break;

    // Check we're not inside an <a> tag: look backwards for unclosed <a
    const before = html.slice(0, pos);
    const lastAOpen = before.lastIndexOf('<a ');
    const lastAClose = before.lastIndexOf('</a>');
    const insideAnchor = lastAOpen > lastAClose;
    if (insideAnchor) { searchFrom = pos + 1; continue; }

    // Check we're not inside a heading
    const lastHOpen = before.search(/<h[1-6][^>]*>[^<]*$/);
    const lastHClose = before.lastIndexOf('</h');
    const insideHeading = lastHOpen !== -1 && lastHOpen > lastHClose;
    if (insideHeading) { searchFrom = pos + 1; continue; }

    // Check not inside another link via href
    if (before.includes(`href="${url}"`)) return null; // already linked

    // Inject
    const original = html.slice(pos, pos + phrase.length);
    const link = `<a href="${url}">${original}</a>`;
    return html.slice(0, pos) + link + html.slice(pos + phrase.length);
  }
  return null;
}

// ── Fetch all posts (paginated) ────────────────────────────────────────────────
async function fetchAllPosts(): Promise<{ id: number; link: string; content: string }[]> {
  const posts: { id: number; link: string; content: string }[] = [];
  let page = 1;
  while (true) {
    const res = await axios.get(`${API}/posts`, {
      params: { per_page: 100, page, _fields: 'id,link,content', status: 'publish' },
      headers,
      httpsAgent: agent,
    });
    const batch = res.data as { id: number; link: string; content: { rendered: string } }[];
    if (!batch.length) break;
    for (const p of batch) {
      posts.push({ id: p.id, link: p.link, content: p.content.rendered });
    }
    if (batch.length < 100) break;
    page++;
  }
  return posts;
}

// ── Update post content ────────────────────────────────────────────────────────
async function updatePostContent(id: number, content: string): Promise<void> {
  await axios.post(
    `${API}/posts/${id}`,
    { content },
    { headers: { ...headers, 'Content-Type': 'application/json' }, httpsAgent: agent },
  );
}

// ── Main ──────────────────────────────────────────────────────────────────────
console.log('[interlink] Fetching all posts...');
const allPosts = await fetchAllPosts();
console.log(`[interlink] Total posts: ${allPosts.length}`);

let updated = 0;
let skipped = 0;

for (const post of allPosts) {
  // Skip posts that already have enough internal links
  const existingLinks = countInternalLinks(post.content);
  if (existingLinks >= 6) { skipped++; continue; }

  // Skip posts that are themselves one of the target articles
  const isSelf = LINK_MAP.some(lm => post.link === lm.url || post.link.includes(lm.url));
  if (isSelf) { skipped++; continue; }

  let html = post.content;
  let injected = 0;
  const alreadyInjectedUrls = new Set<string>();

  for (const { url, anchors } of LINK_MAP) {
    if (injected >= 5) break;
    if (alreadyInjectedUrls.has(url)) continue;
    // Don't link to itself
    if (post.link === url || post.link.includes(new URL(url).pathname)) continue;

    for (const anchor of anchors) {
      const result = injectLink(html, anchor, url);
      if (result) {
        html = result;
        alreadyInjectedUrls.add(url);
        injected++;
        break; // found one match for this target article, move to next
      }
    }
  }

  if (injected === 0) { skipped++; continue; }

  try {
    await updatePostContent(post.id, html);
    const slug = post.link.split('/').filter(Boolean).pop();
    console.log(`[interlink] ✅ ${slug} +${injected} links (was ${existingLinks})`);
    updated++;
  } catch (err: any) {
    console.warn(`[interlink] ❌ ${post.link}: ${err.message}`);
  }

  // Throttle: 1 update per 300ms to avoid WP API overload
  await new Promise(r => setTimeout(r, 300));
}

console.log(`[interlink] DONE. Updated: ${updated}, skipped: ${skipped}`);
