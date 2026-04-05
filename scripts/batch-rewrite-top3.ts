/**
 * Top-3 GSC articles closest to top-3 position — targeted Yandex optimization
 */
import 'dotenv/config';
import { runBatchRewrite } from '../server/routers/articles';

const URLS = [
  // pos 3.9 Google, "как узнать планировку квартиры по адресу" — almost top-3, Yandex competitor has 1300 words
  'https://kadastrmap.info/kadastr/kadastrovyj-plan-kvartiry-po-adresu/',
  // pos 4.6 Google, "найти участок по кадастровому номеру со спутника" — 102 clicks
  'https://kadastrmap.info/kadastr/kadastrovaya-publichnaya-karta-so-sputnika/',
  // pos 6.6 Google, "найти участок по кадастровому номеру" — 1241 impressions
  'https://kadastrmap.info/kadastr/raspolozhenie-po-kadastrovomu-nomeru/',
];

const USER_ID = 1;
console.log(`[top3] Starting: ${URLS.length} articles`);
const start = Date.now();
await runBatchRewrite(USER_ID, URLS);
const mins = ((Date.now() - start) / 60000).toFixed(1);
console.log(`[top3] DONE in ${mins} min`);
