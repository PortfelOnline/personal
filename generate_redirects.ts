#!/usr/bin/env npx tsx
/**
 * Scans kadastrmap.info catalog, finds title duplicates,
 * and generates a JSON file ready to import in Redirection plugin.
 *
 * Run: npx tsx generate_redirects.ts
 * Then import redirects-import.json in WP Admin → Tools → Redirection → Import/Export
 */

import axios from 'axios';
import * as cheerio from 'cheerio';
import * as fs from 'fs';

const BASE_URL = 'https://kadastrmap.info/kadastr/';
const CONCURRENCY = 5;
const OUTPUT_FILE = './redirects-import.json';

interface Article { url: string; title: string }

function normalizeTitleKey(title: string): string {
  return title
    .toLowerCase()
    .replace(/[^а-яёa-z0-9\s]/gi, ' ')
    .replace(/\s+/g, ' ')
    .trim()
    .split(' ')
    .slice(0, 6)
    .join(' ');
}

async function fetchPage(url: string): Promise<{ articles: Article[]; totalPages: number }> {
  const res = await axios.get(url, {
    headers: { 'User-Agent': 'Mozilla/5.0 (compatible; RedirectGen/1.0)' },
    timeout: 30000,
  });
  const $ = cheerio.load(res.data as string);
  const articles: Article[] = [];

  $('div.article-entry h3 a, h2 a, h3 a, .entry-title a').each((_, el) => {
    const href = $(el).attr('href') || '';
    const title = $(el).text().trim();
    if (href && title && title.length >= 5 && href.includes('/kadastr/')) {
      const fullUrl = href.startsWith('http') ? href : new URL(href, url).toString();
      if (!articles.find(a => a.url === fullUrl)) articles.push({ url: fullUrl, title });
    }
  });

  let totalPages = 1;
  $('a[href*="/page/"]').each((_, el) => {
    const m = ($(el).attr('href') || '').match(/\/page\/(\d+)\//);
    if (m) totalPages = Math.max(totalPages, parseInt(m[1], 10));
  });

  return { articles, totalPages };
}

async function scanAllPages(): Promise<Article[]> {
  console.log('Scanning page 1...');
  const first = await fetchPage(BASE_URL);
  console.log(`  Found ${first.articles.length} articles, total pages: ${first.totalPages}`);

  const all = [...first.articles];

  for (let p = 2; p <= first.totalPages; p += CONCURRENCY) {
    const batch: number[] = [];
    for (let i = p; i < p + CONCURRENCY && i <= first.totalPages; i++) batch.push(i);

    process.stdout.write(`  Pages ${batch[0]}–${batch[batch.length - 1]}... `);
    const results = await Promise.allSettled(
      batch.map(n => fetchPage(`${BASE_URL.replace(/\/$/, '')}/page/${n}/`))
    );
    for (const r of results) {
      if (r.status === 'fulfilled') all.push(...r.value.articles);
    }
    console.log(`total so far: ${all.length}`);
  }

  return all;
}

function findDuplicates(articles: Article[]): Map<string, Article[]> {
  const groups = new Map<string, Article[]>();
  for (const art of articles) {
    const key = normalizeTitleKey(art.title);
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key)!.push(art);
  }
  // Keep only groups with 2+ articles
  for (const [key, arts] of Array.from(groups.entries())) {
    if (arts.length < 2) groups.delete(key);
  }
  return groups;
}

/** Heuristic: keep the article with the shortest URL path (simplest slug = canonical).
 *  If tie, keep the one with a longer title (more specific/informative). */
function pickCanonical(articles: Article[]): Article {
  return articles.slice().sort((a, b) => {
    const pa = new URL(a.url).pathname.length;
    const pb = new URL(b.url).pathname.length;
    if (pa !== pb) return pa - pb; // shorter path = canonical
    return b.title.length - a.title.length; // longer title = more specific
  })[0];
}

async function main() {
  console.log('=== Redirection JSON Generator ===\n');

  const articles = await scanAllPages();
  console.log(`\nTotal articles: ${articles.length}`);

  const groups = findDuplicates(articles);
  console.log(`Duplicate groups: ${groups.size}`);

  const redirects: object[] = [];

  for (const [key, arts] of Array.from(groups.entries())) {
    const canonical = pickCanonical(arts);
    const others = arts.filter(a => a.url !== canonical.url);

    console.log(`\nGroup: "${key}"`);
    console.log(`  KEEP: ${canonical.url}`);

    for (const art of others) {
      const sourcePath = new URL(art.url).pathname;
      console.log(`  301 : ${sourcePath} → ${canonical.url}`);

      redirects.push({
        url: sourcePath,
        action_code: 301,
        action_type: 'url',
        action_data: { url: canonical.url },
        match_type: 'url',
        group_id: 1,
        enabled: true,
      });
    }
  }

  const output = { redirects };
  fs.writeFileSync(OUTPUT_FILE, JSON.stringify(output, null, 2), 'utf8');

  console.log(`\n✅ Done! ${redirects.length} redirects written to ${OUTPUT_FILE}`);
  console.log('\nImport in WordPress:');
  console.log('  WP Admin → Tools → Redirection → Import/Export → Upload JSON file');
}

main().catch(e => { console.error(e); process.exit(1); });
