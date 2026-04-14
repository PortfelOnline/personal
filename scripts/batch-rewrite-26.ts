/**
 * Batch-26: batch-24 + batch-25 объединены (2026-04-14)
 * batch-24: 46 HIGH-priority (выписки, справки, обременения)
 * batch-25: 35 HIGH-priority (проверка при покупке, справки ЕГРН, виды выписок)
 * Оба не запускались. Объединены для одного прогона.
 * Usage: npx tsx scripts/batch-rewrite-26.ts
 */
import 'dotenv/config';
import { runBatchRewrite } from '../server/routers/articles';

const BASE = 'https://kadastrmap.info/kadastr/';

// ── batch-24 ──────────────────────────────────────────────────────────────────
const SLUGS_24 = [
  // Справки и выписки ЕГРН — прямой заказ
  'spravku-egrn-cherez-internet',
  'spravka-na-dom-v-egrn',
  'spravka-egrn-po-vsej-rossii',
  'chto-takoe-predostavlenie-svedenij-iz-egrn',
  'vypiska-dlya-ooo-iz-egrn',
  'gde-vzyat-spravku-egrn',
  'kak-skachat-vypisku-egrn',
  'vypiska-na-zdanie-iz-egrn',
  'usluga-onlajn-vypiska-egrn-iz-rosreestra',
  'chto-takoe-predstavlenie-vypiski-iz-egrn',
  'kak-uznat-nomer-egrn-kvartiry',
  'spravka-egrn-na-nedvizhimoe-imushhestvo',
  'zaprosit-vypisku-iz-egrn-v-rosreestre',
  'pochemu-v-vypiske-net-kadastrovoj-stoimosti',
  'kto-daet-vypisku-iz-egrn',
  'skolko-zhdat-vypisku-iz-egrn',
  'vypiska-o-sobstvennosti-kvartiry-iz-egrn',
  'spravka-egrn-o-prave-sobstvennosti',
  // Обременения — высокий интент
  'chto-znachit-dolya-pod-obremeneniem',
  'kak-snyat-obremenenie-cherez-rosreestr',
  'proverit-kvartiru-na-obremenenie-pri-pokupke-bystryj-sposob',
  'kak-pokupat-kvartiru-s-obremeneniem-ipotekoj',
  'kak-kupit-kvartiru-bez-obremenenij',
  'kak-prodat-dom-s-obremeneniem',
  'chto-delat-esli-rosreestr-ne-vydaet-vypiski-iz-egrn',
  'chto-znachit-kvartira-s-obremeneniem',
  'kak-snyat-obremenenie-s-kvartiry-po-voennoj-ipoteke',
  'chto-delat-posle-snyatiya-obremeneniya-po-ipoteke',
  'kak-snyat-obremenenie-s-kvartiry-v-mfts',
  'kak-snyat-obremenenie-posle-vyplaty-materinskogo-kapitala',
  // Кадастровая стоимость
  'uznat-kadastrovuyu-stoimost-doma-onlajn-instruktsiya',
  'kak-uznat-zapis-egrn-kvartiry',
  'kak-opredelyaetsya-kadastrovaya-stoimost-uchastka',
  'kak-kupit-zemlyu-po-kadastrovoj-stoimosti',
  'kakoj-dokument-podtverzhdaet-pravo-sobstvennosti-na-kvartiru',
  'kak-uznat-kadastrovyj-nomer-zemelnogo-uchastka',
  // Проверка и поиск
  'uznat-kakaya-nedvizhimost-zaregistrirovana-na-cheloveka',
  'kak-proverit-zemelnyj-uchastok-po-kadastrovomu-nomeru-onlajn',
  'egrn-chto-eto-takoe-rasshifrovka',
  'spravka-iz-egrn-dlya-registratsii',
];

// ── batch-25 ──────────────────────────────────────────────────────────────────
const SLUGS_25 = [
  // Проверка при покупке / обременения
  'kak-proverit-dom-pered-pokupkoj-na-obremenenie',
  'kak-proverit-kvartiru-v-rosreestre-na-obremenenie',
  'kak-proverit-zemlyu-na-obremenenie-po-kadastrovomu-nomeru',
  'chto-mozhno-delat-s-kvartiroj-v-ipoteke-bez-vedoma-banka',
  'obremeneniya-i-ogranicheniya-na-kvartiru-chto-nuzhno-znat-pokupatelyu',
  'kak-proverit-kvartiru-na-obremenenie-samostoyatelno',
  'kak-proverit-kvartiru-na-obremeneniya-pered-pokupkoj-poshagovaya-instruktsiya',
  'proverit-kvartiru-pered-pokupkoj-onlajn-poshagovoe-rukovodstvo',
  'zaschita-prav-obremenenie-nedvizhimosti',
  'chto-takoe-obremenenie-nedvizhimosti-kak-proverit-i-izbezhat',
  // Справки ЕГРН — получение, стоимость, виды
  'gde-poluchayut-spravku-egrn',
  'kakie-nuzhny-dokumenty-dlya-spravki-iz-egrn',
  'dokumenty-dlya-spravki-egrn',
  'spravka-egrn-zakazat-cherez-rosreestr',
  'spravka-egrn-skolko-stoit',
  'spravka-egrn-skolko-delaetsya-po-vremeni',
  'stoimost-spravki-egrn',
  'spravka-egrn-chto-eto-i-gde-poluchit',
  'spravka-iz-egrn-o-nedvizhimosti',
  'gde-zakazyvat-spravku-egrn',
  // Выписки ЕГРН — виды, стоимость, получение
  'vidy-vypisok-iz-egrn',
  'vidy-vypisok-iz-egrn-na-zemelnyj-uchastok',
  'gde-poluchayut-vypisku-iz-egrn-na-kvartiru',
  'skolko-stoit-vypiska-iz-egrn-v-mfts',
  'srochnaya-vypiska-iz-egrn-v-mfts',
  'kak-vosstanovit-vypisku-iz-egrn',
  'tsena-vypiski-iz-egrn-na-zemelnyj-uchastok',
  'srok-dejstviya-vypiski-iz-egrn-ob-obekte-nedvizhimosti',
  'kak-poluchit-novuyu-vypisku-iz-egrn',
  'zakazat-vypisku-iz-egrn-o-kadastrovoj-stoimosti-obekta-nedvizhimosti',
  'vypiska-iz-egrn-pri-arende-kvartiry',
  'zemelnaya-spravka-iz-egrn',
  'vypiska-iz-egrn-po-obremeneniyam',
  'chto-mozhno-uznat-iz-vypiski-egrn',
  'egrn-vypiski-optom',
];

const ALL = [...new Set([...SLUGS_24, ...SLUGS_25])];
const URLS = ALL.map(s => `${BASE}${s}/`);

console.log(`[batch-26] Starting: ${URLS.length} articles`);
const start = Date.now();
await runBatchRewrite(1, URLS);
const mins = ((Date.now() - start) / 60000).toFixed(1);
console.log(`[batch-26] DONE in ${mins} min`);
