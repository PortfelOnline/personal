/**
 * Batch 17: 10 HIGH priority articles
 */
import 'dotenv/config';
import { runBatchRewrite } from '../server/routers/articles';

const URLS = [
  'https://kadastrmap.info/kadastr/kadastrovyj-plan/',
  'https://kadastrmap.info/kadastr/kadastrovyj-plan-snt/',
  'https://kadastrmap.info/kadastr/kadastrovyj-plan-territorii-obrazets/',
  'https://kadastrmap.info/kadastr/kak-poluchit-kadastrovyj-pasport-na-zdanie-yuridicheskomu-litsu/',
  'https://kadastrmap.info/kadastr/kak-poluchit-vypisku-egrn-cherez-portal-gosuslug/',
  'https://kadastrmap.info/kadastr/kak-poluchit-vypisku-iz-egrn-v-rezhime-onlajn-v-rosreestr/',
  'https://kadastrmap.info/kadastr/kak-uznat-sobstvennika-kvartiry-po-adresu-onlajn-rosreestr-2/',
  'https://kadastrmap.info/kadastr/kak-uznat-sobstvennika-kvartiry-po-kadastrovomu-nomeru/',
  'https://kadastrmap.info/kadastr/kak-uznat-sobstvennika-nedvizhimosti-po-adresu/',
  'https://kadastrmap.info/kadastr/kak-uznat-sobstvennika-uchastka/',
];

const USER_ID = 1;
console.log(`[batch-17] Starting: ${URLS.length} articles`);
const start = Date.now();
await runBatchRewrite(USER_ID, URLS);
const mins = ((Date.now() - start) / 60000).toFixed(1);
console.log(`[batch-17] DONE in ${mins} min`);
