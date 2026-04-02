/**
 * Batch 15: Next 12 HIGH priority articles (score=30)
 * Goal: TOP-3 quality in Yandex + Google
 */
import 'dotenv/config';
import { runBatchRewrite } from '../server/routers/articles';

const URLS = [
  'https://kadastrmap.info/kadastr/kadastrovyj-pasport-chto-eto-za-dokument/',
  'https://kadastrmap.info/kadastr/kadastrovyj-pasport-dachnyj-domik/',
  'https://kadastrmap.info/kadastr/kadastrovyj-pasport-dlya-yuridicheskih-lits-stoimost/',
  'https://kadastrmap.info/kadastr/kadastrovyj-pasport-i-kadastrovyj-plan/',
  'https://kadastrmap.info/kadastr/kadastrovyj-pasport-kvartiry-gde-poluchit/',
  'https://kadastrmap.info/kadastr/kadastrovyj-pasport-mnogokvartirnogo-zhilogo-doma/',
  'https://kadastrmap.info/kadastr/kadastrovyj-pasport-na-chast-zhilogo-doma/',
  'https://kadastrmap.info/kadastr/kadastrovyj-pasport-na-dom-onlajn-rosreestr/',
  'https://kadastrmap.info/kadastr/kadastrovyj-pasport-na-garazhnyj-boks/',
  'https://kadastrmap.info/kadastr/kadastrovyj-pasport-na-kvartiru-mfts/',
  'https://kadastrmap.info/kadastr/kadastrovyj-pasport-obekta-nedvizhimosti-eto/',
  'https://kadastrmap.info/kadastr/kadastrovyj-pasport-obekta-nedvizhimosti-stoimost-2/',
];

const USER_ID = 1;
console.log(`[batch-15] Starting: ${URLS.length} articles`);
const start = Date.now();
await runBatchRewrite(USER_ID, URLS);
const mins = ((Date.now() - start) / 60000).toFixed(1);
console.log(`[batch-15] DONE in ${mins} min`);
