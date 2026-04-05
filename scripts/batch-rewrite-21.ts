/**
 * Batch-21: 25 HIGH-priority articles (2026-04-04)
 */
import 'dotenv/config';
import { runBatchRewrite } from '../server/routers/articles';

const BASE = 'https://kadastrmap.info/kadastr/';
const SLUGS = [
  'rosreestr-uznat-sobstvennika-uchastka',
  'rosreestr-vypiska-iz-egrn',
  'rosreestr-zakazat-kadastrovyj-pasport',
  'skolko-delaetsya-kadastrovyj-pasport',
  'skolko-stoit-kadastrovyj-pasport',
  'skolko-stoit-kadastrovyj-pasport-na-kvartiru',
  'skolko-stoit-kadastrovyj-pasport-na-zemlyu',
  'skolko-stoit-kadastrovyj-pasport-uchastka',
  'skolko-stoit-kadastrovyj-plan',
  'skolko-stoit-poluchit-kadastrovyj-pasport',
  'skolko-stoit-rasshirennaya-vypiska-iz-egrn',
  'skolko-stoit-sdelat-kadastrovyj-pasport',
  'skolko-stoit-vypiska-iz-egrn-v-mfts',
  'skolko-stoit-zakazat-kadastrovyj-pasport-na-dom',
  'skolko-stoit-zakazat-kadastrovyj-pasport-na-kvartiru',
  'skolko-vremeni-dejstvitelna-kadastrovaya-spravka-na-nedvizhimost',
  'spravka-egrn-zakazat-cherez-rosreestr',
  'spravka-o-zaloge-nedvizhimosti',
  'srochnaya-vypiska-iz-egrn-v-mfts',
  'stoimost-vypiski-iz-egrp',
  'tsena-vypiski-iz-egrn-na-zemelnyj-uchastok',
  'usluga-onlajn-vypiska-egrn-iz-rosreestra',
  'uznat-sobstvennika-dachnogo-uchastka',
  'vypiska-egrn-dlya-fizicheskogo-litsa',
  'vypiska-egrn-v-elektronnom-vide',
];

const URLS = SLUGS.map(s => `${BASE}${s}/`);
console.log(`[batch-21] Starting: ${URLS.length} articles`);
const start = Date.now();
await runBatchRewrite(1, URLS);
const mins = ((Date.now() - start) / 60000).toFixed(1);
console.log(`[batch-21] DONE in ${mins} min`);
