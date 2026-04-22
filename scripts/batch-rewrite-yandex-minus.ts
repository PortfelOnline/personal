/**
 * Rewrite 6 thin pages excluded from Yandex index (5 April 2026)
 * Причина: <1500 слов, 0 FAQ → Яндекс исключил из индекса
 *
 * Usage: npx tsx scripts/batch-rewrite-yandex-minus.ts
 */
import 'dotenv/config';
import { runBatchRewrite } from '../server/routers/articles';

const URLS = [
  // 463 слова, 0 FAQ
  'https://kadastrmap.info/kadastr/spravku-egrn-cherez-internet/',
  // 351 слово, 0 FAQ
  'https://kadastrmap.info/kadastr/uznat-kadastrovuyu-stoimost-doma-onlajn-instruktsiya/',
  // 466 слов, 0 FAQ, нет картинок
  'https://kadastrmap.info/kadastr/spravka-egrn-po-vsej-rossii/',
  // 549 слов, 0 FAQ
  'https://kadastrmap.info/kadastr/kak-sobrat-sobranie-sobstvennikov-mnogokvartirnogo-doma/',
  // 692 слова, 0 FAQ
  'https://kadastrmap.info/kadastr/chto-zapreshheno-stroit-na-dache/',
  // 780 слов, 0 FAQ
  'https://kadastrmap.info/kadastr/chto-takoe-vypiska-iz-egrn-na-zemlyu-i-dom-2/',
];

runBatchRewrite('admin', URLS).catch(e => { console.error(e); process.exit(1); });
