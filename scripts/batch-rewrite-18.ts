/**
 * Batch 18: 10 HIGH priority articles
 */
import 'dotenv/config';
import { runBatchRewrite } from '../server/routers/articles';

const URLS = [
  'https://kadastrmap.info/kadastr/kadastrovyj-pasport-eto-novyj-vzglyad-na-gosregistrtsiyu/',
  'https://kadastrmap.info/kadastr/kadastrovyj-pasport-foto/',
  'https://kadastrmap.info/kadastr/kadastrovyj-pasport-v-2017-godu/',
  'https://kadastrmap.info/kadastr/kadastrovyj-pasport-zdaniya-obrazets/',
  'https://kadastrmap.info/kadastr/kak-uznat-sobstvennika-uchastka-po-kadastrovomu-nomeru/',
  'https://kadastrmap.info/kadastr/kak-uznat-sobstvennika-zemelnogo-uchastka-po-adresu/',
  'https://kadastrmap.info/kadastr/kak-vosstanovit-kadastrovyj-pasport-na-kvartiru/',
  'https://kadastrmap.info/kadastr/kak-vosstanovit-kadastrovyj-pasport-na-zemelnyj-uchastok/',
  'https://kadastrmap.info/kadastr/kak-vyglyadit-kadastrovyj-pasport/',
  'https://kadastrmap.info/kadastr/kak-vyglyadit-kadastrovyj-pasport-na-kvartiru/',
];

const USER_ID = 1;
console.log(`[batch-18] Starting: ${URLS.length} articles`);
const start = Date.now();
await runBatchRewrite(USER_ID, URLS);
const mins = ((Date.now() - start) / 60000).toFixed(1);
console.log(`[batch-18] DONE in ${mins} min`);
