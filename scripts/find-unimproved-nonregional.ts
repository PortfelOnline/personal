/**
 * Find thin articles excluding regional map pages
 * (publichnaya-kadastrovaya-karta-*, kadastrovaya-stoimost-region)
 */
import 'dotenv/config';
import axios from 'axios';

const AUTH = 'Basic ' + Buffer.from('grudeves_vf97s8yc:uX$8LCdpGKH9Rcd').toString('base64');
const API = 'https://kadastrmap.info/wp-json/wp/v2';

// Patterns of regional/map pages to skip (they need a separate batch strategy)
const REGIONAL_PATTERNS = [
  /publichnaya-kadastrovaya-karta-/,
  /kadastrovaya-karta-/,
  /kadastrovaya-stoimost-(zemli|nedvizhimosti|zemelnogo)-(v-|na-|g-)?[a-z]+-?(oblast|kraj|respubliki|okrug|ajon|kazan|moskv|piter|burg|novosibirsk|ekaterinburg|samara|volgograd|permskij|stavropolskij|vologodsk|chelyabinskaya|tambovsk|irkutsk|naberezhnye|kemerovo|omsk|tomsk|smolenskoj|ryazansk|zaporozhskoj|altajsk|chukotsk|buryatiya|komi|amursk|vladivostok|primorsk|podmoskovya|pskovsk|kursk|volgogradsk|kemerovsk)/,
];

const thin: {slug: string; words: number; faq: number; modified: string}[] = [];

function isRegional(slug: string): boolean {
  return REGIONAL_PATTERNS.some(p => p.test(slug));
}

async function main() {
  let page = 1;
  console.log('Scanning for thin non-regional articles...');

  while (true) {
    const r = await axios.get(
      `${API}/posts?per_page=100&page=${page}&_fields=slug,modified,content&status=publish`,
      { headers: { Authorization: AUTH }, timeout: 30000 }
    );
    if (!r.data.length) break;

    for (const p of r.data) {
      if (isRegional(p.slug)) continue;

      const raw = p.content.rendered;
      const words = raw.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim().split(' ').filter(Boolean).length;
      const faq = (raw.match(/faq-item/g) || []).length;

      if (words < 2000 || faq < 5) {
        thin.push({ slug: p.slug, words, faq, modified: p.modified.slice(0, 10) });
      }
    }

    const totalPages = parseInt(r.headers['x-wp-totalpages'] || '1');
    if (page % 4 === 0) process.stdout.write(`page ${page}/${totalPages} thin=${thin.length}\n`);
    if (page >= totalPages) break;
    page++;
    await new Promise(res => setTimeout(res, 200));
  }

  thin.sort((a, b) => a.words - b.words);

  console.log(`\n=== TOP 60 thin non-regional ===`);
  for (const t of thin.slice(0, 60)) {
    const flag = t.words < 500 ? '🔴' : t.words < 1200 ? '🟡' : '🟢';
    console.log(`${flag} ${String(t.words).padStart(4)}w faq=${t.faq} ${t.slug}`);
  }
  console.log(`\nTotal non-regional thin: ${thin.length}`);
}

main().catch(e => { console.error(e); process.exit(1); });
