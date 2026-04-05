/**
 * Batch-19: 25 HIGH-priority articles (2026-04-04)
 */
import 'dotenv/config';
import { runBatchRewrite } from '../server/routers/articles';

const BASE = 'https://kadastrmap.info/kadastr/';
const SLUGS = [
  'kak-zakazat-kadastrovyj-plan-zemelnogo-uchastka-bystro-i-onlajn',
  'kak-zakazat-plan-bti',
  'kak-zakazat-spravku-egrn-cherez-mfts',
  'kak-zakazat-spravku-egrn-iz-rosreestra',
  'kak-zakazat-spravku-egrn-v-rosreestre-cherez-internet',
  'kak-zakazat-spravku-iz-egrn-o-sobstvennosti',
  'kak-zakazat-spravku-vypisku-iz-egrn',
  'kak-zakazat-v-gkn-vypisku-po-nedvizhimosti',
  'kak-zakazat-vypisku-egrn-dlya-prodazhi-kvartiry',
  'kak-zakazat-vypisku-egrn-na-zemlyu',
  'kak-zakazat-vypisku-egrn-v-mfts',
  'kak-zakazat-vypisku-iz-egrn-cherez-internet',
  'kak-zakazat-vypisku-iz-egrn-dlya-fizicheskih-lits',
  'kak-zakazat-vypisku-iz-egrn-dlya-fizicheskih-lits-na-kvartiru',
  'kak-zakazat-vypisku-iz-egrn-v-rosreestre-cherez-internet',
  'kak-zakazat-vypisku-iz-egrp-cherez-internet',
  'kak-zakazat-vypisku-iz-egrp-cherez-mfts',
  'kak-zakazat-vypisku-iz-egrp-v-mfts',
  'kakaya-vypiska-iz-egrn-nuzhna-pri-pokupke-kvartiry',
  'kakaya-vypiska-iz-egrn-nuzhna-pri-prodazhe-kvartiry',
  'kto-delaet-kadastrovyj-pasport-na-zemelnyj-uchastok',
  'kto-mozhet-poluchit-kadastrovyj-pasport-na-kvartiru',
  'kto-mozhet-poluchit-vypisku-iz-egrn',
  'kto-vydaet-kadastrovyj-pasport',
  'mfts-kadastrovyj-pasport',
];

const URLS = SLUGS.map(s => `${BASE}${s}/`);
console.log(`[batch-19] Starting: ${URLS.length} articles`);
const start = Date.now();
await runBatchRewrite(1, URLS);
const mins = ((Date.now() - start) / 60000).toFixed(1);
console.log(`[batch-19] DONE in ${mins} min`);
