/**
 * Batch-29 (2026-04-14): Кадастровый паспорт на земельный участок + дом + квартира залог/арест
 *
 * Group 1 — Кадастровый паспорт на земельный участок (прямой заказ)
 * Group 2 — Кадастровый паспорт на дом / жилой дом
 * Group 3 — Квартира: залог, арест, проверка
 * Group 4 — Выписки и планы на земельный участок
 *
 * Usage: npx tsx scripts/batch-rewrite-29.ts 2>&1 | tee /tmp/batch29.log
 */
import 'dotenv/config';
import { runBatchRewrite } from '../server/routers/articles';

const BASE = 'https://kadastrmap.info/kadastr/';

// ── Group 1: Кадастровый паспорт земельный участок ───────────────────────────
const SLUGS_PASPORT_ZU = [
  'zakazat-kadastrovyj-pasport-na-zemelnyj-uchastok',
  'zakazat-kadastrovyj-pasport-na-zemelnyj-uchastok-onlajn-v-rosreestre',
  'gde-poluchit-kadastrovyj-pasport-na-zemelnyj-uchastok',
  'kak-zakazat-kadastrovyj-pasport-na-zemelnyj-uchastok',
  'poluchenie-kadastrovogo-pasporta-na-zemelnyj-uchastok',
  'tsena-kadastrovogo-pasporta-na-zemelnyj-uchastok',
  'kto-delaet-kadastrovyj-pasport-na-zemelnyj-uchastok',
  'gde-vydayut-kadastrovyj-pasport-na-zemelnyj-uchastok',
  'chto-takoe-kadastrovyj-pasport-na-zemelnyj-uchastok',
  'kak-postavit-na-uchet-kadastrovyj-zemelnyj-uchastok',
];

// ── Group 2: Кадастровый паспорт дом ─────────────────────────────────────────
const SLUGS_PASPORT_DOM = [
  'kadastrovyj-pasport-zhilogo-doma',
  'kadastrovyj-pasport-na-chast-zhilogo-doma',
  'kadastrovyj-plan-doma',
  'kadastrovyj-plan-doma-kak-poluchit',
  'poluchenie-kadastrovogo-pasporta-pri-prodazhe-zhilogo-doma',
  'kadastrovyj-pasport-na-dom-v-snt',
  'kadastrovyj-pasport-doma-po-adresu',
  'kadastrovyj-pasport-doma-po-adresu-onlajn',
];

// ── Group 3: Квартира — залог, арест ─────────────────────────────────────────
const SLUGS_KVARTIRA = [
  'kak-uznat-kvartira-v-areste-ili-net',
  'kak-uznat-kvartira-v-zaloge-ili-net',
  'kak-uznat-nahoditsya-li-kvartira-pod-arestom',
  'kak-uznat-nahoditsya-li-kvartira-v-zaloge',
  'kvartira-pod-zalogom-kak-uznat',
];

// ── Group 4: Выписки и планы на земельный участок ─────────────────────────────
const SLUGS_VYPISKA_ZU = [
  'zakazat-kadastrovuyu-vypisku-na-zemelnyj-uchastok',
  'zakazat-kadastrovuyu-vypisku-na-zemelnyj-uchastok-v-elektronnom-vide',
  'kak-poluchit-kadastrovuyu-vypisku-na-zemelnyj-uchastok',
  'vypiska-iz-kadastra-na-zemelnyj-uchastok',
  'vypiska-iz-zemelnogo-kadastra-na-zemelnyj-uchastok',
  'rasshirennaya-kadastrovaya-vypiska-na-zemelnyj-uchastok',
];

const ALL_SLUGS = [
  ...SLUGS_PASPORT_ZU,
  ...SLUGS_PASPORT_DOM,
  ...SLUGS_KVARTIRA,
  ...SLUGS_VYPISKA_ZU,
];

const URLS = [...new Set(ALL_SLUGS)].map(s => `${BASE}${s}/`);
console.log(`Batch-29: ${URLS.length} URLs`);

const start = Date.now();
await runBatchRewrite(1, URLS);
const mins = ((Date.now() - start) / 60000).toFixed(1);
console.log(`[batch-29] DONE in ${mins} min`);
