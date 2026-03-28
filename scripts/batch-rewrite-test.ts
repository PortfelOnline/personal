/**
 * Test run: 2 articles to verify emoji improvements.
 */
import 'dotenv/config';
import { runBatchRewrite } from '../server/routers/articles';

const URLS = [
  'https://kadastrmap.info/kadastr/vypiska-iz-egrn-na-kvartiru/',
  'https://kadastrmap.info/kadastr/kak-snyat-obremenenie-s-ipotechnoj-kvartiry/',
];

const USER_ID = 1;
console.log(`[batch-test] Starting: ${URLS.length} articles`);
const start = Date.now();
await runBatchRewrite(USER_ID, URLS);
const mins = ((Date.now() - start) / 60000).toFixed(1);
console.log(`[batch-test] DONE in ${mins} min`);
