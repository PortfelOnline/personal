/**
 * Standalone batch rewrite script — runs outside tsx watch, won't be killed by file edits.
 * Usage: npx tsx scripts/batch-rewrite.ts
 */
import 'dotenv/config';
import { runBatchRewrite } from '../server/routers/articles';

// Override batchRewriteJobs progress to console
const URLS = [
  'https://kadastrmap.info/kadastr/kak-snyat-obremenenie-s-obekta-nedvizhimosti-poshagovaya-instruktsiya/',
  'https://kadastrmap.info/kadastr/kadastrovaya-stoimost-nedvizhimosti-v-rosreestre-kak-uznat/',
  'https://kadastrmap.info/kadastr/kak-snyat-obremenenie-s-ipotechnoj-kvartiry/',
  'https://kadastrmap.info/kadastr/kak-proverit-sobstvennika-po-kadastrovomu-nomeru-onlajn/',
  'https://kadastrmap.info/kadastr/karta-kadastrovoj-stoimosti-kak-uznat-tsenu-nedvizhimosti-onlajn/',
  'https://kadastrmap.info/kadastr/kak-snyat-arest-s-kvartiry-chto-delat-sobstvenniku/',
  'https://kadastrmap.info/kadastr/kak-snyat-obremenenie-posle-pogasheniya-ipoteki/',
  'https://kadastrmap.info/kadastr/vypiska-iz-egrn-na-zemelnyj-uchastok/',
  'https://kadastrmap.info/kadastr/kadastrovyj-plan-kvartiry-po-adresu/',
  'https://kadastrmap.info/kadastr/vypiska-iz-egrn-bystro/',
  'https://kadastrmap.info/kadastr/vypiska-iz-egrn-stoimost/',
  'https://kadastrmap.info/kadastr/vypiska-iz-egrn-na-zemlyu/',
  'https://kadastrmap.info/kadastr/vypiska-iz-egrn-na-nedvizhimost/',
  'https://kadastrmap.info/kadastr/vypiska-iz-egrn-zakazat-onlajn/',
  'https://kadastrmap.info/kadastr/vypiska-iz-egrn-na-kvartiru/',
  'https://kadastrmap.info/kadastr/nalozhen-li-arest-na-kvartiru/',
  'https://kadastrmap.info/kadastr/kvartira-pod-zalogom-spravka/',
  'https://kadastrmap.info/kadastr/kak-proverit-ne-v-zaloge-li-kvartira/',
  'https://kadastrmap.info/kadastr/kadastrovaya-publichnaya-karta-so-sputnika/',
  'https://kadastrmap.info/kadastr/raspolozhenie-po-kadastrovomu-nomeru/',
  'https://kadastrmap.info/kadastr/zakazat-kadastrovuyu-vypisku-onlajn-tsena-sposoby-polucheniya/',
  'https://kadastrmap.info/kadastr/plan-pomeshheniya-i-kadastrovaya-vypiska-kak-oni-svyazany/',
  'https://kadastrmap.info/kadastr/chto-ukazyvaetsya-v-vypiske-iz-egrn-na-kvartiru/',
  'https://kadastrmap.info/kadastr/kak-zakazat-vypisku-egrn-v-elektronnom-vide-cherez-gosuslugi/',
  'https://kadastrmap.info/kadastr/kadastrovaya-spravka-onlajn/',
  'https://kadastrmap.info/kadastr/generalnyj-plan-zemelnogo-uchastka-chto-eto-i-gde-poluchit/',
  'https://kadastrmap.info/kadastr/chto-nuzhno-znat-o-kadastrovyh-vypiskah/',
  'https://kadastrmap.info/kadastr/chem-otlichaetsya-situatsionnyj-plan-ot-kadastrovogo-plana-uchastka/',
  'https://kadastrmap.info/kadastr/situatsionnyj-plan-dlya-izhs-zachem-nuzhen-i-kak-zakazat-onlajn-bez-ocheredej/',
  'https://kadastrmap.info/kadastr/situatsionnyj-plan-dlya-stroitelstva-doma-poryadok-i-dokumenty/',
  'https://kadastrmap.info/kadastr/kak-uznat-svedeniya-po-kadastrovomu-nomeru-egrn-i-karta/',
  'https://kadastrmap.info/kadastr/poluchit-vypisku-o-perehode-prav-na-nedvizhimost-onlajn-bystro-i-udobno/',
  'https://kadastrmap.info/kadastr/kak-uznat-vladeltsa-kvartiry-po-adresu-zakonnye-sposoby-i-vypiska/',
  'https://kadastrmap.info/kadastr/publichnaya-kadastrovaya-karta-moskvy/',
  'https://kadastrmap.info/kadastr/publichnaya-kadastrovaya-karta-orlovskoj-oblasti/',
  'https://kadastrmap.info/kadastr/publichnaya-kadastrovaya-karta-moskovskoj-oblasti/',
  'https://kadastrmap.info/kadastr/publichnaya-kadastrovaya-karta-volgogradskaya-oblast/',
  'https://kadastrmap.info/kadastr/publichnaya-kadastrovaya-karta-ulyanovskoj-oblasti/',
  'https://kadastrmap.info/kadastr/publichnaya-kadastrovaya-karta-novosibirskoy-oblasti/',
  'https://kadastrmap.info/kadastr/kadastr-simferopol/',
  'https://kadastrmap.info/kadastr/zakazat-spravku-ob-obremenenii-nedvizhimosti-v-moskve-poshagovoe-rukovodstvo/',
  'https://kadastrmap.info/kadastr/zakazat-spravku-ob-obremenenii-nedvizhimosti-v-moskve-p/',
];

const USER_ID = 1; // dev-user-local

console.log(`[batch-rewrite] Starting: ${URLS.length} articles, userId=${USER_ID}`);
console.log('[batch-rewrite] This process is independent of tsx watch — safe to edit files');

const start = Date.now();

await runBatchRewrite(USER_ID, URLS);

const mins = ((Date.now() - start) / 60000).toFixed(1);
console.log(`\n[batch-rewrite] DONE in ${mins} min`);
process.exit(0);
