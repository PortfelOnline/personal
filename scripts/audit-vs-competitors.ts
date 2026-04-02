/**
 * Audit: compare all improved kadastrmap.info articles vs TOP-3 competitors
 * Fetches each article, gets SERP top-3, compares word count / FAQ / H2 / table
 *
 * Run: npx tsx scripts/audit-vs-competitors.ts [--limit 20]
 */
import 'dotenv/config';
import * as wordpressDb from '../server/_core/wordpress';
import { fetchGoogleSerp, fetchYandexSerp } from '../server/_core/serpParser';
import { fetchPageHtml } from '../server/_core/browser';

const SITE = 'https://kadastrmap.info';
const DELAY_MS = 4000; // between SERP calls to avoid 429

function sleep(ms: number) { return new Promise(r => setTimeout(r, ms)); }

function parseMetrics(html: string) {
  const words = html.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim().split(' ').filter(Boolean).length;
  const h2 = (html.match(/<h2\b/gi) || []).length;
  const faq = (html.match(/<details\b/gi) || []).length;
  const table = /<table\b/i.test(html);
  return { words, h2, faq, table };
}

const args = process.argv.slice(2);
const limitArg = args.indexOf('--limit');
const LIMIT = limitArg !== -1 ? parseInt(args[limitArg + 1]) : 30;

const accounts = await wordpressDb.getUserWordpressAccounts(1);
const { siteUrl, username, appPassword } = accounts[0];
const auth = 'Basic ' + Buffer.from(`${username}:${appPassword}`).toString('base64');

// Fetch all published posts
let page = 1;
const allPosts: { id: number; slug: string; title: string; link: string }[] = [];
while (true) {
  const resp = await fetch(`${siteUrl}/wp-json/wp/v2/posts?per_page=100&page=${page}&_fields=id,slug,title,link&status=publish`, { headers: { Authorization: auth } });
  if (!resp.ok) break;
  const posts = await resp.json() as any[];
  if (!posts.length) break;
  allPosts.push(...posts.map((p: any) => ({ id: p.id, slug: p.slug, title: p.title?.rendered || p.slug, link: p.link })));
  page++;
}

console.log(`\nTotal published: ${allPosts.length} — auditing up to ${LIMIT}\n`);
console.log('slug | our_words | top_words | our_faq | top_faq | our_h2 | top_h2 | our_table | status');
console.log('-'.repeat(120));

const results: { slug: string; gap: number; status: string }[] = [];

for (const post of allPosts.slice(0, LIMIT)) {
  try {
    // Fetch our article
    const ourResp = await fetch(post.link, { headers: { 'User-Agent': 'Mozilla/5.0' } });
    const ourHtml = await ourResp.text();
    // Extract main content (between <article> tags or body)
    const contentMatch = ourHtml.match(/<article[^>]*>([\s\S]*?)<\/article>/i);
    const ourContent = contentMatch ? contentMatch[1] : ourHtml;
    const our = parseMetrics(ourContent);

    await sleep(DELAY_MS);

    // Get top Google competitor
    const keyword = post.slug.replace(/-/g, ' ');
    let topCompetitor = { words: 0, h2: 0, faq: 0, table: false };
    try {
      const serp = await fetchGoogleSerp(keyword);
      const top = serp.results.filter(r => !r.url.includes('kadastrmap')).slice(0, 3);
      if (top.length > 0) {
        const compHtml = await fetchPageHtml(top[0].url);
        topCompetitor = parseMetrics(compHtml);
      }
      await sleep(DELAY_MS);
    } catch { /* fallback */ }

    const wordGap = our.words - topCompetitor.words;
    const status = our.words >= 3000 && our.faq >= 8 && our.h2 >= 6
      ? (wordGap >= 0 ? '✅ PASS' : '⚠️  thin')
      : '❌ FAIL';
    const row = `${post.slug.slice(0, 50).padEnd(52)} | ${String(our.words).padStart(9)} | ${String(topCompetitor.words).padStart(9)} | ${String(our.faq).padStart(7)} | ${String(topCompetitor.faq).padStart(7)} | ${String(our.h2).padStart(6)} | ${String(topCompetitor.h2).padStart(6)} | ${String(our.table).padStart(9)} | ${status}`;
    console.log(row);
    results.push({ slug: post.slug, gap: wordGap, status });

  } catch (e: any) {
    console.log(`${post.slug.slice(0, 50).padEnd(52)} | ERROR: ${e.message.slice(0, 50)}`);
  }
}

console.log('\n--- SUMMARY ---');
const pass = results.filter(r => r.status.includes('PASS')).length;
const fail = results.filter(r => r.status.includes('FAIL')).length;
const thin = results.filter(r => r.status.includes('thin')).length;
console.log(`✅ PASS: ${pass}  ⚠️ thin: ${thin}  ❌ FAIL: ${fail}`);
console.log('\nNeeds improvement:');
results.filter(r => !r.status.includes('PASS')).sort((a,b) => a.gap - b.gap).slice(0, 10).forEach(r => {
  console.log(`  ${r.slug} (gap: ${r.gap > 0 ? '+' : ''}${r.gap} words)`);
});
