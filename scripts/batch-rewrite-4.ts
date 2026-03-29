/**
 * Batch 4: 25 HIGH-priority articles
 * Focus: gde-zakazat-*, kadastrovyj-pasport variants, vypiska-egrn-*, obremenenie
 * Priority: articles matching Google positions 11-20 (page 2 → easy win)
 *           + high-freq queries not ranking yet
 *
 * Usage: npx tsx scripts/batch-rewrite-4.ts
 */
import 'dotenv/config';
import { runBatchRewrite } from '../server/routers/articles';

const URLS = [
  // gde-zakazat variants (HIGH: zakazat pattern)
  'https://kadastrmap.info/kadastr/gde-zakazat-kadastrovyj-pasport/',
  'https://kadastrmap.info/kadastr/gde-zakazat-kadastrovyj-pasport-na-dom/',
  'https://kadastrmap.info/kadastr/gde-zakazat-kadastrovyj-pasport-na-kvartiru/',
  'https://kadastrmap.info/kadastr/gde-zakazat-kadastrovyj-pasport-na-zemelnyj-uchastok/',
  'https://kadastrmap.info/kadastr/gde-zakazat-kadastrovuyu-vypisku/',
  // gde-vzyat (HIGH)
  'https://kadastrmap.info/kadastr/gde-vzyat-kadastrovyj-pasport-zemelnogo-uchastka/',
  // kadastrovyj-pasport variants (HIGH)
  'https://kadastrmap.info/kadastr/kadastrovyj-pasport/',
  'https://kadastrmap.info/kadastr/kadastrovyj-pasport-kvartiry/',
  'https://kadastrmap.info/kadastr/kadastrovyj-pasport-na-dom/',
  'https://kadastrmap.info/kadastr/kadastrovyj-pasport-na-zemelnyj-uchastok/',
  'https://kadastrmap.info/kadastr/kadastrovyj-pasport-na-zemlyu/',
  'https://kadastrmap.info/kadastr/kadastrovyj-pasport-zemelnogo-uchastka/',
  // obremenenie (Google page 2 → easy wins, freq 50-84)
  'https://kadastrmap.info/kadastr/kak-snyat-obremenenie-s-kvartiry/',
  'https://kadastrmap.info/kadastr/obremenenie-na-kvartiru/',
  'https://kadastrmap.info/kadastr/proverit-obremenenie-na-kvartiru/',
  'https://kadastrmap.info/kadastr/arest-nedvizhimosti/',
  // vypiska-egrn variants (not ranking, high commercial value)
  'https://kadastrmap.info/kadastr/poluchit-vypisku-iz-egrn/',
  'https://kadastrmap.info/kadastr/poluchit-vypisku-iz-egrn-onlajn/',
  'https://kadastrmap.info/kadastr/poluchit-vypisku-egrn-bystro/',
  'https://kadastrmap.info/kadastr/zakazat-vypisku-iz-egrn/',
  'https://kadastrmap.info/kadastr/zakazat-vypisku-egrn-onlajn/',
  // kadastrovaya-stoimost (freq 582+22, not ranking)
  'https://kadastrmap.info/kadastr/kadastrovaya-stoimost-kvartiry/',
  'https://kadastrmap.info/kadastr/kadastrovaya-stoimost-zemelnogo-uchastka/',
  // uznat-vladeltsa (Google pos 35, freq 193 → page 2 opportunity)
  'https://kadastrmap.info/kadastr/uznat-vladeltsa-kvartiry-po-kadastrovomu-nomeru/',
  // spravka-ob-obremenenii (Google pos 10 → TOP-10 already, push to TOP-5)
  'https://kadastrmap.info/kadastr/spravka-ob-obremenenii-onlajn/',
];

const USER_ID = 1;

console.log(`[batch-rewrite-4] Starting: ${URLS.length} articles, userId=${USER_ID}`);
console.log(`[batch-rewrite-4] Priority: Google page-2 wins + high-freq not ranking`);
console.log(`[batch-rewrite-4] AI-mentions fix: answer-first structure + FAQ schema\n`);
const start = Date.now();

await runBatchRewrite(USER_ID, URLS);

const mins = ((Date.now() - start) / 60000).toFixed(1);
console.log(`\n[batch-rewrite-4] DONE in ${mins} min`);
process.exit(0);
