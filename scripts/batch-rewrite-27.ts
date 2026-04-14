/**
 * Batch-27 (2026-04-14): High-traffic priority + межевание + регистрация
 *
 * Group 1 — High-traffic pages (low position, high impressions from GSC)
 * Group 2 — Межевание (land surveying): direct order / cost intent
 * Group 3 — Регистрация права собственности / дача амнистия
 * Group 4 — Кадастровый номер, план, границы
 *
 * Usage: npx tsx scripts/batch-rewrite-27.ts 2>&1 | tee /tmp/batch27.log
 */
import 'dotenv/config';
import { runBatchRewrite } from '../server/routers/articles';

const BASE = 'https://kadastrmap.info/kadastr/';

// ── Group 1: High-traffic priority (from GSC impressions data) ────────────────
const SLUGS_PRIORITY = [
  'kadastrovyj-nomer-po-adresu-obekta-nedvizhimosti',  // #15, 1944 impr
  'rosreestr-spravochnaya-informatsiya-po-obektam-nedvizhimosti-onlajn', // #18.6, 1010 impr
  'kadastrovye-koordinaty',              // #12.7, 974 impr
  'granitsy-zemelnogo-uchastka',         // #15.7, 548 impr
];

// ── Group 2: Межевание ────────────────────────────────────────────────────────
const SLUGS_MEZHEVANIE = [
  'skolko-stoit-mezhevanie-zemelnogo-uchastka',
  'mezhevanie-zemli-kak-pravilno-sdelat',
  'mezhevanie-zemelnogo-uchastka-kak-pravilno-sdelat',
  'mezhevanie-zemelnogo-uchastka-eto',
  'kadastrovoe-mezhevanie',
  'mozhno-li-prodat-zemelnyj-uchastok-bez-mezhevaniya',
  'est-li-neobhodimost-delat-mezhevanie-na-uchastke-v-snt',
  'osobennosti-provedeniya-mezhevaniya-zemelnogo-uchastka',
  'zachem-neobhodimo-mezhevanie-zemelnogo-uchastka',
  'kadastrovyj-i-mezhevoj-plan-v-chem-raznitsa',
];

// ── Group 3: Регистрация и оформление ────────────────────────────────────────
const SLUGS_REGISTRATSIYA = [
  'elektronnaya-registratsiya-prava-sobstvennosti',
  'registratsiya-nedvizhimosti-v-rosreestre',
  'registratsiya-doma-v-snt-do-i-posle-1-marta-2019-goda',
  'registratsiya-sadovogo-domika-pravo-ili-obyazannost-sobstvennika',
  'elektronnaya-registratsiya-ddu-v-rosreestre',
  'registratsiya-ddu-v-rosreestre-s-ipotekoj',
  'registratsiya-prava-na-dachnyj-uchastok',
  'registratsiya-doma-i-zemelnogo-uchastka-na-dache',
  'privatizatsiya-zemelnogo-uchastka',
];

// ── Group 4: Kadastr + границы ────────────────────────────────────────────────
const SLUGS_KADASTR = [
  'edinyj-gosudarstvennyj-reestr-nedvizhimosti',
  'gosudarstvennaya-registratsiya-i-kadastr',
  'kadastrovaya-registratsiya-ili-uchyot-nedvizhimosti',
  'o-gosudarstvennoj-registratsii-nedvizhimosti',
  'kakoj-document-podtverzhdaet-pravo-sobstvennosti-na-zemelnyj-uchastok',
];

const ALL_SLUGS = [
  ...SLUGS_PRIORITY,
  ...SLUGS_MEZHEVANIE,
  ...SLUGS_REGISTRATSIYA,
  ...SLUGS_KADASTR,
];

const URLS = [...new Set(ALL_SLUGS)].map(s => `${BASE}${s}/`);
console.log(`Batch-27: ${URLS.length} URLs`);

const start = Date.now();
await runBatchRewrite(1, URLS);
const mins = ((Date.now() - start) / 60000).toFixed(1);
console.log(`[batch-27] DONE in ${mins} min`);
