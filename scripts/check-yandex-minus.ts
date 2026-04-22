import 'dotenv/config';
import axios from 'axios';

const SITE_URL = 'https://kadastrmap.info';
const WP_USER = 'grudeves_vf97s8yc';
const WP_PASS = process.env.WP_APP_PASSWORD_KAD ?? 'uX$8LCdpGKH9Rcd';
const AUTH = 'Basic ' + Buffer.from(`${WP_USER}:${WP_PASS}`).toString('base64');
const API = `${SITE_URL}/wp-json/wp/v2`;

const MINUS_SLUGS = [
  'kak-sobrat-sobranie-sobstvennikov-mnogokvartirnogo-doma',
  'chto-zapreshheno-stroit-na-dache',
  'spravku-egrn-cherez-internet',
  'uznat-kadastrovuyu-stoimost-doma-onlajn-instruktsiya',
  'kak-snyat-obremenenie-s-ipotechnoj-kvartiry',
  'kirovskoj-oblasti',
  'kak-poluchit-spravku-egrn-onlajn',
  'chto-takoe-vypiska-iz-egrn-na-zemlyu-i-dom-2',
  'spravka-egrn-po-vsej-rossii',
  'vidy-vypisok-iz-egrn', // PLUS для сравнения
];

async function checkSlug(slug: string) {
  try {
    const r = await axios.get(`${API}/posts?slug=${slug}&_fields=id,status,modified,content`, {
      headers: { Authorization: AUTH },
      timeout: 15000,
    });
    if (!r.data.length) {
      console.log(`✗ ${slug} → NOT FOUND`);
      return;
    }
    const p = r.data[0];
    const raw = p.content.rendered;
    const words = raw.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim().split(' ').filter(Boolean).length;
    const imgs = (raw.match(/<img /g) || []).length;
    const placeholders = (raw.match(/src=["']image\d+\.jpg["']/g) || []).length;
    const h2 = (raw.match(/<h2/gi) || []).length;
    const faq = (raw.match(/faq-item/g) || []).length;
    const hasTable = raw.includes('<table');
    
    const issues: string[] = [];
    if (words < 1500) issues.push(`МАЛО СЛОВ: ${words}`);
    if (imgs === 0) issues.push('НЕТ КАРТИНОК');
    if (faq < 5) issues.push(`МАЛО FAQ: ${faq}`);
    if (placeholders > 0) issues.push(`PLACEHOLDER: ${placeholders}`);
    if (p.status !== 'publish') issues.push(`СТАТУС: ${p.status}`);
    
    const status = issues.length ? '⚠️ ' + issues.join(' | ') : '✅ OK';
    console.log(`${slug}`);
    console.log(`  mod=${p.modified.slice(0,10)} words=${words} h2=${h2} faq=${faq} imgs=${imgs} table=${hasTable} ${status}`);
  } catch (e: any) {
    console.log(`✗ ${slug} → ERR: ${e.message?.slice(0,80)}`);
  }
}

async function main() {
  console.log('=== Яндекс.Вебмастер минусы (5 апреля 2026) ===\n');
  for (const slug of MINUS_SLUGS) {
    await checkSlug(slug);
  }
}

main().catch(e => { console.error(e); process.exit(1); });
