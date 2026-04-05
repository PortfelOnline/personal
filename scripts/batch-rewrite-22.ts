/**
 * Batch-22: remaining 21 HIGH-priority articles (2026-04-04)
 */
import 'dotenv/config';
import { runBatchRewrite } from '../server/routers/articles';

const BASE = 'https://kadastrmap.info/kadastr/';
const SLUGS = [
  'vypiska-egrn-za-chas',
  'vypiska-iz-egrn-dlya-propiski',
  'vypiska-iz-egrn-dlya-yuridicheskih-lits',
  'vypiska-iz-egrn-gosuslugi',
  'vypiska-iz-egrn-moskva',
  'vypiska-iz-egrn-na-imushhestvo',
  'vypiska-iz-egrn-na-mashinomesto',
  'vypiska-iz-egrn-na-pomeshhenie',
  'vypiska-iz-egrn-na-sobstvennost',
  'vypiska-iz-egrn-na-zemelnyj-uchastok-gosuslugi',
  'vypiska-iz-egrn-o-postanovke-obekta-na-kadastrovyj-uchet',
  'vypiska-iz-egrn-o-pravah-na-nedvizhimost',
  'vypiska-iz-egrn-o-pravoobladatele',
  'vypiska-iz-egrn-ob-osnovnyh-harakteristikah-obekta',
  'vypiska-iz-egrn-ofitsialnyj-sajt',
  'vypiska-iz-egrn-onlajn-fns',
  'vypiska-iz-egrn-onlajn-ofitsialnyj-sajt',
  'vypiska-iz-egrn-po-obremeneniyam',
  'vypiska-iz-egrn-podtverzhdayushhaya-pravo-sobstvennosti',
  'vypiska-iz-egrn-pri-arende-kvartiry',
  'vypiska-iz-egrn-vmesto-svidetelstva-o-sobstvennosti',
  'vypisku-o-kadastrovoj-stoimosti-zakazat',
  'zachem-nuzhen-kadastrovyj-pasport-na-zemelnyj-uchastok',
  'zachem-nuzhna-vypiska-iz-egrn-na-kvartiru',
  'zakazat-kadastrovuyu-spravku-o-kadastrovoj-stoimosti-kvartiry',
  'zakazat-kadastrovuyu-vipisku',
  'zakazat-kadastrovuyu-vypisku-cherez-internet',
  'zakazat-kadastrovuyu-vypisku-na-zemelnyj-uchastok',
  'zakazat-kadastrovuyu-vypisku-na-zemelnyj-uchastok-v-elektronnom-vide',
  'zakazat-kadastrovyj-pasport-na-zemelnyj-uchastok-onlajn-v-rosreestre',
  'zakazat-kadastrovyj-pasport-onlajn-v-rosreestre',
  'zakazat-kadastrovyj-pasport-v-mfts',
  'zakazat-kadastrovyj-pasport-zdaniya',
  'zakazat-kadastrovyj-pasport-zemelnogo-uchastka-zakazat',
  'zakazat-kadastrovyj-plan-na-zemlyu',
  'zakazat-onlajn-kadastrovuyu-vypisku',
  'zakazat-otchet-egrn-onlajn',
  'zakazat-rasshirennuyu-vypisku-iz-egrp',
  'zakazat-spravku-o-kadastrovoj-stoimosti-zemelnogo-uchastka',
  'zakazat-spravku-o-kadastrovoj-stoimosti-zemli',
  'zakazat-vypisku-egrn',
  'zakazat-vypisku-iz-egrn-o-kadastrovoj-stoimosti-obekta-nedvizhimosti',
  'zakazat-vypisku-iz-egrp-onlajn-rosreestr',
  'zakazat-vypisku-iz-egrp-rosreestr',
  'zakazat-vypisku-o-perehode-prav',
  'zemelnyj-kadastrovyj-pasport',
];

const URLS = SLUGS.map(s => `${BASE}${s}/`);
console.log(`[batch-22] Starting: ${URLS.length} articles`);
const start = Date.now();
await runBatchRewrite(1, URLS);
const mins = ((Date.now() - start) / 60000).toFixed(1);
console.log(`[batch-22] DONE in ${mins} min`);
