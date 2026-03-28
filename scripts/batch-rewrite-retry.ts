/**
 * Retry script for 4 failed articles from batch-rewrite7.
 */
import 'dotenv/config';
import { runBatchRewrite } from '../server/routers/articles';

const URLS = [
  'https://kadastrmap.info/kadastr/kadastrovyj-plan-kvartiry-po-adresu/',
  'https://kadastrmap.info/kadastr/kak-snyat-obremenenie-s-obekta-nedvizhimosti-poshagovaya-instruktsiya/',
  'https://kadastrmap.info/kadastr/publichnaya-kadastrovaya-karta-novosibirskoy-oblasti/',
  'https://kadastrmap.info/kadastr/zakazat-spravku-ob-obremenenii-nedvizhimosti-v-moskve-poshagovoe-rukovodstvo/',
];

const USER_ID = 1;
console.log(`[batch-retry] Starting: ${URLS.length} articles`);
const start = Date.now();
await runBatchRewrite(USER_ID, URLS);
const mins = ((Date.now() - start) / 60000).toFixed(1);
console.log(`[batch-retry] DONE in ${mins} min`);
