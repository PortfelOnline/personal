/**
 * Batch 16: 10 HIGH priority articles
 */
import 'dotenv/config';
import { runBatchRewrite } from '../server/routers/articles';

const URLS = [
  'https://kadastrmap.info/kadastr/kadastrovyj-pasport-obekta-nezavershennogo-stroitelstva/',
  'https://kadastrmap.info/kadastr/kadastrovyj-pasport-obrazets/',
  'https://kadastrmap.info/kadastr/kadastrovyj-pasport-rf/',
  'https://kadastrmap.info/kadastr/kadastrovyj-pasport-skolko-dejstvitelen/',
  'https://kadastrmap.info/kadastr/kadastrovyj-pasport-tsena-voprosa/',
  'https://kadastrmap.info/kadastr/kadastrovyj-pasport-uchastka/',
  'https://kadastrmap.info/kadastr/kadastrovyj-pasport-uchastka-stoimost/',
  'https://kadastrmap.info/kadastr/kadastrovyj-pasport-zdaniya-sooruzheniya-obekta-nezavershennogo-stroitelstva/',
  'https://kadastrmap.info/kadastr/kadastrovyj-pasport-zemelnogo-uchastka-ufa/',
  'https://kadastrmap.info/kadastr/kadastrovyj-pasport-zhilya/',
];

const USER_ID = 1;
console.log(`[batch-16] Starting: ${URLS.length} articles`);
const start = Date.now();
await runBatchRewrite(USER_ID, URLS);
const mins = ((Date.now() - start) / 60000).toFixed(1);
console.log(`[batch-16] DONE in ${mins} min`);
