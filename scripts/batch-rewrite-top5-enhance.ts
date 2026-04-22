/**
 * Top-5 high-priority enhance: articles with highest SEO potential
 * that need fresher content, better featured snippets, more FAQ
 */
import 'dotenv/config';
import { runBatchRewrite } from '../server/routers/articles';

const BASE = 'https://kadastrmap.info/kadastr/';
const SLUGS = [
  'raspolozhenie-po-kadastrovomu-nomeru',           // #8.2 Google, 6229 impr, нет в Яндексе
  'proverit-obremenenie-na-nedvizhimost',           // #17.5 Google, 870 impr — нужен перезапуск
  'uznat-sobstvennika-zemelnogo-uchastka-po-kadastrovomu-nomeru', // #12.7, конкуренты слабые
  'kadastrovye-koordinaty',                         // 12 FAQ (минимум), 5764 слова
  'kadastrovyj-plan-zemelnogo-uchastka',            // 12 FAQ (минимум), pos 13.7
];

const URLS = SLUGS.map(s => `${BASE}${s}/`);
console.log(`[top5-enhance] Starting: ${URLS.length} articles`);
const start = Date.now();
await runBatchRewrite(1, URLS);
const mins = ((Date.now() - start) / 60000).toFixed(1);
console.log(`[top5-enhance] DONE in ${mins} min`);
