/**
 * Batch 2: 25 HIGH-priority commercial intent articles
 * Focus: vypiska, zakazat, obremenenie, kadastrovaya-spravka
 * Usage: npx tsx scripts/batch-rewrite-2.ts
 */
import 'dotenv/config';
import { runBatchRewrite } from '../server/routers/articles';

const URLS = [
  'https://kadastrmap.info/kadastr/chto-nuzhno-chtoby-poluchit-vypisku-iz-egrn/',
  'https://kadastrmap.info/kadastr/chto-pokazyvaet-vypiska-iz-egrn/',
  'https://kadastrmap.info/kadastr/elektronnaya-vypiska-iz-egrn/',
  'https://kadastrmap.info/kadastr/dlya-chego-nuzhna-vypiska-iz-egrn/',
  'https://kadastrmap.info/kadastr/dlya-chego-nuzhna-vypiska-iz-egrn-na-zemelnyj-uchastok/',
  'https://kadastrmap.info/kadastr/dlya-chego-nuzhna-vypiska-iz-egrn-ob-obekte-nedvizhimosti/',
  'https://kadastrmap.info/kadastr/kadastrovaya-spravka/',
  'https://kadastrmap.info/kadastr/kadastrovaya-spravka-iz-egrn/',
  'https://kadastrmap.info/kadastr/kadastrovaya-vypiska/',
  'https://kadastrmap.info/kadastr/kadastrovaya-vypiska-na-zemlyu/',
  'https://kadastrmap.info/kadastr/kadastrovaya-vypiska-ob-obekte-nedvizhimosti/',
  'https://kadastrmap.info/kadastr/kak-zakazat-kadastrovyj-pasport/',
  'https://kadastrmap.info/kadastr/kak-zakazat-kadastrovyj-pasport-cherez-internet/',
  'https://kadastrmap.info/kadastr/kak-zakazat-kadastrovuyu-spravku-o-kadastrovoj-stoimosti/',
  'https://kadastrmap.info/kadastr/kadastrovyj-pasport-kvartiry-zakazat/',
  'https://kadastrmap.info/kadastr/kadastrovyj-pasport-na-dom-zakazat/',
  'https://kadastrmap.info/kadastr/gde-mozhno-zakazat-kadastrovyj-pasport/',
  'https://kadastrmap.info/kadastr/gde-mozhno-zakazat-kadastrovyj-pasport-na-kvartiru/',
  'https://kadastrmap.info/kadastr/gde-poluchit-vypisku-iz-egrn/',
  'https://kadastrmap.info/kadastr/gde-poluchit-vypisku-iz-egrn-na-kvartiru/',
  'https://kadastrmap.info/kadastr/gde-mozhno-poluchit-vypisku-iz-egrn/',
  'https://kadastrmap.info/kadastr/gde-mozhno-poluchit-spravku-egrn/',
  'https://kadastrmap.info/kadastr/arest-kvartiry-obremeneniem/',
  'https://kadastrmap.info/kadastr/gde-proverit-kvartiru-na-obremenenie/',
  'https://kadastrmap.info/kadastr/kak-bystro-snimaetsya-obremenenie/',
];

const USER_ID = 1;

console.log(`[batch-rewrite-2] Starting: ${URLS.length} articles, userId=${USER_ID}`);
const start = Date.now();

await runBatchRewrite(USER_ID, URLS);

const mins = ((Date.now() - start) / 60000).toFixed(1);
console.log(`\n[batch-rewrite-2] DONE in ${mins} min`);
process.exit(0);
