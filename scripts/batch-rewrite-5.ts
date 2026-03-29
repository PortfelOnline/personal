/**
 * Batch 5: 25 HIGH-priority articles
 * Focus: kadastrovyj-pasport-* core cluster, vypiska-iz-egrn cluster,
 *        gde-zakazat variants, skolko-stoit (pricing), spravka/uznat
 *
 * IndexNow now submits to Yandex + Bing + Google sitemap ping automatically.
 *
 * Usage: npx tsx scripts/batch-rewrite-5.ts
 */
import 'dotenv/config';
import { runBatchRewrite } from '../server/routers/articles';

const URLS = [
  // gde-zakazat (HIGH: zakazat pattern, not in batch 4)
  'https://kadastrmap.info/kadastr/gde-zakazat-kadastrovyj-pasport-na-kvartiru-v-ekaterinburge/',
  'https://kadastrmap.info/kadastr/gde-zakazat-tehnicheskij-pasport-na-kvartiru/',
  'https://kadastrmap.info/kadastr/gde-zakazat-tehnicheskij-plan-kvartiry/',
  'https://kadastrmap.info/kadastr/gde-zakazat-vypisku-iz-egrn/',

  // kadastrovyj-pasport core (high-traffic, high-conversion)
  'https://kadastrmap.info/kadastr/kadastrovyj-pasport-chto-eto-takoe/',
  'https://kadastrmap.info/kadastr/kadastrovyj-pasport-kakie-dokumenty-nuzhny/',
  'https://kadastrmap.info/kadastr/kadastrovyj-pasport-na-kvartiru/',
  'https://kadastrmap.info/kadastr/kadastrovyj-pasport-na-kvartiru-kak-poluchit/',
  'https://kadastrmap.info/kadastr/kadastrovyj-pasport-na-kvartiru-stoimost/',
  'https://kadastrmap.info/kadastr/kadastrovyj-pasport-na-dom-kak-poluchit/',
  'https://kadastrmap.info/kadastr/kadastrovyj-pasport-onlajn/',
  'https://kadastrmap.info/kadastr/kadastrovyj-pasport-cherez-internet/',
  'https://kadastrmap.info/kadastr/kadastrovyj-pasport-gde-poluchit/',

  // vypiska-iz-egrn cluster (very high commercial value)
  'https://kadastrmap.info/kadastr/vypiska-iz-egrn-onlajn/',
  'https://kadastrmap.info/kadastr/vypiska-iz-egrn-zakazat/',
  'https://kadastrmap.info/kadastr/vypiska-iz-egrn-srochno/',
  'https://kadastrmap.info/kadastr/vypiska-iz-egrn-ob-obekte-nedvizhimosti/',
  'https://kadastrmap.info/kadastr/vypiska-iz-egrn-skolko-delaetsya/',

  // skolko-stoit (pricing queries — highest conversion intent)
  'https://kadastrmap.info/kadastr/skolko-stoit-vypiska-iz-egrn/',
  'https://kadastrmap.info/kadastr/stoimost-vypiski-iz-egrn/',
  'https://kadastrmap.info/kadastr/skolko-stoit-zakazat-kadastrovyj-pasport/',

  // spravka-ob-obremenenii cluster
  'https://kadastrmap.info/kadastr/spravka-ob-obremenenii-kvartiry-gde-poluchit/',
  'https://kadastrmap.info/kadastr/spravka-ob-obremenenii-na-kvartiru/',

  // uznat-sobstvennika (Google opportunity)
  'https://kadastrmap.info/kadastr/uznat-sobstvennika-zemelnogo-uchastka-po-kadastrovomu-nomeru/',

  // kadastrovaya-vypiska
  'https://kadastrmap.info/kadastr/kadastrovaya-vypiska-o-zemelnom-uchastke/',
];

const USER_ID = 1;

console.log(`[batch-rewrite-5] Starting: ${URLS.length} articles, userId=${USER_ID}`);
console.log(`[batch-rewrite-5] Clusters: gde-zakazat(4), kadastrovyj-pasport(9), vypiska-egrn(5), skolko-stoit(3), spravka(2), uznat(1), kadastrovaya-vypiska(1)`);
console.log(`[batch-rewrite-5] IndexNow: Yandex + Bing + Google sitemap ping per URL\n`);
const start = Date.now();

await runBatchRewrite(USER_ID, URLS);

const mins = ((Date.now() - start) / 60000).toFixed(1);
console.log(`\n[batch-rewrite-5] DONE in ${mins} min`);
process.exit(0);
