/**
 * Find articles that still need improvement:
 * words < 2500 OR faq < 5
 * Scans WP posts page by page
 */
import 'dotenv/config';
import axios from 'axios';

const AUTH = 'Basic ' + Buffer.from('grudeves_vf97s8yc:uX$8LCdpGKH9Rcd').toString('base64');
const API = 'https://kadastrmap.info/wp-json/wp/v2';

// All slugs already processed in recent batches (skip them)
const DONE_BATCHES = new Set([
  // batch-22
  'vypiska-egrn-za-chas','vypiska-iz-egrn-dlya-propiski','vypiska-iz-egrn-dlya-yuridicheskih-lits',
  'vypiska-iz-egrn-gosuslugi','vypiska-iz-egrn-moskva','vypiska-iz-egrn-na-imushhestvo',
  'vypiska-iz-egrn-na-mashinomesto','vypiska-iz-egrn-na-pomeshhenie','vypiska-iz-egrn-na-sobstvennost',
  'vypiska-iz-egrn-na-zemelnyj-uchastok-gosuslugi','vypiska-iz-egrn-o-postanovke-obekta-na-kadastrovyj-uchet',
  'vypiska-iz-egrn-o-pravah-na-nedvizhimost','vypiska-iz-egrn-o-pravoobladatele',
  'vypiska-iz-egrn-ob-osnovnyh-harakteristikah-obekta','vypiska-iz-egrn-ofitsialnyj-sajt',
  'vypiska-iz-egrn-onlajn-fns','vypiska-iz-egrn-onlajn-ofitsialnyj-sajt',
  'vypiska-iz-egrn-po-obremeneniyam','vypiska-iz-egrn-podtverzhdayushhaya-pravo-sobstvennosti',
  'vypiska-iz-egrn-pri-arende-kvartiry','vypiska-iz-egrn-vmesto-svidetelstva-o-sobstvennosti',
  'vypisku-o-kadastrovoj-stoimosti-zakazat','zachem-nuzhen-kadastrovyj-pasport-na-zemelnyj-uchastok',
  'zachem-nuzhna-vypiska-iz-egrn-na-kvartiru','zakazat-kadastrovuyu-spravku-o-kadastrovoj-stoimosti-kvartiry',
  'zakazat-kadastrovuyu-vipisku','zakazat-kadastrovuyu-vypisku-cherez-internet',
  'zakazat-kadastrovuyu-vypisku-na-zemelnyj-uchastok',
  'zakazat-kadastrovuyu-vypisku-na-zemelnyj-uchastok-v-elektronnom-vide',
  'zakazat-kadastrovyj-pasport-na-zemelnyj-uchastok-onlajn-v-rosreestre',
  'zakazat-kadastrovyj-pasport-onlajn-v-rosreestre','zakazat-kadastrovyj-pasport-v-mfts',
  'zakazat-kadastrovyj-pasport-zdaniya','zakazat-kadastrovyj-pasport-zemelnogo-uchastka-zakazat',
  'zakazat-kadastrovyj-plan-na-zemlyu','zakazat-onlajn-kadastrovuyu-vypisku',
  'zakazat-otchet-egrn-onlajn','zakazat-rasshirennuyu-vypisku-iz-egrp',
  'zakazat-spravku-o-kadastrovoj-stoimosti-zemelnogo-uchastka',
  'zakazat-spravku-o-kadastrovoj-stoimosti-zemli','zakazat-vypisku-egrn',
  'zakazat-vypisku-iz-egrn-o-kadastrovoj-stoimosti-obekta-nedvizhimosti',
  'zakazat-vypisku-iz-egrp-onlajn-rosreestr','zakazat-vypisku-iz-egrp-rosreestr',
  'zakazat-vypisku-o-perehode-prav','zemelnyj-kadastrovyj-pasport',
]);

const thin: {slug: string; words: number; faq: number; modified: string}[] = [];

async function main() {
  let page = 1;
  let total = 0;

  console.log('Scanning WP posts for thin content...');

  while (true) {
    const r = await axios.get(
      `${API}/posts?per_page=100&page=${page}&_fields=slug,modified,content&status=publish`,
      { headers: { Authorization: AUTH }, timeout: 30000 }
    );
    if (!r.data.length) break;

    for (const p of r.data) {
      if (!p.slug.startsWith('k') && !p.slug.startsWith('s') && !p.slug.startsWith('z') &&
          !p.slug.startsWith('o') && !p.slug.startsWith('c') && !p.slug.startsWith('v') &&
          !p.slug.startsWith('u') && !p.slug.startsWith('g') && !p.slug.startsWith('p') &&
          !p.slug.startsWith('r') && !p.slug.startsWith('n') && !p.slug.startsWith('d') &&
          !p.slug.startsWith('b') && !p.slug.startsWith('e') && !p.slug.startsWith('f') &&
          !p.slug.startsWith('m') && !p.slug.startsWith('a') && !p.slug.startsWith('i')) continue;

      if (DONE_BATCHES.has(p.slug)) continue;

      const raw = p.content.rendered;
      const words = raw.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim().split(' ').filter(Boolean).length;
      const faq = (raw.match(/faq-item/g) || []).length;

      if (words < 2500 || faq < 5) {
        thin.push({ slug: p.slug, words, faq, modified: p.modified.slice(0, 10) });
        total++;
      }
    }

    const totalPages = parseInt(r.headers['x-wp-totalpages'] || '1');
    console.log(`page ${page}/${totalPages} — thin so far: ${total}`);
    if (page >= totalPages) break;
    page++;
    await new Promise(res => setTimeout(res, 300));
  }

  // Sort by words ascending (worst first)
  thin.sort((a, b) => a.words - b.words);

  console.log(`\n=== TOP 50 thin articles (worst first) ===`);
  for (const t of thin.slice(0, 50)) {
    const flag = t.words < 1000 ? '🔴' : t.words < 2000 ? '🟡' : '🟢';
    console.log(`${flag} words=${String(t.words).padStart(4)} faq=${t.faq} mod=${t.modified} ${t.slug}`);
  }
  console.log(`\nTotal thin: ${thin.length}`);
}

main().catch(e => { console.error(e); process.exit(1); });
