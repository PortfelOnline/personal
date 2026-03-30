/**
 * Batch 6: 25 HIGH-priority articles
 * Focus: kadastrovyj-pasport variants — stoimost/tsena/srochno/adres/zemlya clusters
 *        + gde-zakazat-vypisku-iz-egrp (HIGH id=8453, missed in batch 5)
 *
 * Usage: npx tsx scripts/batch-rewrite-6.ts
 */
import 'dotenv/config';
import { runBatchRewrite } from '../server/routers/articles';

const URLS = [
  // gde-zakazat (missed from batch 5)
  'https://kadastrmap.info/kadastr/gde-zakazat-vypisku-iz-egrp/',

  // kadastrovyj-pasport — tsena/stoimost (highest conversion intent)
  'https://kadastrmap.info/kadastr/kadastrovyj-pasport-tsena/',
  'https://kadastrmap.info/kadastr/kadastrovyj-pasport-na-kvartiru-tsena/',
  'https://kadastrmap.info/kadastr/kadastrovyj-pasport-na-dom-stoimost/',
  'https://kadastrmap.info/kadastr/kadastrovyj-pasport-obekta-nedvizhimosti-stoimost/',
  'https://kadastrmap.info/kadastr/kadastrovyj-pasport-zemelnogo-uchastka-stoimost/',

  // kadastrovyj-pasport — srochno (urgent, top conversion)
  'https://kadastrmap.info/kadastr/kadastrovyj-pasport-na-kvartiru-srochno/',
  'https://kadastrmap.info/kadastr/kadastrovyj-pasport-srochno-v-moskovskoj-oblasti/',
  'https://kadastrmap.info/kadastr/kadastrovyj-pasport-za-odin-den/',

  // kadastrovyj-pasport — po adresu (geo-intent)
  'https://kadastrmap.info/kadastr/kadastrovyj-pasport-doma-po-adresu/',
  'https://kadastrmap.info/kadastr/kadastrovyj-pasport-doma-po-adresu-onlajn/',
  'https://kadastrmap.info/kadastr/kadastrovyj-pasport-po-kadastrovomu-nomeru/',

  // kadastrovyj-pasport — zemlya cluster
  'https://kadastrmap.info/kadastr/kadastrovyj-pasport-zemelnogo-uchastka-kak-poluchit/',
  'https://kadastrmap.info/kadastr/kadastrovyj-pasport-zemelnogo-uchastka-onlajn/',
  'https://kadastrmap.info/kadastr/kadastrovyj-pasport-zemelnogo-uchastka-poluchit/',
  'https://kadastrmap.info/kadastr/kadastrovyj-pasport-na-zemlyu-poluchit-bystro/',
  'https://kadastrmap.info/kadastr/kadastrovyj-pasport-na-zemlyu-stoimost/',

  // kadastrovyj-pasport — dom/dacha
  'https://kadastrmap.info/kadastr/kadastrovyj-pasport-na-zhiloj-dom/',
  'https://kadastrmap.info/kadastr/kadastrovyj-pasport-na-chastnyj-dom/',
  'https://kadastrmap.info/kadastr/kadastrovyj-pasport-na-dachu/',
  'https://kadastrmap.info/kadastr/kadastrovyj-pasport-na-dachnyj-uchastok/',

  // kadastrovyj-pasport — srok/poryadok (informational + CTA)
  'https://kadastrmap.info/kadastr/kadastrovyj-pasport-srok-dejstviya/',
  'https://kadastrmap.info/kadastr/kadastrovyj-pasport-na-kvartiru-srok-dejstviya/',
  'https://kadastrmap.info/kadastr/kadastrovyj-pasport-poryadok-oformleniya/',

  // kadastrovyj-pasport — ili-vypiska comparison (high decision intent)
  'https://kadastrmap.info/kadastr/kadastrovyj-pasport-ili-vypiska-iz-egrn/',
];

const USER_ID = 1;

console.log(`[batch-rewrite-6] Starting: ${URLS.length} articles, userId=${USER_ID}`);
console.log(`[batch-rewrite-6] Clusters: gde-zakazat(1), tsena/stoimost(5), srochno(3), adres(3), zemlya(5), dom/dacha(4), srok/poryadok(3), comparison(1)`);
const start = Date.now();

await runBatchRewrite(USER_ID, URLS);

const mins = ((Date.now() - start) / 60000).toFixed(1);
console.log(`\n[batch-rewrite-6] DONE in ${mins} min`);
process.exit(0);
