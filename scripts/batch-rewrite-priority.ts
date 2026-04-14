/**
 * Priority rewrite: high-traffic articles not yet improved
 */
import 'dotenv/config';
import { runBatchRewrite } from '../server/routers/articles';

const BASE = 'https://kadastrmap.info/kadastr/';
const SLUGS = [
  'kadastrovyj-nomer-po-adresu-obekta-nedvizhimosti', // #15, 1944 impr, H2=0 !
  'rosreestr-spravochnaya-informatsiya-po-obektam-nedvizhimosti-onlajn', // #18.6, 1010 impr
  'kadastrovye-koordinaty',               // #12.7, 974 impr
  'kadastrovyj-plan-zemelnogo-uchastka',  // #13.7, 840 impr
  'granitsy-zemelnogo-uchastka',          // #15.7, 548 impr
];

const URLS = SLUGS.map(s => `${BASE}${s}/`);
console.log(`[priority] Starting: ${URLS.length} articles`);
const start = Date.now();
await runBatchRewrite(1, URLS);
const mins = ((Date.now() - start) / 60000).toFixed(1);
console.log(`[priority] DONE in ${mins} min`);
